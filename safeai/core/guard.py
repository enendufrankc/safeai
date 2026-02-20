"""Output boundary guard."""

from __future__ import annotations

from dataclasses import dataclass
from string import Formatter

from safeai.core.audit import AuditEvent, AuditLogger
from safeai.core.classifier import Classifier, Detection
from safeai.core.policy import PolicyContext, PolicyDecision, PolicyEngine
from safeai.core.scanner import _apply_text_action


@dataclass(frozen=True)
class GuardResult:
    original: str
    safe_output: str
    detections: list[Detection]
    decision: PolicyDecision
    fallback_used: bool = False


class OutputGuard:
    """Applies output policy before content leaves the system."""

    def __init__(self, classifier: Classifier, policy_engine: PolicyEngine, audit_logger: AuditLogger) -> None:
        self._classifier = classifier
        self._policy_engine = policy_engine
        self._audit = audit_logger

    def guard(self, data: str, agent_id: str = "unknown") -> GuardResult:
        detections = self._classifier.classify_text(data)
        tags = sorted({item.tag for item in detections})
        decision = self._policy_engine.evaluate(
            PolicyContext(boundary="output", data_tags=tags, agent_id=agent_id)
        )
        redacted = _apply_text_action(data, detections, decision.action)
        safe_output, fallback_used = _apply_output_fallback(
            original=data,
            redacted=redacted,
            detections=detections,
            tags=tags,
            agent_id=agent_id,
            decision=decision,
        )

        self._audit.emit(
            AuditEvent(
                boundary="output",
                action=decision.action,
                policy_name=decision.policy_name,
                reason=decision.reason,
                data_tags=tags,
                agent_id=agent_id,
                metadata={"fallback_used": fallback_used},
            )
        )
        return GuardResult(
            original=data,
            safe_output=safe_output,
            detections=detections,
            decision=decision,
            fallback_used=fallback_used,
        )


def _apply_output_fallback(
    *,
    original: str,
    redacted: str,
    detections: list[Detection],
    tags: list[str],
    agent_id: str,
    decision: PolicyDecision,
) -> tuple[str, bool]:
    if decision.action not in {"block", "redact"}:
        return redacted, False

    template = (decision.fallback_template or "").strip()
    if not template:
        return redacted, False

    rendered = _render_fallback_template(
        template=template,
        original=original,
        redacted=redacted,
        detections=detections,
        tags=tags,
        agent_id=agent_id,
        decision=decision,
    )
    return rendered, True


def _render_fallback_template(
    *,
    template: str,
    original: str,
    redacted: str,
    detections: list[Detection],
    tags: list[str],
    agent_id: str,
    decision: PolicyDecision,
) -> str:
    fields: dict[str, str] = {
        "original": original,
        "redacted": redacted,
        "reason": decision.reason,
        "policy_name": decision.policy_name or "default-deny",
        "action": decision.action,
        "agent_id": agent_id,
        "data_tags": ",".join(tags),
        "detections": str(len(detections)),
    }
    try:
        return Formatter().vformat(template, (), _SafeTemplateDict(fields))
    except Exception:
        return template


class _SafeTemplateDict(dict[str, str]):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"
