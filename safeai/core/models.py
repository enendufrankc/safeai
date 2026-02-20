"""Validated core data models used across runtime components."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class DetectionModel(BaseModel):
    detector: str = Field(min_length=1)
    tag: str = Field(min_length=1, pattern=r"^[a-z][a-z0-9_.-]*$")
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    value: str

    @model_validator(mode="after")
    def validate_span(self) -> "DetectionModel":
        if self.end < self.start:
            raise ValueError("end must be >= start")
        return self


class PolicyRuleModel(BaseModel):
    name: str = Field(min_length=1)
    boundary: list[Literal["input", "action", "output"]]
    action: Literal["allow", "redact", "block", "require_approval"]
    reason: str = Field(min_length=1)
    condition: dict[str, Any] = Field(default_factory=dict)
    priority: int = Field(default=100, ge=0)
    fallback_template: str | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize_boundary(cls, value: Any) -> Any:
        if isinstance(value, dict) and isinstance(value.get("boundary"), str):
            updated = dict(value)
            updated["boundary"] = [updated["boundary"]]
            return updated
        return value

    @model_validator(mode="after")
    def validate_condition_shape(self) -> "PolicyRuleModel":
        if not isinstance(self.condition, dict):
            raise ValueError("condition must be an object")
        return self


class PolicyDecisionModel(BaseModel):
    action: Literal["allow", "redact", "block", "require_approval"]
    policy_name: str | None = None
    reason: str = Field(min_length=1)
    fallback_template: str | None = None


class AuditEventModel(BaseModel):
    boundary: Literal["input", "action", "output", "memory"]
    action: Literal["allow", "redact", "block", "require_approval", "approve", "deny"]
    policy_name: str | None = None
    reason: str = Field(min_length=1)
    data_tags: list[str] = Field(default_factory=list)
    agent_id: str = "unknown"
    tool_name: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @model_validator(mode="after")
    def validate_tags(self) -> "AuditEventModel":
        for tag in self.data_tags:
            token = str(tag).strip()
            if token and not _is_tag(token):
                raise ValueError(f"Invalid tag format: {tag}")
        return self


class MemoryFieldModel(BaseModel):
    name: str = Field(min_length=1)
    type: Literal["string", "integer", "number", "boolean", "list", "object"]
    tag: str = Field(min_length=1, pattern=r"^[a-z][a-z0-9_.-]*$")
    retention: str | None = None
    encrypted: bool = False
    required: bool = False


class MemorySchemaModel(BaseModel):
    name: str = Field(min_length=1)
    scope: Literal["session", "user", "global"]
    fields: list[MemoryFieldModel] = Field(min_length=1)
    max_entries: int = Field(default=100, ge=1)
    default_retention: str = Field(default="24h", min_length=1)

    @model_validator(mode="after")
    def validate_unique_fields(self) -> "MemorySchemaModel":
        names = {field.name for field in self.fields}
        if len(names) != len(self.fields):
            raise ValueError("memory field names must be unique")
        return self


class MemorySchemaDocumentModel(BaseModel):
    version: Literal["v1alpha1"] = "v1alpha1"
    memory: MemorySchemaModel | None = None
    memories: list[MemorySchemaModel] | None = None

    @model_validator(mode="after")
    def validate_payload_shape(self) -> "MemorySchemaDocumentModel":
        if self.memory is None and not self.memories:
            raise ValueError("memory or memories is required")
        return self


def _is_tag(value: str) -> bool:
    return bool(value) and value[0].isalpha() and all(ch.isalnum() or ch in "._-" for ch in value)
