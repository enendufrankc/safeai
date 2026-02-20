"""Pydantic config models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PathsConfig(BaseModel):
    policy_files: list[str] = Field(default_factory=lambda: ["policies/default.yaml"])
    contract_files: list[str] = Field(default_factory=lambda: ["contracts/*.yaml"])
    memory_schema_files: list[str] = Field(default_factory=lambda: ["schemas/*.yaml"])


class AuditConfig(BaseModel):
    file_path: str | None = "logs/audit.log"


class SafeAIConfig(BaseModel):
    version: str = "v1alpha1"
    paths: PathsConfig = Field(default_factory=PathsConfig)
    audit: AuditConfig = Field(default_factory=AuditConfig)
