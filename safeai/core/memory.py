"""Schema-bound in-memory store with retention enforcement."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from safeai.config.loader import load_memory_documents
from safeai.core.models import MemoryFieldModel, MemorySchemaDocumentModel, MemorySchemaModel


@dataclass(frozen=True)
class MemoryEntry:
    value: Any
    expires_at: datetime
    tag: str
    encrypted: bool


@dataclass
class MemoryController:
    """Schema-enforced memory controller with field-level retention."""

    schema: MemorySchemaModel
    _data: dict[str, dict[str, MemoryEntry]] = field(default_factory=dict)

    @classmethod
    def from_schema_file(
        cls,
        path: str | Path,
        *,
        version: str = "v1alpha1",
    ) -> "MemoryController":
        loaded = load_memory_documents(path, [Path(path).name], version=version)
        if not loaded:
            raise ValueError(f"No memory definitions found in {path}")
        return cls.from_documents(loaded)

    @classmethod
    def from_documents(cls, documents: list[dict[str, Any]]) -> "MemoryController":
        if not documents:
            raise ValueError("No memory schema documents provided")

        parsed_definitions: list[MemorySchemaModel] = []
        for doc in documents:
            parsed = MemorySchemaDocumentModel.model_validate(doc)
            if parsed.memory:
                parsed_definitions.append(parsed.memory)
            if parsed.memories:
                parsed_definitions.extend(parsed.memories)

        if not parsed_definitions:
            raise ValueError("No memory definitions present after validation")

        # MVP uses first memory definition; multi-profile routing is post-MVP.
        return cls(schema=parsed_definitions[0])

    @property
    def allowed_fields(self) -> set[str]:
        return {field.name for field in self.schema.fields}

    def write(self, key: str, value: Any, agent_id: str) -> bool:
        field_spec = self._field(key)
        if field_spec is None:
            return False
        if not _matches_declared_type(value, field_spec.type):
            return False

        bucket = self._data.setdefault(agent_id, {})
        if key not in bucket and len(bucket) >= self.schema.max_entries:
            return False

        expiry = _compute_expiry(field_spec.retention or self.schema.default_retention)
        bucket[key] = MemoryEntry(
            value=value,
            expires_at=expiry,
            tag=field_spec.tag,
            encrypted=field_spec.encrypted,
        )
        return True

    def read(self, key: str, agent_id: str) -> Any:
        bucket = self._data.get(agent_id)
        if not bucket:
            return None
        entry = bucket.get(key)
        if not entry:
            return None
        if entry.expires_at <= datetime.now(timezone.utc):
            bucket.pop(key, None)
            return None
        return entry.value

    def purge(self, agent_id: str | None = None) -> int:
        if agent_id is None:
            count = sum(len(values) for values in self._data.values())
            self._data.clear()
            return count
        removed = len(self._data.get(agent_id, {}))
        self._data.pop(agent_id, None)
        return removed

    def purge_expired(self) -> int:
        now = datetime.now(timezone.utc)
        purged = 0
        for agent_id in list(self._data.keys()):
            bucket = self._data.get(agent_id, {})
            for key in list(bucket.keys()):
                if bucket[key].expires_at <= now:
                    bucket.pop(key, None)
                    purged += 1
            if not bucket:
                self._data.pop(agent_id, None)
        return purged

    def _field(self, key: str) -> MemoryFieldModel | None:
        for field_spec in self.schema.fields:
            if field_spec.name == key:
                return field_spec
        return None


def _compute_expiry(retention: str) -> datetime:
    return datetime.now(timezone.utc) + _parse_duration(retention)


def _parse_duration(value: str) -> timedelta:
    match = re.match(r"^\s*(\d+)\s*([smhdw])\s*$", str(value).lower())
    if not match:
        raise ValueError(f"Invalid retention duration '{value}'. Use forms like 30m, 24h, 7d.")

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


def _matches_declared_type(value: Any, declared: str) -> bool:
    if declared == "string":
        return isinstance(value, str)
    if declared == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if declared == "number":
        return (isinstance(value, int) and not isinstance(value, bool)) or isinstance(value, float)
    if declared == "boolean":
        return isinstance(value, bool)
    if declared == "list":
        return isinstance(value, list)
    if declared == "object":
        return isinstance(value, dict)
    return False
