"""Tool contract normalization and request validation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from safeai.core.models import ToolContractDocumentModel, ToolContractModel
from safeai.core.policy import expand_tag_hierarchy


@dataclass(frozen=True)
class ToolSideEffects:
    reversible: bool
    requires_approval: bool
    description: str | None = None


@dataclass(frozen=True)
class ToolContract:
    tool_name: str
    description: str | None
    accepts_tags: set[str]
    accepts_fields: set[str]
    emits_tags: set[str]
    emits_fields: set[str]
    stores_fields: set[str]
    stores_retention: str | None
    side_effects: ToolSideEffects


@dataclass(frozen=True)
class ContractValidationResult:
    allowed: bool
    reason: str
    unauthorized_tags: list[str]
    contract: ToolContract | None


class ToolContractRegistry:
    """Runtime registry for declared tool contracts."""

    def __init__(self, contracts: list[ToolContract] | None = None) -> None:
        self._contracts: dict[str, ToolContract] = {}
        self.load(contracts or [])

    def load(self, contracts: list[ToolContract]) -> None:
        self._contracts = {item.tool_name: item for item in contracts}

    def get(self, tool_name: str) -> ToolContract | None:
        return self._contracts.get(str(tool_name).strip())

    def has(self, tool_name: str) -> bool:
        return self.get(tool_name) is not None

    def validate_request(self, tool_name: str, data_tags: list[str]) -> ContractValidationResult:
        contract = self.get(tool_name)
        if contract is None:
            return ContractValidationResult(
                allowed=False,
                reason=f"tool '{tool_name}' has no declared contract",
                unauthorized_tags=sorted(set(data_tags)),
                contract=None,
            )

        if not data_tags:
            return ContractValidationResult(
                allowed=True,
                reason="no classified data tags on request",
                unauthorized_tags=[],
                contract=contract,
            )

        unauthorized: list[str] = []
        accepted = {tag.lower() for tag in contract.accepts_tags}
        for raw_tag in data_tags:
            token = str(raw_tag).strip().lower()
            if not token:
                continue
            expanded = expand_tag_hierarchy([token])
            if accepted.intersection(expanded):
                continue
            unauthorized.append(token)

        if unauthorized:
            return ContractValidationResult(
                allowed=False,
                reason=f"tool '{tool_name}' does not accept data tags: {','.join(sorted(set(unauthorized)))}",
                unauthorized_tags=sorted(set(unauthorized)),
                contract=contract,
            )

        return ContractValidationResult(
            allowed=True,
            reason="tool contract allows request tags",
            unauthorized_tags=[],
            contract=contract,
        )

    def all(self) -> list[ToolContract]:
        return list(self._contracts.values())


def normalize_contracts(raw_items: list[dict[str, Any]]) -> list[ToolContract]:
    """Normalize YAML/JSON contract documents into runtime contract objects."""
    contracts: list[ToolContract] = []
    seen_names: set[str] = set()

    for item in raw_items:
        doc = ToolContractDocumentModel.model_validate(item)
        models: list[ToolContractModel] = []
        if doc.contract is not None:
            models.append(doc.contract)
        if doc.contracts:
            models.extend(doc.contracts)

        for model in models:
            name = model.tool_name.strip()
            if name in seen_names:
                raise ValueError(f"Duplicate tool contract name: {name}")
            seen_names.add(name)
            contracts.append(
                ToolContract(
                    tool_name=name,
                    description=model.description,
                    accepts_tags={tag.lower() for tag in model.accepts.tags},
                    accepts_fields=set(model.accepts.fields),
                    emits_tags={tag.lower() for tag in model.emits.tags},
                    emits_fields=set(model.emits.fields),
                    stores_fields=set(model.stores.fields),
                    stores_retention=model.stores.retention,
                    side_effects=ToolSideEffects(
                        reversible=model.side_effects.reversible,
                        requires_approval=model.side_effects.requires_approval,
                        description=model.side_effects.description,
                    ),
                )
            )
    return contracts
