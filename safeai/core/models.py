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


class ToolIOContractModel(BaseModel):
    tags: list[str] = Field(default_factory=list)
    fields: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def normalize_values(self) -> "ToolIOContractModel":
        self.tags = sorted({str(tag).strip() for tag in self.tags if str(tag).strip()})
        self.fields = sorted({str(field).strip() for field in self.fields if str(field).strip()})
        return self


class ToolStoresModel(BaseModel):
    fields: list[str] = Field(default_factory=list)
    retention: str | None = None

    @model_validator(mode="after")
    def normalize_values(self) -> "ToolStoresModel":
        self.fields = sorted({str(field).strip() for field in self.fields if str(field).strip()})
        self.retention = str(self.retention).strip() if self.retention else None
        return self


class ToolSideEffectsModel(BaseModel):
    reversible: bool
    requires_approval: bool
    description: str | None = None


class ToolContractModel(BaseModel):
    tool_name: str = Field(min_length=1)
    description: str | None = None
    accepts: ToolIOContractModel = Field(default_factory=ToolIOContractModel)
    emits: ToolIOContractModel = Field(default_factory=ToolIOContractModel)
    stores: ToolStoresModel = Field(default_factory=ToolStoresModel)
    side_effects: ToolSideEffectsModel

    @model_validator(mode="after")
    def normalize_tool_name(self) -> "ToolContractModel":
        self.tool_name = self.tool_name.strip()
        if self.description is not None:
            self.description = self.description.strip() or None
        return self


class ToolContractDocumentModel(BaseModel):
    version: Literal["v1alpha1"] = "v1alpha1"
    contract: ToolContractModel | None = None
    contracts: list[ToolContractModel] | None = None

    @model_validator(mode="after")
    def validate_payload_shape(self) -> "ToolContractDocumentModel":
        if self.contract is None and not self.contracts:
            raise ValueError("contract or contracts is required")
        return self


class AgentIdentityModel(BaseModel):
    agent_id: str = Field(min_length=1)
    description: str | None = None
    tools: list[str] = Field(default_factory=list)
    clearance_tags: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def normalize_values(self) -> "AgentIdentityModel":
        self.agent_id = self.agent_id.strip()
        self.description = str(self.description).strip() if self.description else None
        self.tools = sorted({str(tool).strip() for tool in self.tools if str(tool).strip()})
        self.clearance_tags = sorted(
            {str(tag).strip().lower() for tag in self.clearance_tags if str(tag).strip()}
        )
        return self


class AgentIdentityDocumentModel(BaseModel):
    version: Literal["v1alpha1"] = "v1alpha1"
    agent: AgentIdentityModel | None = None
    agents: list[AgentIdentityModel] | None = None

    @model_validator(mode="after")
    def validate_payload_shape(self) -> "AgentIdentityDocumentModel":
        if self.agent is None and not self.agents:
            raise ValueError("agent or agents is required")
        return self


class CapabilityScopeModel(BaseModel):
    tool_name: str = Field(min_length=1)
    actions: list[str] = Field(min_length=1)
    secret_keys: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def normalize_values(self) -> "CapabilityScopeModel":
        self.tool_name = self.tool_name.strip()
        self.actions = sorted(
            {str(action).strip().lower() for action in self.actions if str(action).strip()}
        )
        self.secret_keys = sorted(
            {str(secret).strip() for secret in self.secret_keys if str(secret).strip()}
        )
        if not self.actions:
            raise ValueError("actions must contain at least one value")
        return self


class CapabilityTokenModel(BaseModel):
    token_id: str = Field(min_length=1, pattern=r"^cap_[a-z0-9]{12,}$")
    agent_id: str = Field(min_length=1)
    issued_at: datetime
    expires_at: datetime
    scope: CapabilityScopeModel
    session_id: str | None = None
    revoked_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_temporal_order(self) -> "CapabilityTokenModel":
        if self.expires_at <= self.issued_at:
            raise ValueError("expires_at must be after issued_at")
        if self.revoked_at is not None and self.revoked_at < self.issued_at:
            raise ValueError("revoked_at must be >= issued_at")
        self.agent_id = self.agent_id.strip()
        if self.session_id is not None:
            self.session_id = self.session_id.strip() or None
        return self


class AuditEventModel(BaseModel):
    event_id: str = Field(min_length=1)
    boundary: Literal["input", "action", "output", "memory"]
    action: Literal["allow", "redact", "block", "require_approval", "approve", "deny"]
    policy_name: str | None = None
    reason: str = Field(min_length=1)
    data_tags: list[str] = Field(default_factory=list)
    agent_id: str = "unknown"
    tool_name: str | None = None
    session_id: str | None = None
    source_agent_id: str | None = None
    destination_agent_id: str | None = None
    context_hash: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @model_validator(mode="after")
    def validate_tags(self) -> "AuditEventModel":
        for tag in self.data_tags:
            token = str(tag).strip()
            if token and not _is_tag(token):
                raise ValueError(f"Invalid tag format: {tag}")
        if not self.event_id.startswith("evt_"):
            raise ValueError("event_id must start with 'evt_'")
        if not self.context_hash.startswith("sha256:"):
            raise ValueError("context_hash must start with 'sha256:'")
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
