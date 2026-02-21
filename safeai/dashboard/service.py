"""Phase 5 dashboard and enterprise service layer."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping

import yaml  # type: ignore[import-untyped]
from fastapi import HTTPException

from safeai.api import SafeAI
from safeai.config.models import DashboardConfig, DashboardUserConfig
from safeai.core.approval import ApprovalRequest

_ROLE_PERMISSIONS: dict[str, set[str]] = {
    "viewer": {
        "dashboard:view",
        "audit:read",
        "incident:read",
        "approval:read",
        "compliance:report",
        "tenant:read",
        "alert:read",
    },
    "approver": {
        "dashboard:view",
        "audit:read",
        "incident:read",
        "approval:read",
        "approval:decide",
        "compliance:report",
        "tenant:read",
        "alert:read",
    },
    "auditor": {
        "dashboard:view",
        "audit:read",
        "incident:read",
        "approval:read",
        "compliance:report",
        "tenant:read",
        "alert:read",
    },
    "admin": {"*"},
}


@dataclass(frozen=True)
class DashboardPrincipal:
    user_id: str
    role: str
    tenant_scope: tuple[str, ...]


@dataclass(frozen=True)
class TenantPolicySet:
    tenant_id: str
    name: str
    policy_files: tuple[str, ...]
    agents: tuple[str, ...]


@dataclass(frozen=True)
class AlertRule:
    rule_id: str
    name: str
    threshold: int
    window: str
    filters: dict[str, Any]
    channels: tuple[str, ...]


class TenantPolicySetManager:
    """File-backed tenant policy set registry."""

    def __init__(self, *, file_path: Path | None, default_tenant_id: str = "default") -> None:
        self.file_path = file_path
        self.default_tenant_id = _token(default_tenant_id) or "default"
        self._sets: dict[str, TenantPolicySet] = {}
        self._load()
        if not self._sets:
            self.upsert(
                TenantPolicySet(
                    tenant_id=self.default_tenant_id,
                    name="Default Tenant",
                    policy_files=("policies/default.yaml",),
                    agents=("default-agent",),
                )
            )

    def list_sets(self) -> list[TenantPolicySet]:
        return sorted(self._sets.values(), key=lambda item: item.tenant_id)

    def get(self, tenant_id: str) -> TenantPolicySet | None:
        token = _token(tenant_id)
        if not token:
            return None
        return self._sets.get(token)

    def upsert(self, policy_set: TenantPolicySet) -> None:
        self._sets[policy_set.tenant_id] = policy_set
        self._persist()

    def resolve_agent_tenant(self, agent_id: str | None) -> str:
        token = _token(agent_id)
        if not token:
            return self.default_tenant_id
        for row in self._sets.values():
            if token in row.agents:
                return row.tenant_id
        return self.default_tenant_id

    def _load(self) -> None:
        if self.file_path is None:
            return
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            return
        raw = yaml.safe_load(self.file_path.read_text(encoding="utf-8")) or {}
        if not isinstance(raw, dict):
            return
        rows = raw.get("tenants", [])
        if not isinstance(rows, list):
            return
        loaded: dict[str, TenantPolicySet] = {}
        for item in rows:
            if not isinstance(item, dict):
                continue
            tenant_id = _token(item.get("tenant_id"))
            if not tenant_id:
                continue
            name = _token(item.get("name")) or tenant_id
            policy_files = _normalize_tokens(item.get("policy_files", []))
            agents = _normalize_tokens(item.get("agents", []))
            loaded[tenant_id] = TenantPolicySet(
                tenant_id=tenant_id,
                name=name,
                policy_files=policy_files,
                agents=agents,
            )
        self._sets = loaded

    def _persist(self) -> None:
        if self.file_path is None:
            return
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": "v1alpha1",
            "tenants": [
                {
                    "tenant_id": row.tenant_id,
                    "name": row.name,
                    "policy_files": list(row.policy_files),
                    "agents": list(row.agents),
                }
                for row in self.list_sets()
            ],
        }
        self.file_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


class AlertRuleManager:
    """File-backed alert rules and alert event sink."""

    def __init__(self, *, rules_file: Path | None, alert_log_file: Path | None) -> None:
        self.rules_file = rules_file
        self.alert_log_file = alert_log_file
        self._rules: dict[str, AlertRule] = {}
        self._load()

    def list_rules(self) -> list[AlertRule]:
        return sorted(self._rules.values(), key=lambda row: row.rule_id)

    def upsert(self, rule: AlertRule) -> None:
        self._rules[rule.rule_id] = rule
        self._persist_rules()

    def recent_alerts(self, *, limit: int = 20) -> list[dict[str, Any]]:
        if self.alert_log_file is None or not self.alert_log_file.exists():
            return []
        rows: list[dict[str, Any]] = []
        for line in self.alert_log_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except Exception:
                continue
            if isinstance(payload, dict):
                rows.append(payload)
        rows.sort(key=lambda item: str(item.get("timestamp", "")), reverse=True)
        if limit <= 0:
            return rows
        return rows[:limit]

    def evaluate(self, *, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        now = datetime.now(timezone.utc)
        triggered: list[dict[str, Any]] = []
        for rule in self.list_rules():
            cutoff = now - _parse_duration(rule.window)
            matched = [event for event in events if _event_within(event, cutoff) and _matches_rule(event, rule)]
            if len(matched) < rule.threshold:
                continue
            tenant_ids = list(_normalize_tokens(_tenant_from_event_metadata(item) for item in matched))
            alert = {
                "alert_id": f"alr_{now.strftime('%Y%m%d%H%M%S')}_{rule.rule_id}",
                "rule_id": rule.rule_id,
                "rule_name": rule.name,
                "threshold": rule.threshold,
                "window": rule.window,
                "count": len(matched),
                "channels": list(rule.channels),
                "tenant_ids": [tenant for tenant in tenant_ids if tenant],
                "sample_event_ids": [str(item.get("event_id", "")) for item in matched[:20]],
                "timestamp": now.isoformat(),
            }
            self._notify(alert)
            triggered.append(alert)
        return triggered

    def _load(self) -> None:
        if self.rules_file is None:
            return
        self.rules_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.rules_file.exists():
            return
        raw = yaml.safe_load(self.rules_file.read_text(encoding="utf-8")) or {}
        if not isinstance(raw, dict):
            return
        rows = raw.get("alert_rules", [])
        if not isinstance(rows, list):
            return
        loaded: dict[str, AlertRule] = {}
        for item in rows:
            if not isinstance(item, dict):
                continue
            parsed = _parse_alert_rule(item)
            if parsed is None:
                continue
            loaded[parsed.rule_id] = parsed
        self._rules = loaded

    def _persist_rules(self) -> None:
        if self.rules_file is None:
            return
        self.rules_file.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": "v1alpha1",
            "alert_rules": [
                {
                    "rule_id": rule.rule_id,
                    "name": rule.name,
                    "threshold": rule.threshold,
                    "window": rule.window,
                    "filters": dict(rule.filters),
                    "channels": list(rule.channels),
                }
                for rule in self.list_rules()
            ],
        }
        self.rules_file.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    def _notify(self, alert: dict[str, Any]) -> None:
        channels = {str(item).strip().lower() for item in alert.get("channels", []) if str(item).strip()}
        if "file" not in channels or self.alert_log_file is None:
            return
        self.alert_log_file.parent.mkdir(parents=True, exist_ok=True)
        with self.alert_log_file.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(alert, separators=(",", ":"), ensure_ascii=True) + "\n")


class DashboardService:
    """Security operations dashboard and enterprise controls."""

    def __init__(self, *, sdk: SafeAI, config_path: str | Path, config: DashboardConfig) -> None:
        self.sdk = sdk
        self.config = config
        path = Path(config_path).expanduser().resolve()
        users: dict[str, DashboardUserConfig] = {}
        for row in config.users:
            token = _token(row.user_id)
            if token:
                users[token] = row
        self._users = users
        self._tenant_sets = TenantPolicySetManager(
            file_path=_resolve_optional_path(path, config.tenant_policy_file),
            default_tenant_id="default",
        )
        self._alerts = AlertRuleManager(
            rules_file=_resolve_optional_path(path, config.alert_rules_file),
            alert_log_file=_resolve_optional_path(path, config.alert_log_file),
        )

    def authorize_request(self, headers: Mapping[str, str], *, permission: str) -> DashboardPrincipal:
        if not self.config.enabled:
            raise HTTPException(status_code=404, detail="dashboard is disabled")
        principal = self._authenticate(headers)
        self._authorize(principal, permission=permission)
        return principal

    def render_dashboard_page(self) -> str:
        return _DASHBOARD_HTML

    def overview(self, principal: DashboardPrincipal, *, last: str = "24h") -> dict[str, Any]:
        events = self.query_events(principal, filters={"last": last, "limit": 5000, "newest_first": True})
        approvals = self.list_approvals(principal, status="pending", limit=200, newest_first=True)
        incidents = self.list_incidents(principal, last=last, limit=20)
        recent_alerts = self._alerts.recent_alerts(limit=20)
        visible_tenants = self.list_tenant_policy_sets(principal)
        return {
            "window": last,
            "events_total": len(events),
            "action_counts": _count_by(events, key="action"),
            "boundary_counts": _count_by(events, key="boundary"),
            "pending_approvals": len(approvals),
            "recent_incidents": incidents[:8],
            "recent_alerts": recent_alerts[:8],
            "tenants": visible_tenants,
        }

    def query_events(self, principal: DashboardPrincipal, *, filters: dict[str, Any]) -> list[dict[str, Any]]:
        rows = self.sdk.query_audit(**filters)
        return self._filter_events_by_tenant(rows, principal)

    def list_incidents(self, principal: DashboardPrincipal, *, last: str = "24h", limit: int = 100) -> list[dict[str, Any]]:
        rows = self.query_events(principal, filters={"last": last, "limit": max(limit * 5, 200), "newest_first": True})
        incident_rows = [row for row in rows if str(row.get("action")) in {"block", "redact", "require_approval"}]
        return incident_rows[: max(limit, 1)]

    def list_approvals(
        self,
        principal: DashboardPrincipal,
        *,
        status: str | None = None,
        limit: int = 100,
        newest_first: bool = True,
    ) -> list[dict[str, Any]]:
        rows = self.sdk.list_approval_requests(
            status=status,
            newest_first=newest_first,
            limit=max(limit * 5, 500),
        )
        visible = [row for row in rows if self._is_tenant_allowed(self._approval_tenant(row), principal)]
        visible.sort(key=lambda item: item.requested_at, reverse=newest_first)
        if limit > 0:
            visible = visible[:limit]
        return [self._approval_to_dict(item) for item in visible]

    def decide_approval(
        self,
        principal: DashboardPrincipal,
        *,
        request_id: str,
        decision: str,
        note: str | None = None,
    ) -> dict[str, Any]:
        row = self.sdk.approvals.get(request_id)
        if row is None:
            raise HTTPException(status_code=404, detail="approval request not found")
        if not self._is_tenant_allowed(self._approval_tenant(row), principal):
            raise HTTPException(status_code=404, detail="approval request not found")
        token = str(decision).strip().lower()
        if token == "approve":
            ok = self.sdk.approve_request(request_id, approver_id=principal.user_id, note=note)
        elif token == "deny":
            ok = self.sdk.deny_request(request_id, approver_id=principal.user_id, note=note)
        else:
            raise HTTPException(status_code=400, detail="decision must be 'approve' or 'deny'")
        if not ok:
            raise HTTPException(status_code=409, detail="approval request can no longer be decided")
        updated = self.sdk.approvals.get(request_id)
        if updated is None:
            raise HTTPException(status_code=500, detail="approval request disappeared after decision")
        return self._approval_to_dict(updated)

    def compliance_report(
        self,
        principal: DashboardPrincipal,
        *,
        since: str | None = None,
        until: str | None = None,
        last: str | None = "24h",
        limit: int = 20000,
    ) -> dict[str, Any]:
        events = self.query_events(
            principal,
            filters={"since": since, "until": until, "last": last, "limit": max(limit, 1), "newest_first": False},
        )
        approvals = self.sdk.list_approval_requests(limit=100000, newest_first=False)
        visible_approvals = [row for row in approvals if self._is_tenant_allowed(self._approval_tenant(row), principal)]
        if since or until or last:
            start_at, end_at = _window_bounds(since=since, until=until, last=last)
            visible_approvals = [
                row
                for row in visible_approvals
                if _approval_within_window(row, start_at=start_at, end_at=end_at)
            ]
        action_counts = _count_by(events, key="action")
        boundary_counts = _count_by(events, key="boundary")
        policy_counts = _count_by(events, key="policy_name")
        agent_counts = _count_by(events, key="agent_id")
        approval_counts = _count_by_approval_status(visible_approvals)
        memory_retention_events = [
            row
            for row in events
            if str(row.get("boundary")) == "memory" and str(_metadata(row).get("phase")) == "retention_purge"
        ]
        violation_count = sum(action_counts.get(key, 0) for key in ("block", "redact", "require_approval"))
        approval_latencies = [
            (row.decided_at - row.requested_at).total_seconds()
            for row in visible_approvals
            if row.decided_at is not None
        ]
        avg_latency = sum(approval_latencies) / len(approval_latencies) if approval_latencies else 0.0
        anomaly_flags: list[str] = []
        total_events = len(events)
        blocked = action_counts.get("block", 0)
        if total_events and blocked / total_events >= 0.1:
            anomaly_flags.append("blocked-rate>=10%")
        if approval_counts.get("pending", 0) >= 10:
            anomaly_flags.append("pending-approvals>=10")
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "window": {"since": since, "until": until, "last": last},
            "summary": {
                "total_events": total_events,
                "boundary_counts": boundary_counts,
                "action_counts": action_counts,
                "policy_violation_count": violation_count,
                "top_policies": sorted(policy_counts.items(), key=lambda item: item[1], reverse=True)[:10],
                "data_access_by_agent": sorted(agent_counts.items(), key=lambda item: item[1], reverse=True)[:10],
                "approval_stats": {
                    "counts": approval_counts,
                    "average_latency_seconds": round(avg_latency, 3),
                },
                "memory_retention_events": len(memory_retention_events),
                "anomaly_flags": anomaly_flags,
            },
            "evidence": {
                "sample_event_ids": [str(row.get("event_id", "")) for row in events[:20]],
                "sample_approval_ids": [row.request_id for row in visible_approvals[:20]],
            },
        }

    def list_tenant_policy_sets(self, principal: DashboardPrincipal) -> list[dict[str, Any]]:
        rows = self._tenant_sets.list_sets()
        if "*" not in principal.tenant_scope:
            rows = [row for row in rows if row.tenant_id in principal.tenant_scope]
        return [self._tenant_policy_to_dict(row) for row in rows]

    def get_tenant_policy_set(self, principal: DashboardPrincipal, tenant_id: str) -> dict[str, Any]:
        token = _token(tenant_id)
        if not token:
            raise HTTPException(status_code=400, detail="tenant_id is required")
        if "*" not in principal.tenant_scope and token not in principal.tenant_scope:
            raise HTTPException(status_code=403, detail="tenant not in scope")
        row = self._tenant_sets.get(token)
        if row is None:
            raise HTTPException(status_code=404, detail="tenant policy set not found")
        return self._tenant_policy_to_dict(row)

    def update_tenant_policy_set(
        self,
        principal: DashboardPrincipal,
        *,
        tenant_id: str,
        name: str | None = None,
        policy_files: list[str] | None = None,
        agents: list[str] | None = None,
    ) -> dict[str, Any]:
        token = _token(tenant_id)
        if not token:
            raise HTTPException(status_code=400, detail="tenant_id is required")
        if "*" not in principal.tenant_scope and token not in principal.tenant_scope:
            raise HTTPException(status_code=403, detail="tenant not in scope")
        current = self._tenant_sets.get(token)
        resolved_name = _token(name) or (current.name if current else token)
        resolved_files = _normalize_tokens(policy_files or (current.policy_files if current else []))
        resolved_agents = _normalize_tokens(agents or (current.agents if current else []))
        updated = TenantPolicySet(
            tenant_id=token,
            name=resolved_name,
            policy_files=resolved_files,
            agents=resolved_agents,
        )
        self._tenant_sets.upsert(updated)
        return self._tenant_policy_to_dict(updated)

    def list_alert_rules(self) -> list[dict[str, Any]]:
        return [self._alert_rule_to_dict(row) for row in self._alerts.list_rules()]

    def upsert_alert_rule(
        self,
        *,
        rule_id: str,
        name: str,
        threshold: int,
        window: str,
        filters: dict[str, Any] | None = None,
        channels: list[str] | None = None,
    ) -> dict[str, Any]:
        parsed = _parse_alert_rule(
            {
                "rule_id": rule_id,
                "name": name,
                "threshold": threshold,
                "window": window,
                "filters": filters or {},
                "channels": channels or ["file"],
            }
        )
        if parsed is None:
            raise HTTPException(status_code=400, detail="invalid alert rule payload")
        self._alerts.upsert(parsed)
        return self._alert_rule_to_dict(parsed)

    def evaluate_alerts(self, principal: DashboardPrincipal, *, last: str = "15m") -> dict[str, Any]:
        rows = self.query_events(principal, filters={"last": last, "limit": 20000, "newest_first": True})
        triggered = self._alerts.evaluate(events=rows)
        if "*" not in principal.tenant_scope:
            allowed = set(principal.tenant_scope)
            triggered = [
                row
                for row in triggered
                if not row.get("tenant_ids") or bool(allowed.intersection(set(row.get("tenant_ids", []))))
            ]
        return {"window": last, "triggered_count": len(triggered), "alerts": triggered}

    def _authenticate(self, headers: Mapping[str, str]) -> DashboardPrincipal:
        if not self.config.rbac_enabled:
            return DashboardPrincipal(user_id="rbac-disabled", role="admin", tenant_scope=("*",))
        user_id = _header_value(headers, self.config.user_header)
        if not user_id:
            raise HTTPException(status_code=401, detail=f"missing '{self.config.user_header}' header")
        user = self._users.get(user_id)
        if user is None:
            raise HTTPException(status_code=403, detail="dashboard user is not registered")
        tenant_scope = tuple(user.tenants or [self._tenant_sets.default_tenant_id])
        selected_tenant = _header_value(headers, self.config.tenant_header)
        if selected_tenant:
            if "*" not in tenant_scope and selected_tenant not in tenant_scope:
                raise HTTPException(status_code=403, detail="requested tenant is outside user scope")
            tenant_scope = (selected_tenant,)
        return DashboardPrincipal(
            user_id=_token(user.user_id) or "unknown",
            role=_token(user.role) or "viewer",
            tenant_scope=tuple(tenant_scope),
        )

    def _authorize(self, principal: DashboardPrincipal, *, permission: str) -> None:
        allowed = _ROLE_PERMISSIONS.get(principal.role, set())
        if "*" in allowed or permission in allowed:
            return
        raise HTTPException(status_code=403, detail=f"role '{principal.role}' lacks '{permission}' permission")

    def _filter_events_by_tenant(
        self, rows: list[dict[str, Any]], principal: DashboardPrincipal
    ) -> list[dict[str, Any]]:
        if "*" in principal.tenant_scope:
            return rows
        allowed = set(principal.tenant_scope)
        return [row for row in rows if self._event_tenant(row) in allowed]

    def _event_tenant(self, event: dict[str, Any]) -> str:
        metadata = _metadata(event)
        direct = _token(metadata.get("tenant_id"))
        if direct:
            return direct
        for key in ("agent_id", "source_agent_id", "destination_agent_id"):
            agent = _token(event.get(key))
            if agent:
                return self._tenant_sets.resolve_agent_tenant(agent)
        return self._tenant_sets.default_tenant_id

    def _approval_tenant(self, row: ApprovalRequest) -> str:
        metadata = row.metadata if isinstance(row.metadata, dict) else {}
        direct = _token(metadata.get("tenant_id"))
        if direct:
            return direct
        return self._tenant_sets.resolve_agent_tenant(row.agent_id)

    @staticmethod
    def _is_tenant_allowed(tenant_id: str, principal: DashboardPrincipal) -> bool:
        return "*" in principal.tenant_scope or tenant_id in principal.tenant_scope

    @staticmethod
    def _approval_to_dict(row: ApprovalRequest) -> dict[str, Any]:
        return {
            "request_id": row.request_id,
            "status": row.status,
            "reason": row.reason,
            "policy_name": row.policy_name,
            "agent_id": row.agent_id,
            "tool_name": row.tool_name,
            "session_id": row.session_id,
            "action_type": row.action_type,
            "data_tags": list(row.data_tags),
            "requested_at": row.requested_at.isoformat(),
            "expires_at": row.expires_at.isoformat(),
            "decided_at": row.decided_at.isoformat() if row.decided_at else None,
            "approver_id": row.approver_id,
            "decision_note": row.decision_note,
            "metadata": dict(row.metadata or {}),
        }

    @staticmethod
    def _tenant_policy_to_dict(row: TenantPolicySet) -> dict[str, Any]:
        return {
            "tenant_id": row.tenant_id,
            "name": row.name,
            "policy_files": list(row.policy_files),
            "agents": list(row.agents),
        }

    @staticmethod
    def _alert_rule_to_dict(row: AlertRule) -> dict[str, Any]:
        return {
            "rule_id": row.rule_id,
            "name": row.name,
            "threshold": row.threshold,
            "window": row.window,
            "filters": dict(row.filters),
            "channels": list(row.channels),
        }


def _count_by(rows: list[dict[str, Any]], *, key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        token = _token(row.get(key)) or "unknown"
        counts[token] = counts.get(token, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def _count_by_approval_status(rows: list[ApprovalRequest]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        token = _token(row.status) or "unknown"
        counts[token] = counts.get(token, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def _metadata(event: dict[str, Any]) -> dict[str, Any]:
    metadata = event.get("metadata", {})
    return metadata if isinstance(metadata, dict) else {}


def _header_value(headers: Mapping[str, str], key: str) -> str | None:
    target = _token(key)
    if not target:
        return None
    for raw_key, raw_value in headers.items():
        if _token(raw_key) == target:
            value = _token(raw_value)
            return value
    return None


def _token(value: Any) -> str | None:
    if value is None:
        return None
    token = str(value).strip().lower()
    return token or None


def _normalize_tokens(values: Any) -> tuple[str, ...]:
    rows: set[str] = set()
    iterable: Iterable[Any]
    if isinstance(values, (list, tuple, set, frozenset)):
        iterable = values
    elif isinstance(values, (str, bytes)):
        iterable = [values]
    elif isinstance(values, Iterable):
        iterable = values
    else:
        iterable = [values]
    for item in iterable:
        token = _token(item)
        if token:
            rows.add(token)
    return tuple(sorted(rows))


def _parse_duration(value: str) -> timedelta:
    token = str(value).strip().lower()
    if len(token) < 2 or token[-1] not in {"s", "m", "h", "d"}:
        raise ValueError(f"Invalid duration '{value}'. Use 30s, 15m, 2h, 7d.")
    amount = int(token[:-1])
    if token[-1] == "s":
        return timedelta(seconds=amount)
    if token[-1] == "m":
        return timedelta(minutes=amount)
    if token[-1] == "h":
        return timedelta(hours=amount)
    return timedelta(days=amount)


def _window_bounds(*, since: str | None, until: str | None, last: str | None) -> tuple[datetime | None, datetime | None]:
    end_at = _parse_timestamp(until) if until else None
    start_at = _parse_timestamp(since) if since else None
    if last:
        end = datetime.now(timezone.utc)
        return end - _parse_duration(last), end
    return start_at, end_at


def _approval_within_window(
    row: ApprovalRequest, *, start_at: datetime | None, end_at: datetime | None
) -> bool:
    when = row.requested_at
    if start_at and when < start_at:
        return False
    if end_at and when > end_at:
        return False
    return True


def _parse_timestamp(value: str | None) -> datetime | None:
    token = _token(value)
    if not token:
        return None
    parsed = datetime.fromisoformat(token.replace("z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _event_within(event: dict[str, Any], cutoff: datetime) -> bool:
    token = _token(event.get("timestamp"))
    if not token:
        return False
    try:
        parsed = datetime.fromisoformat(token.replace("z", "+00:00"))
    except ValueError:
        return False
    when = parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    return when >= cutoff


def _matches_rule(event: dict[str, Any], rule: AlertRule) -> bool:
    filters = rule.filters or {}
    boundaries = {_token(item) for item in filters.get("boundaries", []) if _token(item)}
    actions = {_token(item) for item in filters.get("actions", []) if _token(item)}
    policies = {_token(item) for item in filters.get("policies", []) if _token(item)}
    agents = {_token(item) for item in filters.get("agents", []) if _token(item)}
    tags = {_token(item) for item in filters.get("tags", []) if _token(item)}
    if boundaries and _token(event.get("boundary")) not in boundaries:
        return False
    if actions and _token(event.get("action")) not in actions:
        return False
    if policies and _token(event.get("policy_name")) not in policies:
        return False
    if agents and _token(event.get("agent_id")) not in agents:
        return False
    if tags:
        row_tags = set(_normalize_tokens(event.get("data_tags", [])))
        if not row_tags.intersection(tags):
            return False
    return True


def _parse_alert_rule(payload: dict[str, Any]) -> AlertRule | None:
    rule_id = _token(payload.get("rule_id"))
    name = str(payload.get("name", "")).strip()
    if not rule_id or not name:
        return None
    threshold = int(payload.get("threshold", 1))
    window = str(payload.get("window", "15m")).strip() or "15m"
    channels = _normalize_tokens(payload.get("channels", ["file"]))
    if not channels:
        channels = ("file",)
    filters = payload.get("filters", {})
    if not isinstance(filters, dict):
        filters = {}
    return AlertRule(
        rule_id=rule_id,
        name=name,
        threshold=max(threshold, 1),
        window=window,
        filters=dict(filters),
        channels=channels,
    )


def _tenant_from_event_metadata(event: dict[str, Any]) -> str | None:
    metadata = _metadata(event)
    return _token(metadata.get("tenant_id"))


def _resolve_optional_path(config_path: Path, value: str | None) -> Path | None:
    token = str(value).strip() if value is not None else ""
    if not token:
        return None
    raw = Path(token).expanduser()
    if raw.is_absolute():
        return raw.resolve()
    return (config_path.parent / raw).resolve()


_DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>SafeAI Security Dashboard</title>
  <style>
    :root {
      --ink-900: #0f172a;
      --ink-700: #1f2937;
      --ink-500: #475569;
      --line: #d5dde8;
      --mist: #f6f8fb;
      --accent-safe: #0f9d7f;
      --accent-risk: #dc4c3e;
      --accent-warn: #c98a1a;
      --card: #ffffff;
      --glow: radial-gradient(circle at 20% 0%, #dcf7ef 0%, transparent 35%),
              radial-gradient(circle at 100% 20%, #dfe7ff 0%, transparent 45%);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
      background: var(--glow), var(--mist);
      color: var(--ink-900);
    }
    .wrap { max-width: 1200px; margin: 0 auto; padding: 20px; }
    .head {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
      flex-wrap: wrap;
      margin-bottom: 16px;
    }
    .title { font-size: 1.4rem; font-weight: 700; letter-spacing: 0.01em; }
    .toolbar {
      display: grid;
      grid-template-columns: repeat(4, minmax(120px, 1fr));
      gap: 8px;
      width: min(760px, 100%);
    }
    input, button, select {
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 10px 12px;
      background: #fff;
      color: var(--ink-900);
      font: inherit;
    }
    button {
      background: var(--ink-900);
      color: #fff;
      border: none;
      cursor: pointer;
    }
    button.secondary { background: #2b3447; }
    button.warn { background: var(--accent-warn); color: #111827; }
    button.danger { background: var(--accent-risk); }
    .grid {
      display: grid;
      grid-template-columns: repeat(12, 1fr);
      gap: 12px;
    }
    .card {
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 14px;
      box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);
    }
    .kpi { grid-column: span 3; min-height: 96px; }
    .kpi h3 { margin: 0 0 8px; font-size: 0.85rem; color: var(--ink-500); font-weight: 600; }
    .kpi .v { font-size: 1.7rem; font-weight: 700; }
    .panel-8 { grid-column: span 8; }
    .panel-4 { grid-column: span 4; }
    .panel-12 { grid-column: span 12; }
    .subtle { color: var(--ink-500); font-size: 0.9rem; }
    table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
    th, td { text-align: left; padding: 8px; border-bottom: 1px solid #e8edf5; vertical-align: top; }
    th { color: var(--ink-500); font-weight: 600; }
    .mono { font-family: "JetBrains Mono", "SFMono-Regular", monospace; }
    .pill {
      display: inline-block;
      padding: 2px 8px;
      border-radius: 999px;
      font-size: 0.75rem;
      font-weight: 600;
    }
    .allow { background: #dcfce7; color: #166534; }
    .block { background: #fee2e2; color: #991b1b; }
    .redact { background: #fef3c7; color: #92400e; }
    .pending { background: #e0e7ff; color: #3730a3; }
    #status { min-height: 22px; font-size: 0.9rem; margin: 8px 0 12px; color: var(--ink-500); }
    pre {
      margin: 0;
      font-family: "JetBrains Mono", "SFMono-Regular", monospace;
      font-size: 0.82rem;
      background: #0f172a;
      color: #dbeafe;
      border-radius: 12px;
      padding: 12px;
      max-height: 300px;
      overflow: auto;
    }
    @media (max-width: 1000px) {
      .toolbar { grid-template-columns: repeat(2, minmax(120px, 1fr)); }
      .kpi, .panel-8, .panel-4 { grid-column: span 12; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="head">
      <div class="title">SafeAI Security Dashboard</div>
      <div class="toolbar">
        <input id="user" placeholder="x-safeai-user" value="security-admin" />
        <input id="tenant" placeholder="x-safeai-tenant (optional)" />
        <select id="window">
          <option value="15m">Last 15m</option>
          <option value="1h">Last 1h</option>
          <option value="24h" selected>Last 24h</option>
          <option value="7d">Last 7d</option>
        </select>
        <button id="refresh">Refresh</button>
      </div>
    </div>

    <div id="status"></div>

    <div class="grid">
      <section class="card kpi"><h3>Events</h3><div id="kpi-events" class="v">-</div></section>
      <section class="card kpi"><h3>Pending Approvals</h3><div id="kpi-approvals" class="v">-</div></section>
      <section class="card kpi"><h3>Blocked</h3><div id="kpi-blocked" class="v">-</div></section>
      <section class="card kpi"><h3>Redacted</h3><div id="kpi-redacted" class="v">-</div></section>

      <section class="card panel-8">
        <h3>Approval Queue</h3>
        <table>
          <thead><tr><th>Request</th><th>Agent</th><th>Tool</th><th>Reason</th><th>Action</th></tr></thead>
          <tbody id="approvals-body"></tbody>
        </table>
      </section>

      <section class="card panel-4">
        <h3>Tenant Policy Sets</h3>
        <div id="tenant-list" class="subtle">No data</div>
      </section>

      <section class="card panel-12">
        <h3>Recent Incidents</h3>
        <table>
          <thead><tr><th>Time</th><th>Boundary</th><th>Agent</th><th>Action</th><th>Policy</th><th>Reason</th></tr></thead>
          <tbody id="incidents-body"></tbody>
        </table>
      </section>

      <section class="card panel-12">
        <h3>Compliance Report</h3>
        <div style="display:flex; gap:8px; flex-wrap:wrap; margin-bottom:10px;">
          <button id="report-btn" class="secondary">Generate Report</button>
          <button id="alert-btn" class="warn">Evaluate Alerts</button>
        </div>
        <pre id="report-json">{}</pre>
      </section>
    </div>
  </div>

  <script>
    const statusBox = document.getElementById("status");
    const userInput = document.getElementById("user");
    const tenantInput = document.getElementById("tenant");
    const windowInput = document.getElementById("window");

    function authHeaders() {
      const h = {"x-safeai-user": userInput.value.trim()};
      const tenant = tenantInput.value.trim();
      if (tenant) h["x-safeai-tenant"] = tenant;
      return h;
    }

    function setStatus(msg, bad=false) {
      statusBox.textContent = msg;
      statusBox.style.color = bad ? "#b91c1c" : "#475569";
    }

    async function api(path, options={}) {
      const headers = Object.assign({}, authHeaders(), options.headers || {});
      if (options.body && !headers["content-type"]) headers["content-type"] = "application/json";
      const res = await fetch(path, Object.assign({}, options, {headers}));
      if (!res.ok) {
        const txt = await res.text();
        throw new Error(`${res.status} ${res.statusText}: ${txt}`);
      }
      return res.json();
    }

    function badge(action) {
      const cls = action === "block" ? "block" : action === "redact" ? "redact" : action === "pending" ? "pending" : "allow";
      return `<span class="pill ${cls}">${action}</span>`;
    }

    async function loadOverview() {
      const last = windowInput.value;
      const overview = await api(`/v1/dashboard/overview?last=${encodeURIComponent(last)}`);
      document.getElementById("kpi-events").textContent = overview.events_total;
      document.getElementById("kpi-approvals").textContent = overview.pending_approvals;
      document.getElementById("kpi-blocked").textContent = overview.action_counts.block || 0;
      document.getElementById("kpi-redacted").textContent = overview.action_counts.redact || 0;
      document.getElementById("tenant-list").textContent = (overview.tenants || []).map(t => `${t.tenant_id} (${(t.policy_files || []).length} policy files)`).join(" | ") || "No tenants";
      setStatus(`Loaded window ${last}`);
    }

    async function loadApprovals() {
      const rows = await api("/v1/dashboard/approvals?status=pending&limit=25");
      const body = document.getElementById("approvals-body");
      body.innerHTML = "";
      rows.forEach(row => {
        const tr = document.createElement("tr");
        tr.innerHTML = `<td class="mono">${row.request_id}</td><td>${row.agent_id}</td><td>${row.tool_name}</td><td>${row.reason}</td><td>
          <button data-act="approve" data-id="${row.request_id}">Approve</button>
          <button data-act="deny" data-id="${row.request_id}" class="danger">Deny</button>
        </td>`;
        body.appendChild(tr);
      });
      body.querySelectorAll("button").forEach(btn => btn.addEventListener("click", async () => {
        const reqId = btn.getAttribute("data-id");
        const decision = btn.getAttribute("data-act");
        try {
          await api(`/v1/dashboard/approvals/${encodeURIComponent(reqId)}/${decision}`, {
            method: "POST",
            body: JSON.stringify({note: `dashboard-${decision}`})
          });
          setStatus(`Request ${reqId} ${decision}d`);
          await refresh();
        } catch (err) {
          setStatus(String(err), true);
        }
      }));
    }

    async function loadIncidents() {
      const last = windowInput.value;
      const rows = await api(`/v1/dashboard/incidents?last=${encodeURIComponent(last)}&limit=25`);
      const body = document.getElementById("incidents-body");
      body.innerHTML = "";
      rows.forEach(row => {
        const tr = document.createElement("tr");
        tr.innerHTML = `<td class="mono">${row.timestamp || "-"}</td><td>${row.boundary || "-"}</td><td>${row.agent_id || "-"}</td><td>${badge(row.action || "unknown")}</td><td>${row.policy_name || "-"}</td><td>${row.reason || "-"}</td>`;
        body.appendChild(tr);
      });
    }

    async function generateReport() {
      const payload = {last: windowInput.value};
      const report = await api("/v1/dashboard/compliance/report", {
        method: "POST",
        body: JSON.stringify(payload)
      });
      document.getElementById("report-json").textContent = JSON.stringify(report, null, 2);
      setStatus("Compliance report generated");
    }

    async function evaluateAlerts() {
      const payload = {last: windowInput.value};
      const result = await api("/v1/dashboard/alerts/evaluate", {
        method: "POST",
        body: JSON.stringify(payload)
      });
      document.getElementById("report-json").textContent = JSON.stringify(result, null, 2);
      setStatus(`Alert evaluation complete (${result.triggered_count} triggered)`);
    }

    async function refresh() {
      try {
        await Promise.all([loadOverview(), loadApprovals(), loadIncidents()]);
      } catch (err) {
        setStatus(String(err), true);
      }
    }

    document.getElementById("refresh").addEventListener("click", refresh);
    document.getElementById("report-btn").addEventListener("click", async () => {
      try { await generateReport(); } catch (err) { setStatus(String(err), true); }
    });
    document.getElementById("alert-btn").addEventListener("click", async () => {
      try { await evaluateAlerts(); } catch (err) { setStatus(String(err), true); }
    });
    refresh();
  </script>
</body>
</html>
"""
