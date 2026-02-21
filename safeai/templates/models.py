"""Pydantic models for the community template marketplace."""

from __future__ import annotations

from pydantic import BaseModel, Field


class TemplateMetadata(BaseModel):
    name: str
    description: str = ""
    author: str = "community"
    category: str = "general"
    tags: list[str] = Field(default_factory=list)
    compliance_standards: list[str] = Field(default_factory=list)
    framework_compat: list[str] = Field(default_factory=list)
    download_url: str = ""
    sha256: str = ""
    version: str = "1.0.0"


class CommunityIndex(BaseModel):
    version: str = "v1"
    templates: list[TemplateMetadata] = Field(default_factory=list)
