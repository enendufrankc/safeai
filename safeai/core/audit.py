"""Audit event primitives and JSON logger."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from safeai.core.models import AuditEventModel
from safeai.core.policy import expand_tag_hierarchy


@dataclass
class AuditEvent:
    boundary: str
    action: str
    policy_name: str | None
    reason: str
    data_tags: list[str]
    event_id: str = field(default_factory=lambda: f"evt_{uuid4().hex[:12]}")
    agent_id: str = "unknown"
    tool_name: str | None = None
    session_id: str | None = None
    source_agent_id: str | None = None
    destination_agent_id: str | None = None
    context_hash: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AuditLogger:
    """Append-only JSON logger for boundary decisions."""

    def __init__(self, file_path: str | None = None) -> None:
        self.file_path = Path(file_path).expanduser() if file_path else None
        if self.file_path:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, event: AuditEvent) -> None:
        event_payload = asdict(event)
        if not event_payload.get("context_hash"):
            event_payload["context_hash"] = context_hash(
                {
                    "event_id": event_payload.get("event_id"),
                    "boundary": event_payload.get("boundary"),
                    "action": event_payload.get("action"),
                    "policy_name": event_payload.get("policy_name"),
                    "reason": event_payload.get("reason"),
                    "data_tags": event_payload.get("data_tags", []),
                    "agent_id": event_payload.get("agent_id"),
                    "tool_name": event_payload.get("tool_name"),
                    "session_id": event_payload.get("session_id"),
                    "source_agent_id": event_payload.get("source_agent_id"),
                    "destination_agent_id": event_payload.get("destination_agent_id"),
                    "metadata": event_payload.get("metadata", {}),
                }
            )
        validated = AuditEventModel.model_validate(event_payload)
        encoded = json.dumps(validated.model_dump(mode="json"), separators=(",", ":"), ensure_ascii=True)
        if self.file_path:
            with self.file_path.open("a", encoding="utf-8") as fh:
                fh.write(encoded + "\n")
        else:
            print(encoded)

    def query(
        self,
        *,
        boundary: str | None = None,
        action: str | None = None,
        policy_name: str | None = None,
        agent_id: str | None = None,
        tool_name: str | None = None,
        data_tag: str | None = None,
        phase: str | None = None,
        session_id: str | None = None,
        event_id: str | None = None,
        source_agent_id: str | None = None,
        destination_agent_id: str | None = None,
        metadata_key: str | None = None,
        metadata_value: str | None = None,
        since: str | datetime | None = None,
        until: str | datetime | None = None,
        last: str | None = None,
        limit: int = 100,
        newest_first: bool = True,
    ) -> list[dict[str, Any]]:
        """Query audit events using in-process filters.

        ``last`` accepts compact durations like ``15m``, ``2h``, and ``7d``.
        ``since`` and ``until`` accept ISO-8601 text or ``datetime``.
        """
        if not self.file_path or not self.file_path.exists():
            return []

        effective_since, effective_until = _normalize_range(since=since, until=until, last=last)
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
                data_tag=data_tag,
                phase=phase,
                session_id=session_id,
                event_id=event_id,
                source_agent_id=source_agent_id,
                destination_agent_id=destination_agent_id,
                metadata_key=metadata_key,
                metadata_value=metadata_value,
                since=effective_since,
                until=effective_until,
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


def _normalize_range(
    *,
    since: str | datetime | None,
    until: str | datetime | None,
    last: str | None,
) -> tuple[datetime | None, datetime | None]:
    if last:
        now = datetime.now(timezone.utc)
        return now - _parse_duration(last), now
    return _normalize_when(since), _normalize_when(until)


def _normalize_when(value: str | datetime | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _matches_event(
    *,
    event: dict[str, Any],
    boundary: str | None,
    action: str | None,
    policy_name: str | None,
    agent_id: str | None,
    tool_name: str | None,
    data_tag: str | None,
    phase: str | None,
    session_id: str | None,
    event_id: str | None,
    source_agent_id: str | None,
    destination_agent_id: str | None,
    metadata_key: str | None,
    metadata_value: str | None,
    since: datetime | None,
    until: datetime | None,
) -> bool:
    metadata = event.get("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}

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
    if event_id and event.get("event_id") != event_id:
        return False
    if session_id and event.get("session_id") != session_id:
        return False
    if source_agent_id and event.get("source_agent_id") != source_agent_id:
        return False
    if destination_agent_id and event.get("destination_agent_id") != destination_agent_id:
        return False
    if phase and str(metadata.get("phase")) != phase:
        return False
    if metadata_key:
        if metadata_key not in metadata:
            return False
        if metadata_value is not None and str(metadata.get(metadata_key)) != metadata_value:
            return False
    if data_tag:
        event_tags = [str(tag) for tag in event.get("data_tags", [])]
        expanded = expand_tag_hierarchy(event_tags)
        token = str(data_tag).strip().lower()
        if token:
            if token not in expanded:
                return False

    if since or until:
        timestamp = event.get("timestamp")
        if not timestamp:
            return False
        try:
            when = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
        except ValueError:
            return False
        if not when.tzinfo:
            when = when.replace(tzinfo=timezone.utc)
        if since and when < since:
            return False
        if until and when > until:
            return False
    return True


def _parse_duration(value: str) -> timedelta:
    import re

    match = re.match(r"^\s*(\d+)\s*([smhdw])\s*$", str(value).lower())
    if not match:
        raise ValueError(f"Invalid duration '{value}'. Use forms like 30s, 15m, 2h, 7d, 2w.")

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
