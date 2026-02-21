"""Proxy route definitions for sidecar and gateway operation."""

from __future__ import annotations

import importlib.metadata
import json
import time
from typing import Any, Literal

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

try:
    _VERSION = importlib.metadata.version("safeai")
except importlib.metadata.PackageNotFoundError:
    _VERSION = "0.0.0-dev"

router = APIRouter()


@router.get("/v1/health")
def health(request: Request) -> dict[str, Any]:
    runtime = request.app.state.runtime
    return {
        "status": "ok",
        "mode": runtime.mode,
        "version": _VERSION,
    }


@router.get("/v1/metrics", response_class=PlainTextResponse)
def metrics(request: Request) -> str:
    runtime = request.app.state.runtime
    return runtime.metrics.render_prometheus()


class ScanInputPayload(BaseModel):
    text: str
    agent_id: str = "unknown"


class StructuredScanPayload(BaseModel):
    payload: Any
    agent_id: str = "unknown"


class FileScanPayload(BaseModel):
    path: str
    agent_id: str = "unknown"


class GuardOutputPayload(BaseModel):
    text: str
    agent_id: str = "unknown"


class ToolInterceptPayload(BaseModel):
    phase: Literal["request", "response"] = "request"
    tool_name: str
    data_tags: list[str] = Field(default_factory=list)
    agent_id: str = "unknown"
    session_id: str | None = None
    source_agent_id: str | None = None
    destination_agent_id: str | None = None
    action_type: str | None = None
    capability_token_id: str | None = None
    capability_action: str = "invoke"
    approval_request_id: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    response: dict[str, Any] | None = None


class AgentMessagePayload(BaseModel):
    message: str
    source_agent_id: str
    destination_agent_id: str
    data_tags: list[str] = Field(default_factory=list)
    session_id: str | None = None
    approval_request_id: str | None = None


class MemoryWritePayload(BaseModel):
    key: str
    value: Any
    agent_id: str = "unknown"


class MemoryReadPayload(BaseModel):
    key: str
    agent_id: str = "unknown"


class MemoryResolvePayload(BaseModel):
    handle_id: str
    agent_id: str = "unknown"
    session_id: str | None = None
    source_agent_id: str | None = None
    destination_agent_id: str | None = None


class AuditQueryPayload(BaseModel):
    boundary: str | None = None
    action: str | None = None
    policy_name: str | None = None
    agent_id: str | None = None
    tool_name: str | None = None
    data_tag: str | None = None
    phase: str | None = None
    session_id: str | None = None
    event_id: str | None = None
    source_agent_id: str | None = None
    destination_agent_id: str | None = None
    metadata_key: str | None = None
    metadata_value: str | None = None
    since: str | None = None
    until: str | None = None
    last: str | None = None
    limit: int = 100
    newest_first: bool = True


class PolicyReloadPayload(BaseModel):
    force: bool = False


class ProxyForwardPayload(BaseModel):
    method: str = "POST"
    path: str | None = None
    upstream_url: str | None = None
    headers: dict[str, str] = Field(default_factory=dict)
    json_body: dict[str, Any] | None = None
    text_body: str | None = None
    timeout_seconds: float = 10.0
    agent_id: str = "unknown"
    session_id: str | None = None
    source_agent_id: str | None = None
    destination_agent_id: str | None = None


@router.post("/v1/scan/input")
def scan_input(payload: ScanInputPayload, request: Request) -> dict[str, Any]:
    started = time.perf_counter()
    runtime = request.app.state.runtime
    result = runtime.safeai.scan_input(payload.text, agent_id=payload.agent_id)
    elapsed = time.perf_counter() - started
    runtime.metrics.observe_request(
        endpoint="/v1/scan/input",
        status_code=200,
        latency_seconds=elapsed,
        decision_action=result.decision.action,
    )
    return {
        "decision": {
            "action": result.decision.action,
            "policy_name": result.decision.policy_name,
            "reason": result.decision.reason,
        },
        "filtered": result.filtered,
        "detections": [
            {
                "detector": item.detector,
                "tag": item.tag,
                "start": item.start,
                "end": item.end,
            }
            for item in result.detections
        ],
    }


