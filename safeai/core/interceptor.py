"""Action boundary interceptor."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from safeai.core.approval import ApprovalManager
from safeai.core.audit import AuditEvent, AuditLogger
from safeai.core.classifier import Classifier
from safeai.core.contracts import ToolContract, ToolContractRegistry
from safeai.core.identity import AgentIdentityRegistry
from safeai.core.policy import PolicyContext, PolicyDecision, PolicyEngine, expand_tag_hierarchy
from safeai.secrets.capability import CapabilityTokenManager


@dataclass(frozen=True)
class ToolCall:
    tool_name: str
    agent_id: str
    parameters: dict[str, Any]
    data_tags: list[str]
    session_id: str | None = None
    source_agent_id: str | None = None
    destination_agent_id: str | None = None
    action_type: str | None = None
    capability_token_id: str | None = None
    capability_action: str = "invoke"
    approval_request_id: str | None = None


@dataclass(frozen=True)
class InterceptResult:
    decision: PolicyDecision
    filtered_params: dict[str, Any]
    unauthorized_tags: list[str]
    stripped_fields: list[str]


@dataclass(frozen=True)
class ResponseInterceptResult:
    decision: PolicyDecision
    filtered_response: dict[str, Any]
    stripped_fields: list[str]
    stripped_tags: list[str]


class ActionInterceptor:
    """Evaluates action-boundary policy on tool calls."""

    def __init__(
        self,
        policy_engine: PolicyEngine,
        audit_logger: AuditLogger,
        contract_registry: ToolContractRegistry | None = None,
        identity_registry: AgentIdentityRegistry | None = None,
        capability_manager: CapabilityTokenManager | None = None,
        approval_manager: ApprovalManager | None = None,
        classifier: Classifier | None = None,
    ) -> None:
        self._policy_engine = policy_engine
        self._audit = audit_logger
        self._contracts = contract_registry or ToolContractRegistry()
        self._identities = identity_registry or AgentIdentityRegistry()
        self._capabilities = capability_manager or CapabilityTokenManager()
        self._approvals = approval_manager or ApprovalManager()
        self._classifier = classifier or Classifier()

    def intercept_request(self, call: ToolCall) -> InterceptResult:
        if call.capability_token_id:
            capability_validation = self._capabilities.validate(
                call.capability_token_id,
                agent_id=call.agent_id,
                tool_name=call.tool_name,
                action=call.capability_action,
                session_id=call.session_id,
            )
            if not capability_validation.allowed:
                decision = _capability_block_decision(capability_validation.reason)
                self._audit.emit(
                    AuditEvent(
                        boundary="action",
                        action=decision.action,
                        policy_name=decision.policy_name,
                        reason=decision.reason,
                        data_tags=call.data_tags,
                        agent_id=call.agent_id,
                        tool_name=call.tool_name,
                        session_id=call.session_id,
                        source_agent_id=call.source_agent_id or call.agent_id,
                        destination_agent_id=call.destination_agent_id,
                        metadata={
                            "phase": "request",
                            "decision_source": "capability-token",
                            "action_type": call.action_type or "tool_call",
                            "capability_token_id": call.capability_token_id,
                            "capability_action": call.capability_action,
                            "parameter_keys": sorted(call.parameters.keys()),
                            "filtered_parameter_keys": [],
                            "unauthorized_tags": [],
                            "stripped_fields": sorted(call.parameters.keys()),
                        },
                    )
                )
                return InterceptResult(
                    decision=decision,
                    filtered_params={},
                    unauthorized_tags=[],
                    stripped_fields=sorted(call.parameters.keys()),
                )

        contract_validation = self._contracts.validate_request(call.tool_name, call.data_tags)
        if not contract_validation.allowed:
            decision = _contract_block_decision(contract_validation.reason)
            self._audit.emit(
                AuditEvent(
                    boundary="action",
                    action=decision.action,
                    policy_name=decision.policy_name,
                    reason=decision.reason,
                    data_tags=call.data_tags,
                    agent_id=call.agent_id,
                    tool_name=call.tool_name,
                    session_id=call.session_id,
                    source_agent_id=call.source_agent_id or call.agent_id,
                    destination_agent_id=call.destination_agent_id,
                    metadata={
                        "phase": "request",
                        "decision_source": "tool-contract",
                    "action_type": call.action_type or "tool_call",
                    "capability_token_id": call.capability_token_id,
                    "capability_action": call.capability_action,
                    "parameter_keys": sorted(call.parameters.keys()),
                    "filtered_parameter_keys": [],
                    "unauthorized_tags": contract_validation.unauthorized_tags,
                        "stripped_fields": sorted(call.parameters.keys()),
                    },
                )
            )
            return InterceptResult(
                decision=decision,
                filtered_params={},
                unauthorized_tags=contract_validation.unauthorized_tags,
                stripped_fields=sorted(call.parameters.keys()),
            )

        identity_validation = self._identities.validate(
            agent_id=call.agent_id,
            tool_name=call.tool_name,
            data_tags=call.data_tags,
        )
        if not identity_validation.allowed:
            decision = _identity_block_decision(identity_validation.reason)
            self._audit.emit(
                AuditEvent(
                    boundary="action",
                    action=decision.action,
                    policy_name=decision.policy_name,
                    reason=decision.reason,
                    data_tags=call.data_tags,
                    agent_id=call.agent_id,
                    tool_name=call.tool_name,
                    session_id=call.session_id,
                    source_agent_id=call.source_agent_id or call.agent_id,
                    destination_agent_id=call.destination_agent_id,
                    metadata={
                        "phase": "request",
                        "decision_source": "agent-identity",
                    "action_type": call.action_type or "tool_call",
                    "capability_token_id": call.capability_token_id,
                    "capability_action": call.capability_action,
                    "parameter_keys": sorted(call.parameters.keys()),
                    "filtered_parameter_keys": [],
                    "unauthorized_tags": identity_validation.unauthorized_tags,
                        "stripped_fields": sorted(call.parameters.keys()),
                    },
                )
            )
            return InterceptResult(
                decision=decision,
                filtered_params={},
                unauthorized_tags=identity_validation.unauthorized_tags,
                stripped_fields=sorted(call.parameters.keys()),
            )

        filtered_params, stripped_fields = _filter_allowed_fields(
            call.parameters,
            contract_validation.contract,
            io_direction="accepts",
        )
        decision = self._policy_engine.evaluate(
            PolicyContext(
                boundary="action",
                data_tags=call.data_tags,
                agent_id=call.agent_id,
                tool_name=call.tool_name,
            )
        )
        approval_required = False
        approval_request_id = call.approval_request_id
        approval_status = "not_required"
        approval_source: str | None = None

        if decision.action not in {"block", "redact"}:
            policy_requires_approval = decision.action == "require_approval"
            approval_required = policy_requires_approval
            if approval_required:
                approval_source = "policy"

                if call.approval_request_id:
                    validation = self._approvals.validate(
                        call.approval_request_id,
                        agent_id=call.agent_id,
                        tool_name=call.tool_name,
                        session_id=call.session_id,
                    )
                    approval_request_id = call.approval_request_id
                    approval_status = validation.reason
                    if validation.allowed:
                        decision = PolicyDecision(
                            action="allow",
                            policy_name=decision.policy_name or "approval-gate",
                            reason=f"approval request '{call.approval_request_id}' approved",
                        )
                    elif validation.request and validation.request.status == "pending":
                        decision = PolicyDecision(
                            action="require_approval",
                            policy_name=decision.policy_name or "approval-gate",
                            reason=validation.reason,
                        )
                    elif validation.request and validation.request.status == "denied":
                        decision = PolicyDecision(
                            action="block",
                            policy_name="approval-gate",
                            reason=validation.reason,
                        )
                    else:
                        created = self._approvals.create_request(
                            reason=decision.reason,
                            policy_name=decision.policy_name or "approval-gate",
                            agent_id=call.agent_id,
                            tool_name=call.tool_name,
                            session_id=call.session_id,
                            action_type=call.action_type or "tool_call",
                            data_tags=call.data_tags,
                            metadata={
                                "parameter_keys": sorted(call.parameters.keys()),
                                "source_agent_id": call.source_agent_id or call.agent_id,
                                "destination_agent_id": call.destination_agent_id,
                                "approval_source": approval_source,
                            },
                            dedupe_key=_approval_dedupe_key(call=call, source=approval_source or "unknown"),
                        )
                        approval_request_id = created.request_id
                        approval_status = "pending"
                        decision = PolicyDecision(
                            action="require_approval",
                            policy_name=created.policy_name or "approval-gate",
                            reason=f"approval required ({created.request_id})",
                        )
                else:
                    created = self._approvals.create_request(
                        reason=decision.reason,
                        policy_name=decision.policy_name or "approval-gate",
                        agent_id=call.agent_id,
                        tool_name=call.tool_name,
                        session_id=call.session_id,
                        action_type=call.action_type or "tool_call",
                        data_tags=call.data_tags,
                        metadata={
                            "parameter_keys": sorted(call.parameters.keys()),
                            "source_agent_id": call.source_agent_id or call.agent_id,
                            "destination_agent_id": call.destination_agent_id,
                            "approval_source": approval_source,
                        },
                        dedupe_key=_approval_dedupe_key(call=call, source=approval_source or "unknown"),
                    )
                    approval_request_id = created.request_id
                    approval_status = "pending"
                    decision = PolicyDecision(
                        action="require_approval",
                        policy_name=created.policy_name or "approval-gate",
                        reason=f"approval required ({created.request_id})",
                    )

        if decision.action in {"block", "redact", "require_approval"}:
            filtered_params = {}
            stripped_fields = sorted(set(stripped_fields).union(call.parameters.keys()))

        self._audit.emit(
            AuditEvent(
                boundary="action",
                action=decision.action,
                policy_name=decision.policy_name,
                reason=decision.reason,
                data_tags=call.data_tags,
                agent_id=call.agent_id,
                tool_name=call.tool_name,
                session_id=call.session_id,
                source_agent_id=call.source_agent_id or call.agent_id,
                destination_agent_id=call.destination_agent_id,
                metadata={
                    "phase": "request",
                    "decision_source": "policy",
                    "action_type": call.action_type or "tool_call",
                    "capability_token_id": call.capability_token_id,
                    "capability_action": call.capability_action,
                    "parameter_keys": sorted(call.parameters.keys()),
                    "filtered_parameter_keys": sorted(filtered_params.keys()),
                    "unauthorized_tags": [],
                    "stripped_fields": stripped_fields,
                    "approval_required": approval_required,
                    "approval_source": approval_source,
                    "approval_request_id": approval_request_id,
                    "approval_status": approval_status,
                    "contract_declared": contract_validation.contract is not None,
                    "contract_side_effects": _contract_side_effects_metadata(contract_validation.contract),
                },
            )
        )
        return InterceptResult(
            decision=decision,
            filtered_params=filtered_params,
            unauthorized_tags=[],
            stripped_fields=stripped_fields,
        )

    def intercept_response(self, call: ToolCall, response: dict[str, Any]) -> ResponseInterceptResult:
        contract = self._contracts.get(call.tool_name)
        if contract is None:
            decision = _contract_block_decision(f"tool '{call.tool_name}' has no declared contract")
            blocked_fields = sorted(response.keys())
            self._audit.emit(
                AuditEvent(
                    boundary="action",
                    action=decision.action,
                    policy_name=decision.policy_name,
                    reason=decision.reason,
                    data_tags=call.data_tags,
                    agent_id=call.agent_id,
                    tool_name=call.tool_name,
                    session_id=call.session_id,
                    source_agent_id=call.source_agent_id or call.agent_id,
                    destination_agent_id=call.destination_agent_id,
                    metadata={
                        "phase": "response",
                        "decision_source": "tool-contract",
                        "action_type": call.action_type or "tool_call",
                        "response_field_count": len(response),
                        "filtered_field_count": 0,
                        "stripped_fields": blocked_fields,
                        "stripped_tags": [],
                    },
                )
            )
            return ResponseInterceptResult(
                decision=decision,
                filtered_response={},
                stripped_fields=blocked_fields,
                stripped_tags=[],
            )

        identity_validation = self._identities.validate(
            agent_id=call.agent_id,
            tool_name=call.tool_name,
            data_tags=call.data_tags,
        )
        if not identity_validation.allowed:
            decision = _identity_block_decision(identity_validation.reason)
            blocked_fields = sorted(response.keys())
            self._audit.emit(
                AuditEvent(
                    boundary="action",
                    action=decision.action,
                    policy_name=decision.policy_name,
                    reason=decision.reason,
                    data_tags=call.data_tags,
                    agent_id=call.agent_id,
                    tool_name=call.tool_name,
                    session_id=call.session_id,
                    source_agent_id=call.source_agent_id or call.agent_id,
                    destination_agent_id=call.destination_agent_id,
                    metadata={
                        "phase": "response",
                        "decision_source": "agent-identity",
                        "action_type": call.action_type or "tool_call",
                        "response_field_count": len(response),
                        "filtered_field_count": 0,
                        "stripped_fields": blocked_fields,
                        "stripped_tags": identity_validation.unauthorized_tags,
                    },
                )
            )
            return ResponseInterceptResult(
                decision=decision,
                filtered_response={},
                stripped_fields=blocked_fields,
                stripped_tags=identity_validation.unauthorized_tags,
            )

        filtered_response: dict[str, Any] = {}
        kept_tags: set[str] = set()
        stripped_field_names: set[str] = set()
        stripped_tag_names: set[str] = set()

        for field_name, value in response.items():
            field_tags = _classify_value_tags(self._classifier, value)
            field_identity_validation = self._identities.validate(
                agent_id=call.agent_id,
                tool_name=call.tool_name,
                data_tags=sorted(field_tags),
            )
            if not field_identity_validation.allowed:
                stripped_field_names.add(field_name)
                stripped_tag_names.update(field_identity_validation.unauthorized_tags)
                continue

            if _field_blocked_by_contract(contract, field_name, field_tags):
                stripped_field_names.add(field_name)
                stripped_tag_names.update(field_tags)
                continue

            field_decision = self._policy_engine.evaluate(
                PolicyContext(
                    boundary="action",
                    data_tags=sorted(field_tags),
                    agent_id=call.agent_id,
                    tool_name=call.tool_name,
                )
            )
            if field_decision.action in {"block", "redact", "require_approval"}:
                stripped_field_names.add(field_name)
                stripped_tag_names.update(field_tags)
                continue

            filtered_response[field_name] = value
            kept_tags.update(field_tags)

        decision = self._policy_engine.evaluate(
            PolicyContext(
                boundary="action",
                data_tags=sorted(kept_tags),
                agent_id=call.agent_id,
                tool_name=call.tool_name,
            )
        )
        if decision.action in {"block", "redact", "require_approval"}:
            stripped_field_names.update(filtered_response.keys())
            stripped_tag_names.update(kept_tags)
            filtered_response = {}

        if decision.action == "allow" and stripped_field_names:
            decision = PolicyDecision(
                action="redact",
                policy_name="tool-contract",
                reason="tool response fields filtered by contract/policy",
            )

        stripped_fields_list = sorted(stripped_field_names)
        stripped_tags_list = sorted(stripped_tag_names)
        self._audit.emit(
            AuditEvent(
                boundary="action",
                action=decision.action,
                policy_name=decision.policy_name,
                reason=decision.reason,
                data_tags=sorted(kept_tags),
                agent_id=call.agent_id,
                tool_name=call.tool_name,
                session_id=call.session_id,
                source_agent_id=call.source_agent_id or call.agent_id,
                destination_agent_id=call.destination_agent_id,
                metadata={
                    "phase": "response",
                    "decision_source": decision.policy_name or "policy",
                    "action_type": call.action_type or "tool_call",
                    "response_field_count": len(response),
                    "filtered_field_count": len(filtered_response),
                    "response_keys": sorted(response.keys()),
                    "filtered_response_keys": sorted(filtered_response.keys()),
                    "stripped_fields": stripped_fields_list,
                    "stripped_tags": stripped_tags_list,
                    "contract_declared": True,
                    "contract_side_effects": _contract_side_effects_metadata(contract),
                },
            )
        )
        return ResponseInterceptResult(
            decision=decision,
            filtered_response=filtered_response,
            stripped_fields=stripped_fields_list,
            stripped_tags=stripped_tags_list,
        )


def _contract_block_decision(reason: str) -> PolicyDecision:
    return PolicyDecision(
        action="block",
        policy_name="tool-contract",
        reason=reason,
    )


def _identity_block_decision(reason: str) -> PolicyDecision:
    return PolicyDecision(
        action="block",
        policy_name="agent-identity",
        reason=reason,
    )


def _capability_block_decision(reason: str) -> PolicyDecision:
    return PolicyDecision(
        action="block",
        policy_name="capability-token",
        reason=reason,
    )


def _filter_allowed_fields(
    params: dict[str, Any],
    contract: ToolContract | None,
    *,
    io_direction: str,
) -> tuple[dict[str, Any], list[str]]:
    if contract is None:
        return {}, sorted(params.keys())

    allowed: set[str]
    if io_direction == "accepts":
        allowed = set(contract.accepts_fields)
    else:
        allowed = set(contract.emits_fields)

    if not allowed:
        return dict(params), []

    filtered: dict[str, Any] = {}
    stripped: list[str] = []
    for key, value in params.items():
        if key in allowed:
            filtered[key] = value
        else:
            stripped.append(key)
    return filtered, sorted(stripped)


def _field_blocked_by_contract(contract: ToolContract, field_name: str, field_tags: set[str]) -> bool:
    if contract.emits_fields and field_name not in contract.emits_fields:
        return True

    if not field_tags:
        return False

    accepted = {tag.lower() for tag in contract.emits_tags}
    if not accepted:
        return False

    for tag in field_tags:
        if accepted.intersection(expand_tag_hierarchy([tag])):
            continue
        return True
    return False


def _classify_value_tags(classifier: Classifier, value: Any) -> set[str]:
    if value is None:
        return set()

    if isinstance(value, str):
        text = value
    else:
        try:
            text = json.dumps(value, sort_keys=True, default=str)
        except TypeError:
            text = str(value)

    return {detection.tag for detection in classifier.classify_text(text)}


def _contract_side_effects_metadata(contract: ToolContract | None) -> dict[str, Any]:
    if contract is None:
        return {}
    return {
        "reversible": contract.side_effects.reversible,
        "requires_approval": contract.side_effects.requires_approval,
        "description": contract.side_effects.description,
    }


def _approval_dedupe_key(*, call: ToolCall, source: str) -> str:
    keys = ",".join(sorted(call.parameters.keys()))
    tags = ",".join(sorted(call.data_tags))
    return "|".join(
        [
            call.agent_id,
            call.tool_name,
            call.session_id or "-",
            source,
            tags,
            keys,
        ]
    )
