"""Action boundary interceptor."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from safeai.core.audit import AuditEvent, AuditLogger
from safeai.core.policy import PolicyContext, PolicyDecision, PolicyEngine


@dataclass(frozen=True)
class ToolCall:
    tool_name: str
    agent_id: str
    parameters: dict[str, Any]
    data_tags: list[str]


@dataclass(frozen=True)
class InterceptResult:
    decision: PolicyDecision
    filtered_params: dict[str, Any]


class ActionInterceptor:
    """Evaluates action-boundary policy on tool calls."""

    def __init__(self, policy_engine: PolicyEngine, audit_logger: AuditLogger) -> None:
        self._policy_engine = policy_engine
        self._audit = audit_logger

    def intercept_request(self, call: ToolCall) -> InterceptResult:
        decision = self._policy_engine.evaluate(
            PolicyContext(
                boundary="action",
                data_tags=call.data_tags,
                agent_id=call.agent_id,
                tool_name=call.tool_name,
            )
        )
        filtered = {} if decision.action == "block" else dict(call.parameters)
        self._audit.emit(
            AuditEvent(
                boundary="action",
                action=decision.action,
                policy_name=decision.policy_name,
                reason=decision.reason,
                data_tags=call.data_tags,
                agent_id=call.agent_id,
                tool_name=call.tool_name,
            )
        )
        return InterceptResult(decision=decision, filtered_params=filtered)