@router.post("/v1/scan/structured")
def scan_structured(payload: StructuredScanPayload, request: Request) -> dict[str, Any]:
    started = time.perf_counter()
    runtime = request.app.state.runtime
    result = runtime.safeai.scan_structured_input(payload.payload, agent_id=payload.agent_id)
    elapsed = time.perf_counter() - started
    runtime.metrics.observe_request(
        endpoint="/v1/scan/structured",
        status_code=200,
        latency_seconds=elapsed,
        decision_action=result.decision.action,
    )
    return {
        "decision": {
            "action": result.decision.action,
            "policy_name": result.decision.policy_name,
            "reason": result.decision.reason,
        },
        "filtered": result.filtered,
        "detections": [
            {
                "path": item.path,
                "detector": item.detector,
                "tag": item.tag,
                "start": item.start,
                "end": item.end,
            }
            for item in result.detections
        ],
    }


@router.post("/v1/scan/file")
def scan_file(payload: FileScanPayload, request: Request) -> dict[str, Any]:
    started = time.perf_counter()
    runtime = request.app.state.runtime
    try:
        result = runtime.safeai.scan_file_input(payload.path, agent_id=payload.agent_id)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        _record_error(
            runtime=runtime,
            endpoint="/v1/scan/file",
            started=started,
            status_code=400,
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    elapsed = time.perf_counter() - started
    runtime.metrics.observe_request(
        endpoint="/v1/scan/file",
        status_code=200,
        latency_seconds=elapsed,
        decision_action=result.get("decision", {}).get("action"),
    )
    return result


@router.post("/v1/guard/output")
def guard_output(payload: GuardOutputPayload, request: Request) -> dict[str, Any]:
    started = time.perf_counter()
    runtime = request.app.state.runtime
    result = runtime.safeai.guard_output(payload.text, agent_id=payload.agent_id)
    elapsed = time.perf_counter() - started
    runtime.metrics.observe_request(
        endpoint="/v1/guard/output",
        status_code=200,
        latency_seconds=elapsed,
        decision_action=result.decision.action,
    )
    return {
        "decision": {
            "action": result.decision.action,
            "policy_name": result.decision.policy_name,
            "reason": result.decision.reason,
        },
        "safe_output": result.safe_output,
        "fallback_used": result.fallback_used,
        "detections": [
            {
                "detector": item.detector,
                "tag": item.tag,
                "start": item.start,
                "end": item.end,
            }
            for item in result.detections
        ],
    }


@router.post("/v1/intercept/tool")
def intercept_tool(payload: ToolInterceptPayload, request: Request) -> dict[str, Any]:
    started = time.perf_counter()
    runtime = request.app.state.runtime
    _ensure_gateway_agent_context(
        runtime_mode=runtime.mode,
        source_agent_id=payload.source_agent_id,
        destination_agent_id=payload.destination_agent_id,
    )

    if payload.phase == "request":
        result = runtime.safeai.intercept_tool_request(
            tool_name=payload.tool_name,
            parameters=payload.parameters,
            data_tags=payload.data_tags,
            agent_id=payload.agent_id,
            session_id=payload.session_id,
            source_agent_id=payload.source_agent_id,
            destination_agent_id=payload.destination_agent_id,
            action_type=payload.action_type,
            capability_token_id=payload.capability_token_id,
            capability_action=payload.capability_action,
            approval_request_id=payload.approval_request_id,
        )
        elapsed = time.perf_counter() - started
        runtime.metrics.observe_request(
            endpoint="/v1/intercept/tool",
            status_code=200,
            latency_seconds=elapsed,
            decision_action=result.decision.action,
        )
        return {
            "phase": "request",
            "decision": {
                "action": result.decision.action,
                "policy_name": result.decision.policy_name,
                "reason": result.decision.reason,
            },
            "filtered_parameters": result.filtered_params,
            "unauthorized_tags": result.unauthorized_tags,
            "stripped_fields": result.stripped_fields,
        }

    if payload.response is None:
        _record_error(
            runtime=runtime,
            endpoint="/v1/intercept/tool",
            started=started,
            status_code=400,
        )
        raise HTTPException(status_code=400, detail="response is required when phase='response'")

    result = runtime.safeai.intercept_tool_response(
        tool_name=payload.tool_name,
        response=payload.response,
        agent_id=payload.agent_id,
        request_data_tags=payload.data_tags,
        session_id=payload.session_id,
        source_agent_id=payload.source_agent_id,
        destination_agent_id=payload.destination_agent_id,
        action_type=payload.action_type,
    )
    elapsed = time.perf_counter() - started
    runtime.metrics.observe_request(
        endpoint="/v1/intercept/tool",
        status_code=200,
        latency_seconds=elapsed,
        decision_action=result.decision.action,
    )
    return {
        "phase": "response",
        "decision": {
            "action": result.decision.action,
            "policy_name": result.decision.policy_name,
            "reason": result.decision.reason,
        },
        "filtered_response": result.filtered_response,
        "stripped_fields": result.stripped_fields,
        "stripped_tags": result.stripped_tags,
    }


@router.post("/v1/intercept/agent-message")
def intercept_agent_message(payload: AgentMessagePayload, request: Request) -> dict[str, Any]:
    started = time.perf_counter()
    runtime = request.app.state.runtime
    result = runtime.safeai.intercept_agent_message(
        message=payload.message,
        source_agent_id=payload.source_agent_id,
        destination_agent_id=payload.destination_agent_id,
        data_tags=payload.data_tags,
        session_id=payload.session_id,
        approval_request_id=payload.approval_request_id,
    )
    elapsed = time.perf_counter() - started
    runtime.metrics.observe_request(
        endpoint="/v1/intercept/agent-message",
        status_code=200,
        latency_seconds=elapsed,
        decision_action=result["decision"]["action"],
    )
    return result


@router.post("/v1/memory/write")
def memory_write(payload: MemoryWritePayload, request: Request) -> dict[str, Any]:
    started = time.perf_counter()
    runtime = request.app.state.runtime
    allowed = runtime.safeai.memory_write(payload.key, payload.value, agent_id=payload.agent_id)
    elapsed = time.perf_counter() - started
    runtime.metrics.observe_request(
        endpoint="/v1/memory/write",
        status_code=200,
        latency_seconds=elapsed,
        decision_action="allow" if allowed else "deny",
    )
    return {"allowed": allowed}


@router.post("/v1/memory/read")
def memory_read(payload: MemoryReadPayload, request: Request) -> dict[str, Any]:
    started = time.perf_counter()
    runtime = request.app.state.runtime
    value = runtime.safeai.memory_read(payload.key, agent_id=payload.agent_id)
    elapsed = time.perf_counter() - started
    runtime.metrics.observe_request(
        endpoint="/v1/memory/read",
        status_code=200,
        latency_seconds=elapsed,
        decision_action="allow" if value is not None else "deny",
    )
    return {"value": value}


@router.post("/v1/memory/resolve-handle")
def memory_resolve_handle(payload: MemoryResolvePayload, request: Request) -> dict[str, Any]:
    started = time.perf_counter()
    runtime = request.app.state.runtime
    value = runtime.safeai.resolve_memory_handle(
        payload.handle_id,
        agent_id=payload.agent_id,
        session_id=payload.session_id,
        source_agent_id=payload.source_agent_id,
        destination_agent_id=payload.destination_agent_id,
    )
    elapsed = time.perf_counter() - started
    runtime.metrics.observe_request(
        endpoint="/v1/memory/resolve-handle",
        status_code=200,
        latency_seconds=elapsed,
        decision_action="allow" if value is not None else "block",
    )
    return {"value": value}


@router.post("/v1/memory/purge-expired")
def memory_purge_expired(request: Request) -> dict[str, Any]:
    started = time.perf_counter()
    runtime = request.app.state.runtime
    purged = runtime.safeai.memory_purge_expired()
    elapsed = time.perf_counter() - started
    runtime.metrics.observe_request(
        endpoint="/v1/memory/purge-expired",
        status_code=200,
        latency_seconds=elapsed,
        decision_action="allow",
    )
    return {"purged": purged}


@router.post("/v1/audit/query")
def audit_query(payload: AuditQueryPayload, request: Request) -> dict[str, Any]:
    started = time.perf_counter()
    runtime = request.app.state.runtime
    rows = runtime.safeai.query_audit(
        boundary=payload.boundary,
        action=payload.action,
        policy_name=payload.policy_name,
        agent_id=payload.agent_id,
        tool_name=payload.tool_name,
        data_tag=payload.data_tag,
        phase=payload.phase,
        session_id=payload.session_id,
        event_id=payload.event_id,
        source_agent_id=payload.source_agent_id,
        destination_agent_id=payload.destination_agent_id,
        metadata_key=payload.metadata_key,
        metadata_value=payload.metadata_value,
        since=payload.since,
        until=payload.until,
        last=payload.last,
        limit=payload.limit,
        newest_first=payload.newest_first,
    )
    elapsed = time.perf_counter() - started
    runtime.metrics.observe_request(
        endpoint="/v1/audit/query",
        status_code=200,
        latency_seconds=elapsed,
        decision_action="allow",
    )
    return {"events": rows, "count": len(rows)}


@router.post("/v1/policies/reload")
def policies_reload(payload: PolicyReloadPayload, request: Request) -> dict[str, Any]:
    started = time.perf_counter()
    runtime = request.app.state.runtime
    reloaded = runtime.safeai.force_reload_policies() if payload.force else runtime.safeai.reload_policies()
    elapsed = time.perf_counter() - started
    runtime.metrics.observe_request(
        endpoint="/v1/policies/reload",
        status_code=200,
        latency_seconds=elapsed,
        decision_action="allow" if reloaded else "deny",
    )
    return {"reloaded": reloaded, "mode": "force" if payload.force else "changed_only"}


@router.get("/v1/plugins")
def list_plugins(request: Request) -> dict[str, Any]:
    started = time.perf_counter()
    runtime = request.app.state.runtime
    rows = runtime.safeai.list_plugins()
    elapsed = time.perf_counter() - started
    runtime.metrics.observe_request(
        endpoint="/v1/plugins",
        status_code=200,
        latency_seconds=elapsed,
        decision_action="allow",
    )
    return {"count": len(rows), "plugins": rows, "adapters": runtime.safeai.list_plugin_adapters()}


@router.get("/v1/policies/templates")
def list_policy_templates(request: Request) -> dict[str, Any]:
    started = time.perf_counter()
    runtime = request.app.state.runtime
    rows = runtime.safeai.list_policy_templates()
    elapsed = time.perf_counter() - started
    runtime.metrics.observe_request(
        endpoint="/v1/policies/templates",
        status_code=200,
        latency_seconds=elapsed,
        decision_action="allow",
    )
    return {"count": len(rows), "templates": rows}


@router.get("/v1/policies/templates/{template_name}")
def get_policy_template(template_name: str, request: Request) -> dict[str, Any]:
    started = time.perf_counter()
    runtime = request.app.state.runtime
    try:
        payload = runtime.safeai.load_policy_template(template_name)
    except KeyError as exc:
        _record_error(
            runtime=runtime,
            endpoint="/v1/policies/templates/{template_name}",
            started=started,
            status_code=404,
        )
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    elapsed = time.perf_counter() - started
    runtime.metrics.observe_request(
        endpoint="/v1/policies/templates/{template_name}",
        status_code=200,
        latency_seconds=elapsed,
        decision_action="allow",
    )
    return payload


@router.post("/v1/proxy/forward")
async def proxy_forward(payload: ProxyForwardPayload, request: Request) -> dict[str, Any]:
    started = time.perf_counter()
    runtime = request.app.state.runtime
    _ensure_gateway_agent_context(
        runtime_mode=runtime.mode,
        source_agent_id=payload.source_agent_id,
        destination_agent_id=payload.destination_agent_id,
    )
    method = str(payload.method).strip().upper() or "POST"
    target_url = _resolve_forward_url(
        upstream_url=payload.upstream_url,
        upstream_base_url=runtime.upstream_base_url,
        path=payload.path,
    )
    body_text = payload.text_body
    content: bytes | None = None
    headers = dict(payload.headers)
    if payload.json_body is not None:
        body_text = json.dumps(payload.json_body, separators=(",", ":"), ensure_ascii=True)
        headers.setdefault("content-type", "application/json")
        content = body_text.encode("utf-8")
    elif body_text is not None:
        content = body_text.encode("utf-8")

    scan_text = body_text or ""
    scan_result = runtime.safeai.scan_input(scan_text, agent_id=payload.agent_id)
    if scan_result.decision.action == "block":
        elapsed = time.perf_counter() - started
        runtime.metrics.observe_request(
            endpoint="/v1/proxy/forward",
            status_code=403,
            latency_seconds=elapsed,
            decision_action="block",
        )
        raise HTTPException(status_code=403, detail="input blocked by policy")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=target_url,
                headers=headers,
                content=content,
                timeout=float(payload.timeout_seconds),
            )
        upstream_status = response.status_code
        upstream_headers = dict(response.headers)
        response_body = response.content
    except httpx.HTTPError as exc:
        _record_error(
            runtime=runtime,
            endpoint="/v1/proxy/forward",
            started=started,
            status_code=502,
        )
        raise HTTPException(status_code=502, detail=f"upstream request failed: {exc}") from exc

    decoded = response_body.decode("utf-8", errors="replace")
    guarded = runtime.safeai.guard_output(decoded, agent_id=payload.agent_id)
    elapsed = time.perf_counter() - started
    runtime.metrics.observe_request(
        endpoint="/v1/proxy/forward",
        status_code=200,
        latency_seconds=elapsed,
        decision_action=guarded.decision.action,
    )
    return {
        "upstream_status": upstream_status,
        "upstream_headers": upstream_headers,
        "decision": {
            "action": guarded.decision.action,
            "policy_name": guarded.decision.policy_name,
            "reason": guarded.decision.reason,
        },
        "body": guarded.safe_output,
    }


def _resolve_forward_url(*, upstream_url: str | None, upstream_base_url: str | None, path: str | None) -> str:
    if upstream_url:
        return str(upstream_url).strip()
    if not upstream_base_url:
        raise HTTPException(status_code=400, detail="upstream_url or SAFEAI_UPSTREAM_BASE_URL is required")
    base = str(upstream_base_url).rstrip("/")
    suffix = str(path or "").strip()
    if not suffix.startswith("/"):
        suffix = "/" + suffix if suffix else ""
    return base + suffix


def _ensure_gateway_agent_context(
    *,
    runtime_mode: str,
    source_agent_id: str | None,
    destination_agent_id: str | None,
) -> None:
    if runtime_mode != "gateway":
        return
    if not str(source_agent_id or "").strip() or not str(destination_agent_id or "").strip():
        raise HTTPException(
            status_code=400,
            detail="gateway mode requires source_agent_id and destination_agent_id",
        )


def _record_error(*, runtime: Any, endpoint: str, started: float, status_code: int) -> None:
    runtime.metrics.observe_request(
        endpoint=endpoint,
        status_code=status_code,
        latency_seconds=time.perf_counter() - started,
    )
