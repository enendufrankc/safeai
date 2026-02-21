"""Pydantic config models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DashboardUserConfig(BaseModel):
    user_id: str
    role: str = "viewer"
    tenants: list[str] = Field(default_factory=lambda: ["default"])


class PluginConfig(BaseModel):
    enabled: bool = True
    plugin_files: list[str] = Field(default_factory=lambda: ["plugins/*.py"])


class DashboardConfig(BaseModel):
    enabled: bool = True
    rbac_enabled: bool = True
    user_header: str = "x-safeai-user"
    tenant_header: str = "x-safeai-tenant"
    tenant_policy_file: str | None = "tenants/policy-sets.yaml"
    alert_rules_file: str | None = "alerts/default.yaml"
    alert_log_file: str | None = "logs/alerts.log"
    users: list[DashboardUserConfig] = Field(
        default_factory=lambda: [
            DashboardUserConfig(user_id="security-admin", role="admin", tenants=["*"]),
            DashboardUserConfig(user_id="security-approver", role="approver", tenants=["default"]),
            DashboardUserConfig(user_id="security-auditor", role="auditor", tenants=["default"]),
            DashboardUserConfig(user_id="security-viewer", role="viewer", tenants=["default"]),
        ]
    )


class PathsConfig(BaseModel):
    policy_files: list[str] = Field(default_factory=lambda: ["policies/default.yaml"])
    contract_files: list[str] = Field(default_factory=lambda: ["contracts/*.yaml"])
    memory_schema_files: list[str] = Field(default_factory=lambda: ["schemas/*.yaml"])
    identity_files: list[str] = Field(default_factory=list)


class AuditConfig(BaseModel):
    file_path: str | None = "logs/audit.log"


class ApprovalConfig(BaseModel):
    file_path: str | None = "logs/approvals.log"
    default_ttl: str = "30m"


class MemoryRuntimeConfig(BaseModel):
    auto_purge_expired: bool = True


class SafeAIConfig(BaseModel):
    version: str = "v1alpha1"
    paths: PathsConfig = Field(default_factory=PathsConfig)
    audit: AuditConfig = Field(default_factory=AuditConfig)
    approvals: ApprovalConfig = Field(default_factory=ApprovalConfig)
    memory_runtime: MemoryRuntimeConfig = Field(default_factory=MemoryRuntimeConfig)
    plugins: PluginConfig = Field(default_factory=PluginConfig)
    dashboard: DashboardConfig = Field(default_factory=DashboardConfig)
