"""Approval workflow manager for high-risk action gating."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Literal, cast
from uuid import uuid4

ApprovalStatus = Literal["pending", "approved", "denied", "expired"]
Clock = Callable[[], datetime]


@dataclass(frozen=True)
class ApprovalRequest:
    request_id: str
    status: ApprovalStatus
    reason: str
    policy_name: str | None
    agent_id: str
    tool_name: str
    session_id: str | None
    action_type: str
    data_tags: list[str]
    requested_at: datetime
    expires_at: datetime
    decided_at: datetime | None = None
    approver_id: str | None = None
    decision_note: str | None = None
    metadata: dict[str, Any] | None = None
    dedupe_key: str | None = None

    def is_expired(self, *, now: datetime) -> bool:
        return self.expires_at <= now


@dataclass(frozen=True)
class ApprovalValidationResult:
    allowed: bool
    reason: str
    request: ApprovalRequest | None


class ApprovalManager:
    """Stateful approval gate with optional file-backed persistence."""

    def __init__(
        self,
        *,
        file_path: str | Path | None = None,
        default_ttl: str = "30m",
        clock: Clock | None = None,
    ) -> None:
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._default_ttl = default_ttl
        self._requests: dict[str, ApprovalRequest] = {}
        self._file_path = Path(file_path).expanduser().resolve() if file_path else None
        self._last_mtime_ns: int | None = None
        self._load()

    def create_request(
        self,
        *,
        reason: str,
        policy_name: str | None,
        agent_id: str,
        tool_name: str,
        session_id: str | None = None,
        action_type: str = "tool_call",
        data_tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        ttl: str | None = None,
        dedupe_key: str | None = None,
    ) -> ApprovalRequest:
        self._reload_if_changed()
        now = self._clock()
        normalized_dedupe = _normalize_optional_token(dedupe_key)
        if normalized_dedupe:
            existing = self._find_pending_by_dedupe(normalized_dedupe, now=now)
            if existing is not None:
                return existing

        duration = _parse_duration(ttl or self._default_ttl)
        request = ApprovalRequest(
            request_id=f"apr_{uuid4().hex[:12]}",
            status="pending",
            reason=str(reason).strip(),
            policy_name=_normalize_optional_token(policy_name),
            agent_id=_normalize_required_token(agent_id, field_name="agent_id"),
            tool_name=_normalize_required_token(tool_name, field_name="tool_name"),
            session_id=_normalize_optional_token(session_id),
            action_type=_normalize_optional_token(action_type) or "tool_call",
            data_tags=sorted({str(tag).strip().lower() for tag in (data_tags or []) if str(tag).strip()}),
            requested_at=now,
            expires_at=now + duration,
            metadata=dict(metadata or {}),
            dedupe_key=normalized_dedupe,
        )
        self._requests[request.request_id] = request
        self._persist()
        return request

    def get(self, request_id: str) -> ApprovalRequest | None:
        self._reload_if_changed()
        token = _normalize_optional_token(request_id)
        if not token:
            return None
        row = self._requests.get(token)
        if row is None:
            return None
        if row.status == "pending" and row.is_expired(now=self._clock()):
            row = row.__class__(**{**row.__dict__, "status": "expired"})
            self._requests[row.request_id] = row
            self._persist()
        return row

    def list_requests(
        self,
        *,
        status: ApprovalStatus | None = None,
        agent_id: str | None = None,
        tool_name: str | None = None,
        newest_first: bool = True,
        limit: int = 100,
    ) -> list[ApprovalRequest]:
        self._reload_if_changed()
        now = self._clock()
        rows: list[ApprovalRequest] = []
        for item in self._requests.values():
            row = item
            if row.status == "pending" and row.is_expired(now=now):
                row = row.__class__(**{**row.__dict__, "status": "expired"})
                self._requests[row.request_id] = row
            if status and row.status != status:
                continue
            if agent_id and row.agent_id != _normalize_required_token(agent_id, field_name="agent_id"):
                continue
            if tool_name and row.tool_name != _normalize_required_token(tool_name, field_name="tool_name"):
                continue
            rows.append(row)
        if rows:
            self._persist()
        rows.sort(key=lambda item: item.requested_at, reverse=newest_first)
        if limit <= 0:
            return rows
        return rows[:limit]

    def approve(self, request_id: str, *, approver_id: str, note: str | None = None) -> bool:
        return self._decide(
            request_id=request_id,
            status="approved",
            approver_id=approver_id,
            note=note,
        )

    def deny(self, request_id: str, *, approver_id: str, note: str | None = None) -> bool:
        return self._decide(
            request_id=request_id,
            status="denied",
            approver_id=approver_id,
            note=note,
        )

    def validate(
        self,
        request_id: str,
        *,
        agent_id: str,
        tool_name: str,
        session_id: str | None = None,
    ) -> ApprovalValidationResult:
        row = self.get(request_id)
        if row is None:
            return ApprovalValidationResult(
                allowed=False,
                reason=f"approval request '{request_id}' not found",
                request=None,
            )
        if row.status == "expired":
            return ApprovalValidationResult(
                allowed=False,
                reason=f"approval request '{request_id}' expired",
                request=row,
            )
        if row.status == "denied":
            return ApprovalValidationResult(
                allowed=False,
                reason=f"approval request '{request_id}' denied",
                request=row,
            )
        if row.status == "pending":
            return ApprovalValidationResult(
                allowed=False,
                reason=f"approval request '{request_id}' pending",
                request=row,
            )

        normalized_agent = _normalize_required_token(agent_id, field_name="agent_id")
        if row.agent_id != normalized_agent:
            return ApprovalValidationResult(
                allowed=False,
                reason="approval request agent binding mismatch",
                request=row,
            )
        normalized_tool = _normalize_required_token(tool_name, field_name="tool_name")
        if row.tool_name != normalized_tool:
            return ApprovalValidationResult(
                allowed=False,
                reason="approval request tool binding mismatch",
                request=row,
            )
        normalized_session = _normalize_optional_token(session_id)
        if row.session_id and row.session_id != normalized_session:
            return ApprovalValidationResult(
                allowed=False,
                reason="approval request session binding mismatch",
                request=row,
            )
        return ApprovalValidationResult(
            allowed=True,
            reason="approval request approved",
            request=row,
        )

    def purge_expired(self) -> int:
        self._reload_if_changed()
        now = self._clock()
        purged = 0
        for request_id in list(self._requests.keys()):
            row = self._requests[request_id]
            if row.status == "pending" and row.is_expired(now=now):
                self._requests.pop(request_id, None)
                purged += 1
        if purged:
            self._persist()
        return purged

    def _decide(
        self,
        *,
        request_id: str,
        status: ApprovalStatus,
        approver_id: str,
        note: str | None,
    ) -> bool:
        self._reload_if_changed()
        token = _normalize_required_token(request_id, field_name="request_id")
        row = self._requests.get(token)
        if row is None:
            return False
        if row.status != "pending" or row.is_expired(now=self._clock()):
            return False
        updated = row.__class__(
            **{
                **row.__dict__,
                "status": status,
                "approver_id": _normalize_required_token(approver_id, field_name="approver_id"),
                "decision_note": _normalize_optional_token(note),
                "decided_at": self._clock(),
            }
        )
        self._requests[token] = updated
        self._persist()
        return True

    def _find_pending_by_dedupe(self, dedupe_key: str, *, now: datetime) -> ApprovalRequest | None:
        for row in self._requests.values():
            if row.dedupe_key != dedupe_key:
                continue
            if row.status != "pending":
                continue
            if row.is_expired(now=now):
                continue
            return row
        return None

    def _reload_if_changed(self) -> None:
        if self._file_path is None or not self._file_path.exists():
            return
        try:
            mtime_ns = self._file_path.stat().st_mtime_ns
        except OSError:
            return
        if self._last_mtime_ns is not None and mtime_ns == self._last_mtime_ns:
            return
        self._load()

    def _load(self) -> None:
        if self._file_path is None:
            return
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self._file_path.exists():
            self._file_path.write_text("", encoding="utf-8")
            try:
                self._last_mtime_ns = self._file_path.stat().st_mtime_ns
            except OSError:
                self._last_mtime_ns = None
            return

        rows: dict[str, ApprovalRequest] = {}
        for line in self._file_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
                row = _request_from_payload(payload)
            except Exception:
                continue
            rows[row.request_id] = row
        self._requests = rows
        try:
            self._last_mtime_ns = self._file_path.stat().st_mtime_ns
        except OSError:
            self._last_mtime_ns = None

    def _persist(self) -> None:
        if self._file_path is None:
            return
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        rows = sorted(self._requests.values(), key=lambda item: item.requested_at)
        encoded = "\n".join(json.dumps(_request_to_payload(row), separators=(",", ":"), ensure_ascii=True) for row in rows)
        self._file_path.write_text(encoded + ("\n" if encoded else ""), encoding="utf-8")
        try:
            self._last_mtime_ns = self._file_path.stat().st_mtime_ns
        except OSError:
            self._last_mtime_ns = None


def _request_to_payload(request: ApprovalRequest) -> dict[str, Any]:
    return {
        "request_id": request.request_id,
        "status": request.status,
        "reason": request.reason,
        "policy_name": request.policy_name,
        "agent_id": request.agent_id,
        "tool_name": request.tool_name,
        "session_id": request.session_id,
        "action_type": request.action_type,
        "data_tags": list(request.data_tags),
        "requested_at": request.requested_at.isoformat(),
        "expires_at": request.expires_at.isoformat(),
        "decided_at": request.decided_at.isoformat() if request.decided_at else None,
        "approver_id": request.approver_id,
        "decision_note": request.decision_note,
        "metadata": dict(request.metadata or {}),
        "dedupe_key": request.dedupe_key,
    }


def _request_from_payload(payload: dict[str, Any]) -> ApprovalRequest:
    return ApprovalRequest(
        request_id=_normalize_required_token(payload.get("request_id"), field_name="request_id"),
        status=_normalize_status(payload.get("status")),
        reason=_normalize_required_token(payload.get("reason"), field_name="reason"),
        policy_name=_normalize_optional_token(payload.get("policy_name")),
        agent_id=_normalize_required_token(payload.get("agent_id"), field_name="agent_id"),
        tool_name=_normalize_required_token(payload.get("tool_name"), field_name="tool_name"),
        session_id=_normalize_optional_token(payload.get("session_id")),
        action_type=_normalize_optional_token(payload.get("action_type")) or "tool_call",
        data_tags=sorted(
            {
                str(tag).strip().lower()
                for tag in (payload.get("data_tags") or [])
                if str(tag).strip()
            }
        ),
        requested_at=_parse_when(payload.get("requested_at")),
        expires_at=_parse_when(payload.get("expires_at")),
        decided_at=_parse_optional_when(payload.get("decided_at")),
        approver_id=_normalize_optional_token(payload.get("approver_id")),
        decision_note=_normalize_optional_token(payload.get("decision_note")),
        metadata=dict(payload.get("metadata") or {}),
        dedupe_key=_normalize_optional_token(payload.get("dedupe_key")),
    )


def _parse_when(value: Any) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _parse_optional_when(value: Any) -> datetime | None:
    if value is None:
        return None
    return _parse_when(value)


def _normalize_optional_token(value: Any) -> str | None:
    if value is None:
        return None
    token = str(value).strip()
    return token or None


def _normalize_required_token(value: Any, *, field_name: str) -> str:
    token = _normalize_optional_token(value)
    if not token:
        raise ValueError(f"{field_name} is required")
    return token


def _parse_duration(value: str) -> timedelta:
    match = re.match(r"^\s*(\d+)\s*([smhdw])\s*$", str(value).lower())
    if not match:
        raise ValueError(f"Invalid duration '{value}'. Use forms like 30s, 15m, 2h, 7d.")
    amount = int(match.group(1))
    unit = match.group(2)
    if unit == "s":
        return timedelta(seconds=amount)
    if unit == "m":
        return timedelta(minutes=amount)
    if unit == "h":
        return timedelta(hours=amount)
    if unit == "d":
        return timedelta(days=amount)
    return timedelta(weeks=amount)


def _normalize_status(value: Any) -> ApprovalStatus:
    token = str(value or "pending").strip().lower()
    if token not in {"pending", "approved", "denied", "expired"}:
        token = "pending"
    return cast(ApprovalStatus, token)
