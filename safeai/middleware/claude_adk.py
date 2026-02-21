"""Claude ADK adapter for SafeAI action-boundary enforcement."""

from __future__ import annotations

from functools import wraps
from typing import Any, Callable

from safeai.middleware.base import BaseMiddleware
from safeai.middleware.langchain import (
    SafeAIBlockedError,
    _ainvoke_with_shape,
    _invoke_with_shape,
    _normalize_input,
    _normalize_response,
    _restore_response_shape,
)


class SafeAIClaudeADKAdapter(BaseMiddleware):
    """Adapter that wraps Claude ADK tool execution paths."""

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
        capability_token_id: str | None = None,
        capability_action: str = "invoke",
        approval_request_id: str | None = None,
    ) -> Callable[..., Any]:
        """Wrap a synchronous Claude ADK tool callable."""

        @wraps(fn)
        def _wrapped(*args: Any, **kwargs: Any) -> Any:
            payload, shape = _normalize_input(args, kwargs)
            tags = list(request_data_tags or [])

            request = self.safeai.intercept_tool_request(
                tool_name=tool_name,
                parameters=payload,
                data_tags=tags,
                agent_id=agent_id,
                session_id=session_id,
                source_agent_id=source_agent_id,
                destination_agent_id=destination_agent_id,
                action_type="claude_adk_tool",
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
            guarded = self.safeai.intercept_tool_response(
                tool_name=tool_name,
                response=_normalize_response(result),
                agent_id=agent_id,
                request_data_tags=tags,
                session_id=session_id,
                source_agent_id=source_agent_id,
                destination_agent_id=destination_agent_id,
                action_type="claude_adk_tool",
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
        capability_token_id: str | None = None,
        capability_action: str = "invoke",
        approval_request_id: str | None = None,
    ) -> Callable[..., Any]:
        """Wrap an asynchronous Claude ADK tool callable."""

        @wraps(fn)
        async def _wrapped(*args: Any, **kwargs: Any) -> Any:
            payload, shape = _normalize_input(args, kwargs)
            tags = list(request_data_tags or [])
            request = self.safeai.intercept_tool_request(
                tool_name=tool_name,
                parameters=payload,
                data_tags=tags,
                agent_id=agent_id,
                session_id=session_id,
                source_agent_id=source_agent_id,
                destination_agent_id=destination_agent_id,
                action_type="claude_adk_tool",
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
            guarded = self.safeai.intercept_tool_response(
                tool_name=tool_name,
                response=_normalize_response(result),
                agent_id=agent_id,
                request_data_tags=tags,
                session_id=session_id,
                source_agent_id=source_agent_id,
                destination_agent_id=destination_agent_id,
                action_type="claude_adk_tool",
            )
            if guarded.decision.action in {"block", "require_approval"}:
                raise SafeAIBlockedError(
                    action=guarded.decision.action,
                    policy_name=guarded.decision.policy_name,
                    reason=guarded.decision.reason,
                )
            return _restore_response_shape(result, guarded.filtered_response)

        return _wrapped
