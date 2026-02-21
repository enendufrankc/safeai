"""Schema-bound in-memory store with retention enforcement."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from cryptography.fernet import Fernet

from safeai.config.loader import load_memory_documents
from safeai.core.models import MemoryFieldModel, MemorySchemaDocumentModel, MemorySchemaModel


@dataclass(frozen=True)
class MemoryEntry:
    value: Any
    expires_at: datetime
    tag: str
    encrypted: bool


@dataclass(frozen=True)
class HandleEntry:
    ciphertext: bytes
    expires_at: datetime
    tag: str
    agent_id: str


@dataclass
class MemoryController:
    """Schema-enforced memory controller with field-level retention."""

    schema: MemorySchemaModel
    _data: dict[str, dict[str, MemoryEntry]] = field(default_factory=dict)
    _handles: dict[str, HandleEntry] = field(default_factory=dict)
    _fernet_key: bytes | None = None
    _fernet: Fernet = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._fernet = Fernet(self._fernet_key or Fernet.generate_key())

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
        existing = bucket.get(key)
        if existing and existing.encrypted:
            self._handles.pop(str(existing.value), None)

        stored_value: Any
        if field_spec.encrypted:
            stored_value = self._store_handle(
                value=value,
                expires_at=expiry,
                tag=field_spec.tag,
                agent_id=agent_id,
            )
        else:
            stored_value = value
        bucket[key] = MemoryEntry(
            value=stored_value,
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
            self._drop_entry(bucket=bucket, key=key, entry=entry)
            return None
        return entry.value

    def purge(self, agent_id: str | None = None) -> int:
        if agent_id is None:
            count = 0
            for bucket in self._data.values():
                for key, entry in list(bucket.items()):
                    self._drop_entry(bucket=bucket, key=key, entry=entry)
                    count += 1
            self._data.clear()
            self._handles.clear()
            return count
        removed = 0
        bucket = self._data.get(agent_id, {})
        for key, entry in list(bucket.items()):
            self._drop_entry(bucket=bucket, key=key, entry=entry)
            removed += 1
        self._data.pop(agent_id, None)
        return removed

    def purge_expired(self) -> int:
        now = datetime.now(timezone.utc)
        purged = 0
        for agent_id in list(self._data.keys()):
            bucket = self._data.get(agent_id, {})
            for key in list(bucket.keys()):
                entry = bucket[key]
                if entry.expires_at <= now:
                    self._drop_entry(bucket=bucket, key=key, entry=entry)
                    purged += 1
            if not bucket:
                self._data.pop(agent_id, None)
        for handle_id in list(self._handles.keys()):
            if self._handles[handle_id].expires_at <= now:
                self._handles.pop(handle_id, None)
        return purged

    def handle_metadata(self, handle_id: str) -> dict[str, Any] | None:
        token = _normalize_handle_id(handle_id)
        if not token:
            return None
        entry = self._handles.get(token)
        if entry is None:
            return None
        if entry.expires_at <= datetime.now(timezone.utc):
            self._handles.pop(token, None)
            return None
        return {
            "tag": entry.tag,
            "agent_id": entry.agent_id,
            "expires_at": entry.expires_at,
        }

    def resolve_handle(self, handle_id: str, *, agent_id: str) -> Any:
        token = _normalize_handle_id(handle_id)
        if not token:
            raise KeyError(f"Invalid memory handle '{handle_id}'")
        entry = self._handles.get(token)
        if entry is None:
            raise KeyError(f"Memory handle '{token}' not found")
        if entry.expires_at <= datetime.now(timezone.utc):
            self._handles.pop(token, None)
            raise KeyError(f"Memory handle '{token}' expired")
        if entry.agent_id != str(agent_id).strip():
            raise PermissionError("memory handle agent binding mismatch")

        decrypted = self._fernet.decrypt(entry.ciphertext)
        payload = json.loads(decrypted.decode("utf-8"))
        if not isinstance(payload, dict) or "value" not in payload:
            raise ValueError("memory handle payload is invalid")
        return payload["value"]

    def _field(self, key: str) -> MemoryFieldModel | None:
        for field_spec in self.schema.fields:
            if field_spec.name == key:
                return field_spec
        return None

    def _drop_entry(self, *, bucket: dict[str, MemoryEntry], key: str, entry: MemoryEntry) -> None:
        bucket.pop(key, None)
        if entry.encrypted:
            self._handles.pop(str(entry.value), None)

    def _store_handle(self, *, value: Any, expires_at: datetime, tag: str, agent_id: str) -> str:
        handle_id = f"hdl_{uuid4().hex[:24]}"
        payload = json.dumps({"value": value}, sort_keys=True, default=str, ensure_ascii=True).encode("utf-8")
        ciphertext = self._fernet.encrypt(payload)
        self._handles[handle_id] = HandleEntry(
            ciphertext=ciphertext,
            expires_at=expires_at,
            tag=str(tag).strip().lower(),
            agent_id=str(agent_id).strip(),
        )
        return handle_id


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


def _normalize_handle_id(value: str) -> str | None:
    token = str(value).strip()
    if not token:
        return None
    return token
