"""Audit event primitives and JSON logger."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from safeai.core.models import AuditEventModel


@dataclass
class AuditEvent:
    boundary: str
    action: str
    policy_name: str | None
    reason: str
    data_tags: list[str]
    agent_id: str = "unknown"
    tool_name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AuditLogger:
    """Append-only JSON logger for boundary decisions."""

    def __init__(self, file_path: str | None = None) -> None:
        self.file_path = Path(file_path).expanduser() if file_path else None
        if self.file_path:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, event: AuditEvent) -> None:
        validated = AuditEventModel.model_validate(asdict(event))
        payload = json.dumps(validated.model_dump(mode="json"), separators=(",", ":"), ensure_ascii=True)
        if self.file_path:
            with self.file_path.open("a", encoding="utf-8") as fh:
                fh.write(payload + "\n")
        else:
            print(payload)

    def query(
        self,
        *,
        boundary: str | None = None,
        action: str | None = None,
        policy_name: str | None = None,
        agent_id: str | None = None,
        tool_name: str | None = None,
        since: str | datetime | None = None,
        last: str | None = None,
        limit: int = 100,
        newest_first: bool = True,
    ) -> list[dict[str, Any]]:
        """Query audit events using in-process filters.

        ``last`` accepts compact durations like ``15m``, ``2h``, and ``7d``.
        ``since`` accepts ISO-8601 text or ``datetime``.
        """
        if not self.file_path or not self.file_path.exists():
            return []

        effective_since = _normalize_since(since=since, last=last)
        parsed: list[dict[str, Any]] = []

        for line in self.file_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
                validated = AuditEventModel.model_validate(event).model_dump(mode="json")
            except Exception:
                continue
            if not _matches_event(
                event=validated,
                boundary=boundary,
                action=action,
                policy_name=policy_name,
                agent_id=agent_id,
                tool_name=tool_name,
                since=effective_since,
            ):
                continue
            parsed.append(validated)

        parsed.sort(key=lambda item: item.get("timestamp", ""), reverse=newest_first)
        if limit <= 0:
            return parsed
        return parsed[:limit]


def context_hash(value: Any) -> str:
    """Build a deterministic hash over structured context."""
    normalized = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return "sha256:" + hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _normalize_since(*, since: str | datetime | None, last: str | None) -> datetime | None:
    if last:
        return datetime.now(timezone.utc) - _parse_duration(last)
    if since is None:
        return None
    if isinstance(since, datetime):
        return since if since.tzinfo else since.replace(tzinfo=timezone.utc)
    parsed = datetime.fromisoformat(str(since).replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _matches_event(
    *,
    event: dict[str, Any],
    boundary: str | None,
    action: str | None,
    policy_name: str | None,
    agent_id: str | None,
    tool_name: str | None,
    since: datetime | None,
) -> bool:
    if boundary and event.get("boundary") != boundary:
        return False
    if action and event.get("action") != action:
        return False
    if policy_name and event.get("policy_name") != policy_name:
        return False
    if agent_id and event.get("agent_id") != agent_id:
        return False
    if tool_name and event.get("tool_name") != tool_name:
        return False
    if since:
        timestamp = event.get("timestamp")
        if not timestamp:
            return False
        try:
            when = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
        except ValueError:
            return False
        if not when.tzinfo:
            when = when.replace(tzinfo=timezone.utc)
        if when < since:
            return False
    return True


def _parse_duration(value: str) -> timedelta:
    token = str(value).strip().lower()
    if len(token) < 2 or token[-1] not in {"s", "m", "h", "d"}:
        raise ValueError(f"Invalid duration '{value}'. Use forms like 30s, 15m, 2h, 7d.")

    amount = int(token[:-1])
    unit = token[-1]
    if unit == "s":
        return timedelta(seconds=amount)
    if unit == "m":
        return timedelta(minutes=amount)
    if unit == "h":
        return timedelta(hours=amount)
    return timedelta(days=amount)
