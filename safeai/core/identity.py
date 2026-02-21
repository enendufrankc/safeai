"""Agent identity normalization and enforcement helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from safeai.core.models import AgentIdentityDocumentModel, AgentIdentityModel
from safeai.core.policy import expand_tag_hierarchy


@dataclass(frozen=True)
class AgentIdentity:
    agent_id: str
    description: str | None
    tools: set[str]
    clearance_tags: set[str]


@dataclass(frozen=True)
class AgentIdentityValidationResult:
    allowed: bool
    reason: str
    unauthorized_tags: list[str]
    identity: AgentIdentity | None


class AgentIdentityRegistry:
    """Registry for declared agent identities and permission scopes."""

    def __init__(self, identities: list[AgentIdentity] | None = None) -> None:
        self._identities: dict[str, AgentIdentity] = {}
        self.load(identities or [])

    def load(self, identities: list[AgentIdentity]) -> None:
        self._identities = {item.agent_id: item for item in identities}

    def get(self, agent_id: str) -> AgentIdentity | None:
        return self._identities.get(str(agent_id).strip())

    def has(self, agent_id: str) -> bool:
        return self.get(agent_id) is not None

    def all(self) -> list[AgentIdentity]:
        return list(self._identities.values())

    def validate(
        self,
        *,
        agent_id: str,
        tool_name: str | None = None,
        data_tags: list[str] | None = None,
    ) -> AgentIdentityValidationResult:
        token = str(agent_id).strip()
        tags = list(data_tags or [])
        if not token:
            return AgentIdentityValidationResult(
                allowed=False,
                reason="agent identity is required",
                unauthorized_tags=sorted({str(tag).strip().lower() for tag in tags if str(tag).strip()}),
                identity=None,
            )

        if not self._identities:
            return AgentIdentityValidationResult(
                allowed=True,
                reason="agent identity registry is not configured",
                unauthorized_tags=[],
                identity=None,
            )

        identity = self.get(token)
        if identity is None:
            return AgentIdentityValidationResult(
                allowed=False,
                reason=f"agent '{token}' is not declared",
                unauthorized_tags=sorted({str(tag).strip().lower() for tag in tags if str(tag).strip()}),
                identity=None,
            )

        if tool_name and identity.tools and str(tool_name).strip() not in identity.tools:
            return AgentIdentityValidationResult(
                allowed=False,
                reason=f"agent '{token}' is not bound to tool '{tool_name}'",
                unauthorized_tags=[],
                identity=identity,
            )

        unauthorized = _find_unauthorized_tags(
            tags=tags,
            clearance_tags=identity.clearance_tags,
        )
        if unauthorized:
            return AgentIdentityValidationResult(
                allowed=False,
                reason=f"agent '{token}' exceeds tag clearance: {','.join(unauthorized)}",
                unauthorized_tags=unauthorized,
                identity=identity,
            )

        return AgentIdentityValidationResult(
            allowed=True,
            reason="agent identity allows tool and data scope",
            unauthorized_tags=[],
            identity=identity,
        )


def normalize_agent_identities(raw_items: list[dict[str, Any]]) -> list[AgentIdentity]:
    """Normalize YAML/JSON identity documents into runtime objects."""
    identities: list[AgentIdentity] = []
    seen_ids: set[str] = set()

    for item in raw_items:
        doc = AgentIdentityDocumentModel.model_validate(item)
        models: list[AgentIdentityModel] = []
        if doc.agent is not None:
            models.append(doc.agent)
        if doc.agents:
            models.extend(doc.agents)

        for model in models:
            name = model.agent_id.strip()
            if name in seen_ids:
                raise ValueError(f"Duplicate agent identity: {name}")
            seen_ids.add(name)
            identities.append(
                AgentIdentity(
                    agent_id=name,
                    description=model.description,
                    tools=set(model.tools),
                    clearance_tags={tag.lower() for tag in model.clearance_tags},
                )
            )
    return identities


def _find_unauthorized_tags(*, tags: list[str], clearance_tags: set[str]) -> list[str]:
    if not tags:
        return []
    if not clearance_tags:
        return []

    accepted = {tag.lower() for tag in clearance_tags}
    unauthorized: set[str] = set()
    for raw_tag in tags:
        token = str(raw_tag).strip().lower()
        if not token:
            continue
        expanded = expand_tag_hierarchy([token])
        if accepted.intersection(expanded):
            continue
        unauthorized.add(token)
    return sorted(unauthorized)
