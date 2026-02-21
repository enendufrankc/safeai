"""Phase 5 dashboard HTTP routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

router = APIRouter()


class EventQueryPayload(BaseModel):
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


class ApprovalDecisionPayload(BaseModel):
    note: str | None = None


class ComplianceReportPayload(BaseModel):
    since: str | None = None
    until: str | None = None
    last: str | None = "24h"
    limit: int = 20000


class TenantPolicyPayload(BaseModel):
    name: str | None = None
    policy_files: list[str] = Field(default_factory=list)
    agents: list[str] = Field(default_factory=list)


class AlertRulePayload(BaseModel):
    rule_id: str
    name: str
    threshold: int = 1
    window: str = "15m"
    filters: dict[str, Any] = Field(default_factory=dict)
    channels: list[str] = Field(default_factory=lambda: ["file"])


class AlertEvaluatePayload(BaseModel):
    last: str = "15m"


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_index(request: Request) -> str:
    runtime = request.app.state.runtime
    return runtime.dashboard.render_dashboard_page()


@router.get("/v1/dashboard/overview")
def dashboard_overview(request: Request, last: str = "24h") -> dict[str, Any]:
    runtime = request.app.state.runtime
    principal = runtime.dashboard.authorize_request(request.headers, permission="dashboard:view")
    return runtime.dashboard.overview(principal, last=last)


@router.post("/v1/dashboard/events/query")
def dashboard_query_events(payload: EventQueryPayload, request: Request) -> dict[str, Any]:
    runtime = request.app.state.runtime
    principal = runtime.dashboard.authorize_request(request.headers, permission="audit:read")
    rows = runtime.dashboard.query_events(principal, filters=payload.model_dump())
    return {"count": len(rows), "events": rows}


@router.get("/v1/dashboard/incidents")
def dashboard_incidents(request: Request, last: str = "24h", limit: int = 100) -> list[dict[str, Any]]:
    runtime = request.app.state.runtime
    principal = runtime.dashboard.authorize_request(request.headers, permission="incident:read")
    return runtime.dashboard.list_incidents(principal, last=last, limit=limit)


@router.get("/v1/dashboard/approvals")
def dashboard_list_approvals(
    request: Request,
    status: str | None = None,
    limit: int = 100,
    newest_first: bool = True,
) -> list[dict[str, Any]]:
    runtime = request.app.state.runtime
    principal = runtime.dashboard.authorize_request(request.headers, permission="approval:read")
    return runtime.dashboard.list_approvals(
        principal,
        status=status,
        limit=limit,
        newest_first=newest_first,
    )


@router.post("/v1/dashboard/approvals/{request_id}/approve")
def dashboard_approve_request(
    request_id: str,
    payload: ApprovalDecisionPayload,
    request: Request,
) -> dict[str, Any]:
    runtime = request.app.state.runtime
    principal = runtime.dashboard.authorize_request(request.headers, permission="approval:decide")
    return runtime.dashboard.decide_approval(principal, request_id=request_id, decision="approve", note=payload.note)


@router.post("/v1/dashboard/approvals/{request_id}/deny")
def dashboard_deny_request(
    request_id: str,
    payload: ApprovalDecisionPayload,
    request: Request,
) -> dict[str, Any]:
    runtime = request.app.state.runtime
    principal = runtime.dashboard.authorize_request(request.headers, permission="approval:decide")
    return runtime.dashboard.decide_approval(principal, request_id=request_id, decision="deny", note=payload.note)


@router.post("/v1/dashboard/compliance/report")
def dashboard_compliance_report(payload: ComplianceReportPayload, request: Request) -> dict[str, Any]:
    runtime = request.app.state.runtime
    principal = runtime.dashboard.authorize_request(request.headers, permission="compliance:report")
    return runtime.dashboard.compliance_report(
        principal,
        since=payload.since,
        until=payload.until,
        last=payload.last,
        limit=payload.limit,
    )


@router.get("/v1/dashboard/tenants")
def dashboard_list_tenants(request: Request) -> list[dict[str, Any]]:
    runtime = request.app.state.runtime
    principal = runtime.dashboard.authorize_request(request.headers, permission="tenant:read")
    return runtime.dashboard.list_tenant_policy_sets(principal)


@router.get("/v1/dashboard/tenants/{tenant_id}/policies")
def dashboard_get_tenant_policies(tenant_id: str, request: Request) -> dict[str, Any]:
    runtime = request.app.state.runtime
    principal = runtime.dashboard.authorize_request(request.headers, permission="tenant:read")
    return runtime.dashboard.get_tenant_policy_set(principal, tenant_id)


@router.put("/v1/dashboard/tenants/{tenant_id}/policies")
def dashboard_upsert_tenant_policies(
    tenant_id: str,
    payload: TenantPolicyPayload,
    request: Request,
) -> dict[str, Any]:
    runtime = request.app.state.runtime
    principal = runtime.dashboard.authorize_request(request.headers, permission="tenant:manage")
    return runtime.dashboard.update_tenant_policy_set(
        principal,
        tenant_id=tenant_id,
        name=payload.name,
        policy_files=payload.policy_files,
        agents=payload.agents,
    )


@router.get("/v1/dashboard/alerts/rules")
def dashboard_list_alert_rules(request: Request) -> list[dict[str, Any]]:
    runtime = request.app.state.runtime
    _ = runtime.dashboard.authorize_request(request.headers, permission="alert:read")
    return runtime.dashboard.list_alert_rules()


@router.post("/v1/dashboard/alerts/rules")
def dashboard_upsert_alert_rule(payload: AlertRulePayload, request: Request) -> dict[str, Any]:
    runtime = request.app.state.runtime
    _ = runtime.dashboard.authorize_request(request.headers, permission="alert:manage")
    return runtime.dashboard.upsert_alert_rule(
        rule_id=payload.rule_id,
        name=payload.name,
        threshold=payload.threshold,
        window=payload.window,
        filters=payload.filters,
        channels=payload.channels,
    )


@router.get("/v1/dashboard/observe/agents")
def dashboard_observe_agents(request: Request, last: str = "24h") -> dict[str, Any]:
    runtime = request.app.state.runtime
    principal = runtime.dashboard.authorize_request(request.headers, permission="audit:read")
    agents = runtime.dashboard.agent_timeline(principal, last=last)
    for item in agents:
        item.pop("events", None)
    return {"count": len(agents), "agents": agents}


@router.get("/v1/dashboard/observe/agents/{agent_id}")
def dashboard_observe_agent_detail(agent_id: str, request: Request, last: str = "24h", limit: int = 100) -> dict[str, Any]:
    runtime = request.app.state.runtime
    principal = runtime.dashboard.authorize_request(request.headers, permission="audit:read")
    timelines = runtime.dashboard.agent_timeline(principal, agent_id=agent_id, last=last, limit=limit)
    if not timelines:
        return {"agent_id": agent_id, "event_count": 0, "events": []}
    return timelines[0]


@router.get("/v1/dashboard/observe/sessions/{session_id}")
def dashboard_observe_session(session_id: str, request: Request, limit: int = 200) -> dict[str, Any]:
    runtime = request.app.state.runtime
    principal = runtime.dashboard.authorize_request(request.headers, permission="audit:read")
    events = runtime.dashboard.session_trace(principal, session_id=session_id, limit=limit)
    return {"session_id": session_id, "count": len(events), "events": events}


@router.get("/v1/dashboard/observe/metrics")
def dashboard_observe_metrics(request: Request) -> dict[str, Any]:
    runtime = request.app.state.runtime
    _ = runtime.dashboard.authorize_request(request.headers, permission="audit:read")
    return {
        "agents": runtime.metrics.agent_summary(),
        "tools": runtime.metrics.tool_summary(),
    }


@router.get("/v1/dashboard/alerts/history")
def dashboard_alert_history(request: Request, limit: int = 50) -> dict[str, Any]:
    runtime = request.app.state.runtime
    _ = runtime.dashboard.authorize_request(request.headers, permission="alert:read")
    alerts = runtime.dashboard._alerts.recent_alerts(limit=limit)
    return {"count": len(alerts), "alerts": alerts}


class IntelligenceExplainPayload(BaseModel):
    event_id: str


@router.post("/v1/dashboard/intelligence/explain")
def dashboard_intelligence_explain(
    payload: IntelligenceExplainPayload, request: Request
) -> dict[str, Any]:
    runtime = request.app.state.runtime
    runtime.dashboard.authorize_request(request.headers, permission="intelligence:explain")
    try:
        result = runtime.safeai.intelligence_explain(payload.event_id)
    except Exception as exc:
        return {"error": f"Intelligence layer not configured: {exc}"}
    return {
        "advisor": result.advisor_name,
        "status": result.status,
        "summary": result.summary,
        "response": result.raw_response,
        "model": result.model_used,
        "metadata": result.metadata,
    }


@router.get("/v1/dashboard/templates")
def dashboard_list_templates(request: Request) -> dict[str, Any]:
    runtime = request.app.state.runtime
    _ = runtime.dashboard.authorize_request(request.headers, permission="dashboard:view")
    rows = runtime.safeai.list_policy_templates()
    return {"count": len(rows), "templates": rows}


class TemplateSearchPayload(BaseModel):
    query: str | None = None
    category: str | None = None
    tags: list[str] = Field(default_factory=list)
    compliance: str | None = None


@router.post("/v1/dashboard/templates/search")
def dashboard_search_templates(payload: TemplateSearchPayload, request: Request) -> dict[str, Any]:
    runtime = request.app.state.runtime
    _ = runtime.dashboard.authorize_request(request.headers, permission="dashboard:view")
    results = runtime.safeai.search_policy_templates(
        query=payload.query,
        category=payload.category,
        tags=payload.tags if payload.tags else None,
        compliance=payload.compliance,
    )
    return {"count": len(results), "templates": results}


class TemplateInstallPayload(BaseModel):
    name: str


@router.post("/v1/dashboard/templates/install")
def dashboard_install_template(payload: TemplateInstallPayload, request: Request) -> dict[str, Any]:
    runtime = request.app.state.runtime
    _ = runtime.dashboard.authorize_request(request.headers, permission="alert:manage")
    try:
        path = runtime.safeai.install_policy_template(payload.name)
    except (KeyError, ValueError, RuntimeError) as exc:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"installed": True, "name": payload.name, "path": path}


@router.post("/v1/dashboard/alerts/evaluate")
def dashboard_evaluate_alerts(payload: AlertEvaluatePayload, request: Request) -> dict[str, Any]:
    runtime = request.app.state.runtime
    principal = runtime.dashboard.authorize_request(request.headers, permission="alert:read")
    return runtime.dashboard.evaluate_alerts(principal, last=payload.last)
