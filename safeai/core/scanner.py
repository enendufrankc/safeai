# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 SafeAI Contributors
"""Input boundary scanner."""

from __future__ import annotations

from dataclasses import dataclass

from safeai.core.audit import AuditEvent, AuditLogger
from safeai.core.classifier import Classifier, Detection
from safeai.core.policy import PolicyContext, PolicyDecision, PolicyEngine


@dataclass(frozen=True)
class ScanResult:
    original: str
    filtered: str
    detections: list[Detection]
    decision: PolicyDecision


@dataclass(frozen=True)
class FileScanResult:
    """Result of scanning a file through SafeAI's input boundary."""

    mode: str
    file_path: str
    size_bytes: int
    decision: dict[str, str | None]
    detections: list[dict[str, str | int | None]]
    filtered: str | dict | list | None

    def __getitem__(self, key: str):
        """Allow dict-style access for backward compatibility."""
        return getattr(self, key)

    def get(self, key: str, default=None):
        """Allow dict-style .get() for backward compatibility."""
        return getattr(self, key, default)

    def keys(self):
        """Allow dict-style .keys() for backward compatibility."""
        return self.__dataclass_fields__.keys()


class InputScanner:
    """Classifies and enforces input policy before model access."""

    def __init__(self, classifier: Classifier, policy_engine: PolicyEngine, audit_logger: AuditLogger) -> None:
        self._classifier = classifier
        self._policy_engine = policy_engine
        self._audit = audit_logger

    def scan(self, data: str, agent_id: str = "unknown") -> ScanResult:
        detections = self._classifier.classify_text(data)
        tags = sorted({item.tag for item in detections})
        decision = self._policy_engine.evaluate(
            PolicyContext(boundary="input", data_tags=tags, agent_id=agent_id)
        )
        filtered = _apply_text_action(data, detections, decision.action)

        self._audit.emit(
            AuditEvent(
                boundary="input",
                action=decision.action,
                policy_name=decision.policy_name,
                reason=decision.reason,
                data_tags=tags,
                agent_id=agent_id,
            )
        )
        return ScanResult(original=data, filtered=filtered, detections=detections, decision=decision)


def _apply_text_action(text: str, detections: list[Detection], action: str) -> str:
    if action == "allow":
        return text
    if action == "block":
        return ""
    if not detections:
        return text
    if action == "redact":
        out = text
        for detection in sorted(detections, key=lambda item: item.start, reverse=True):
            out = out[: detection.start] + "[REDACTED]" + out[detection.end :]
        return out
    return text
