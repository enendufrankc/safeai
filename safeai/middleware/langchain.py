"""LangChain middleware adapter for SafeAI action-boundary enforcement."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable, Protocol

from safeai.middleware.base import BaseMiddleware

try:  # pragma: no cover - optional dependency.
    from langchain_core.callbacks.base import BaseCallbackHandler
except Exception:  # pragma: no cover - fallback when langchain isn't installed.
    class BaseCallbackHandler:  # type: ignore[no-redef]
        pass


class SafeAIBlockedError(RuntimeError):
    """Raised when SafeAI blocks a LangChain tool invocation."""

    def __init__(self, *, action: str, policy_name: str | None, reason: str) -> None:
        super().__init__(f"SafeAI blocked tool call ({action}): {reason}")
        self.action = action
        self.policy_name = policy_name
        self.reason = reason


class TagExtractor(Protocol):
    def __call__(self, payload: dict[str, Any], *, safeai: Any) -> list[str]:
        ...


@dataclass
class _InvocationShape:
    mode: str
    key_order: list[str]


class SafeAILangChainAdapter(BaseMiddleware):
    """Adapter that wraps LangChain tool invocations with SafeAI checks."""

    def wrap_tool(
        self,
        tool_name: str,
        fn: Callable[..., Any],
        *,
        agent_id: str = "unknown",
        session_id: str | None = None,
        source_agent_id: str | None = None,
        destination_agent_id: str | None = None,
        request_data_tags: list[str] | None = None,
        tag_extractor: TagExtractor | None = None,
        capability_token_id: str | None = None,
        capability_action: str = "invoke",
        approval_request_id: str | None = None,
    ) -> Callable[..., Any]:
        """Wrap a synchronous tool callable.

        Input payload is normalized to key/value form, validated on request,
        then the tool response is filtered before returning to caller.
        """

        @wraps(fn)
        def _wrapped(*args: Any, **kwargs: Any) -> Any:
            payload, shape = _normalize_input(args, kwargs)
            inferred_tags = _infer_tags(payload, safeai=self.safeai, extractor=tag_extractor)
            tags = list(request_data_tags or inferred_tags)

            request = self.safeai.intercept_tool_request(
                tool_name=tool_name,
                parameters=payload,
                data_tags=tags,
                agent_id=agent_id,
                session_id=session_id,
                source_agent_id=source_agent_id,
                destination_agent_id=destination_agent_id,
                action_type="langchain_tool",
                capability_token_id=capability_token_id,
                capability_action=capability_action,
                approval_request_id=approval_request_id,
            )
            if request.decision.action != "allow":
                raise SafeAIBlockedError(
                    action=request.decision.action,
                    policy_name=request.decision.policy_name,
                    reason=request.decision.reason,
                )

            result = _invoke_with_shape(fn, request.filtered_params, shape)
            response_payload = _normalize_response(result)
            guarded = self.safeai.intercept_tool_response(
                tool_name=tool_name,
                response=response_payload,
                agent_id=agent_id,
                request_data_tags=tags,
                session_id=session_id,
                source_agent_id=source_agent_id,
                destination_agent_id=destination_agent_id,
                action_type="langchain_tool",
            )
            if guarded.decision.action in {"block", "require_approval"}:
                raise SafeAIBlockedError(
                    action=guarded.decision.action,
                    policy_name=guarded.decision.policy_name,
                    reason=guarded.decision.reason,
                )
            return _restore_response_shape(result, guarded.filtered_response)

        return _wrapped

    def wrap_async_tool(
        self,
        tool_name: str,
        fn: Callable[..., Any],
        *,
        agent_id: str = "unknown",
        session_id: str | None = None,
        source_agent_id: str | None = None,
        destination_agent_id: str | None = None,
        request_data_tags: list[str] | None = None,
        tag_extractor: TagExtractor | None = None,
        capability_token_id: str | None = None,
        capability_action: str = "invoke",
        approval_request_id: str | None = None,
    ) -> Callable[..., Any]:
        """Wrap an async tool callable."""

        @wraps(fn)
        async def _wrapped(*args: Any, **kwargs: Any) -> Any:
            payload, shape = _normalize_input(args, kwargs)
            inferred_tags = _infer_tags(payload, safeai=self.safeai, extractor=tag_extractor)
            tags = list(request_data_tags or inferred_tags)

            request = self.safeai.intercept_tool_request(
                tool_name=tool_name,
                parameters=payload,
                data_tags=tags,
                agent_id=agent_id,
                session_id=session_id,
                source_agent_id=source_agent_id,
                destination_agent_id=destination_agent_id,
                action_type="langchain_tool",
                capability_token_id=capability_token_id,
                capability_action=capability_action,
                approval_request_id=approval_request_id,
            )
            if request.decision.action != "allow":
                raise SafeAIBlockedError(
                    action=request.decision.action,
                    policy_name=request.decision.policy_name,
                    reason=request.decision.reason,
                )

            result = await _ainvoke_with_shape(fn, request.filtered_params, shape)
            response_payload = _normalize_response(result)
            guarded = self.safeai.intercept_tool_response(
                tool_name=tool_name,
                response=response_payload,
                agent_id=agent_id,
                request_data_tags=tags,
                session_id=session_id,
                source_agent_id=source_agent_id,
                destination_agent_id=destination_agent_id,
                action_type="langchain_tool",
            )
            if guarded.decision.action in {"block", "require_approval"}:
                raise SafeAIBlockedError(
                    action=guarded.decision.action,
                    policy_name=guarded.decision.policy_name,
                    reason=guarded.decision.reason,
                )
            return _restore_response_shape(result, guarded.filtered_response)

        return _wrapped

    def wrap_langchain_tool(
        self,
        tool: Any,
        *,
        agent_id: str = "unknown",
        session_id: str | None = None,
        source_agent_id: str | None = None,
        destination_agent_id: str | None = None,
        request_data_tags: list[str] | None = None,
        capability_token_id: str | None = None,
        capability_action: str = "invoke",
        approval_request_id: str | None = None,
    ) -> Any:
        """Patch `invoke`/`ainvoke` on a LangChain-like tool object in place."""
        tool_name = str(getattr(tool, "name", "") or getattr(tool, "__name__", "tool")).strip() or "tool"
        if hasattr(tool, "invoke") and callable(tool.invoke):
            tool.invoke = self.wrap_tool(
                tool_name=tool_name,
                fn=tool.invoke,
                agent_id=agent_id,
                session_id=session_id,
                source_agent_id=source_agent_id,
                destination_agent_id=destination_agent_id,
                request_data_tags=request_data_tags,
                capability_token_id=capability_token_id,
                capability_action=capability_action,
                approval_request_id=approval_request_id,
            )
        if hasattr(tool, "ainvoke") and callable(tool.ainvoke):
            tool.ainvoke = self.wrap_async_tool(
                tool_name=tool_name,
                fn=tool.ainvoke,
                agent_id=agent_id,
                session_id=session_id,
                source_agent_id=source_agent_id,
                destination_agent_id=destination_agent_id,
                request_data_tags=request_data_tags,
                capability_token_id=capability_token_id,
                capability_action=capability_action,
                approval_request_id=approval_request_id,
            )
        return tool


class SafeAICallback(BaseCallbackHandler):
    """LangChain callback helper for explicit request/response interception."""

    def __init__(
        self,
        safeai: Any,
        *,
        agent_id: str = "unknown",
        session_id: str | None = None,
        source_agent_id: str | None = None,
        destination_agent_id: str | None = None,
    ) -> None:
        self.safeai = safeai
        self.agent_id = agent_id
        self.session_id = session_id
        self.source_agent_id = source_agent_id
        self.destination_agent_id = destination_agent_id

    def intercept_tool_call(
        self,
        *,
        tool_name: str,
        parameters: dict[str, Any],
        response: dict[str, Any],
        data_tags: list[str],
        capability_token_id: str | None = None,
        capability_action: str = "invoke",
        approval_request_id: str | None = None,
    ) -> dict[str, Any]:
        """Run explicit request + response interception for callback-driven flows."""
        request = self.safeai.intercept_tool_request(
            tool_name=tool_name,
            parameters=parameters,
            data_tags=data_tags,
            agent_id=self.agent_id,
            session_id=self.session_id,
            source_agent_id=self.source_agent_id,
            destination_agent_id=self.destination_agent_id,
            action_type="langchain_callback",
            capability_token_id=capability_token_id,
            capability_action=capability_action,
            approval_request_id=approval_request_id,
        )
        if request.decision.action != "allow":
            raise SafeAIBlockedError(
                action=request.decision.action,
                policy_name=request.decision.policy_name,
                reason=request.decision.reason,
            )

        guarded = self.safeai.intercept_tool_response(
            tool_name=tool_name,
            response=response,
            agent_id=self.agent_id,
            request_data_tags=data_tags,
            session_id=self.session_id,
            source_agent_id=self.source_agent_id,
            destination_agent_id=self.destination_agent_id,
            action_type="langchain_callback",
        )
        if guarded.decision.action in {"block", "require_approval"}:
            raise SafeAIBlockedError(
                action=guarded.decision.action,
                policy_name=guarded.decision.policy_name,
                reason=guarded.decision.reason,
            )
        return guarded.filtered_response


def _normalize_input(args: tuple[Any, ...], kwargs: dict[str, Any]) -> tuple[dict[str, Any], _InvocationShape]:
    if kwargs:
        keys = sorted(kwargs.keys())
        return dict(kwargs), _InvocationShape(mode="kwargs", key_order=keys)
    if len(args) == 1 and isinstance(args[0], dict):
        payload = dict(args[0])
        return payload, _InvocationShape(mode="dict-arg", key_order=sorted(payload.keys()))
    if len(args) == 1:
        return {"input": args[0]}, _InvocationShape(mode="single-arg", key_order=["input"])
    if not args:
        return {}, _InvocationShape(mode="empty", key_order=[])

    payload = {f"arg{index}": value for index, value in enumerate(args)}
    return payload, _InvocationShape(mode="multi-arg", key_order=list(payload.keys()))


def _invoke_with_shape(fn: Callable[..., Any], payload: dict[str, Any], shape: _InvocationShape) -> Any:
    if shape.mode == "kwargs":
        return fn(**payload)
    if shape.mode == "dict-arg":
        return fn(payload)
    if shape.mode == "single-arg":
        return fn(payload.get("input"))
    if shape.mode == "empty":
        return fn()
    ordered = [payload.get(key) for key in shape.key_order]
    return fn(*ordered)


async def _ainvoke_with_shape(fn: Callable[..., Any], payload: dict[str, Any], shape: _InvocationShape) -> Any:
    if shape.mode == "kwargs":
        return await fn(**payload)
    if shape.mode == "dict-arg":
        return await fn(payload)
    if shape.mode == "single-arg":
        return await fn(payload.get("input"))
    if shape.mode == "empty":
        return await fn()
    ordered = [payload.get(key) for key in shape.key_order]
    return await fn(*ordered)


def _normalize_response(result: Any) -> dict[str, Any]:
    if isinstance(result, dict):
        return dict(result)
    if hasattr(result, "model_dump") and callable(result.model_dump):
        dumped = result.model_dump()
        if isinstance(dumped, dict):
            return dumped
    if hasattr(result, "dict") and callable(result.dict):
        dumped = result.dict()
        if isinstance(dumped, dict):
            return dumped
    return {"result": result}


def _restore_response_shape(original_result: Any, filtered: dict[str, Any]) -> Any:
    if isinstance(original_result, dict):
        return filtered
    if "result" in filtered and len(filtered) == 1:
        return filtered["result"]
    return filtered


def _infer_tags(
    payload: dict[str, Any],
    *,
    safeai: Any,
    extractor: TagExtractor | None,
) -> list[str]:
    if extractor is not None:
        return sorted({str(tag).strip().lower() for tag in extractor(payload, safeai=safeai) if str(tag).strip()})

    text = json.dumps(payload, sort_keys=True, default=str)
    detections = safeai.classifier.classify_text(text)
    return sorted({item.tag for item in detections})
