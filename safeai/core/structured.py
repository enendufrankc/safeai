"""Structured payload scanning helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from safeai.core.audit import AuditEvent, AuditLogger
from safeai.core.classifier import Classifier, Detection
from safeai.core.policy import PolicyContext, PolicyDecision, PolicyEngine


@dataclass(frozen=True)
class StructuredDetection:
    path: str
    detector: str
    tag: str
    start: int
    end: int
    value: str


@dataclass(frozen=True)
class StructuredScanResult:
    original: Any
    filtered: Any
    detections: list[StructuredDetection]
    decision: PolicyDecision


class StructuredScanner:
    """Scan nested structured payloads (dict/list/scalar) at input boundary."""

    def __init__(self, classifier: Classifier, policy_engine: PolicyEngine, audit_logger: AuditLogger) -> None:
        self._classifier = classifier
        self._policy_engine = policy_engine
        self._audit = audit_logger

    def scan(self, payload: Any, *, agent_id: str = "unknown") -> StructuredScanResult:
        detections, path_map, nodes_scanned = _collect_detections(payload, self._classifier)
        tags = sorted({item.tag for item in detections})
        decision = self._policy_engine.evaluate(
            PolicyContext(boundary="input", data_tags=tags, agent_id=agent_id)
        )
        filtered = _apply_payload_action(payload, path_map, decision.action)
        self._audit.emit(
            AuditEvent(
                boundary="input",
                action=decision.action,
                policy_name=decision.policy_name,
                reason=decision.reason,
                data_tags=tags,
                agent_id=agent_id,
                metadata={
                    "phase": "structured_scan",
                    "nodes_scanned": nodes_scanned,
                    "detections": len(detections),
                },
            )
        )
        return StructuredScanResult(
            original=payload,
            filtered=filtered,
            detections=detections,
            decision=decision,
        )


def _collect_detections(
    payload: Any, classifier: Classifier
) -> tuple[list[StructuredDetection], dict[str, list[Detection]], int]:
    rows: list[StructuredDetection] = []
    path_map: dict[str, list[Detection]] = {}
    nodes_scanned = 0
    for path, text in _walk_strings(payload):
        nodes_scanned += 1
        matched = classifier.classify_text(text)
        if not matched:
            continue
        path_map[path] = matched
        for item in matched:
            rows.append(
                StructuredDetection(
                    path=path,
                    detector=item.detector,
                    tag=item.tag,
                    start=item.start,
                    end=item.end,
                    value=item.value,
                )
            )
    rows.sort(key=lambda item: (item.path, item.start, item.end))
    return rows, path_map, nodes_scanned


def _walk_strings(value: Any, *, path: str = "$"):
    if isinstance(value, str):
        yield path, value
        return
    if isinstance(value, dict):
        for key, item in value.items():
            token = str(key)
            child = f"{path}.{token}" if token.isidentifier() else f"{path}[{token!r}]"
            yield from _walk_strings(item, path=child)
        return
    if isinstance(value, (list, tuple)):
        for idx, item in enumerate(value):
            yield from _walk_strings(item, path=f"{path}[{idx}]")
        return
    return


def _apply_payload_action(payload: Any, path_map: dict[str, list[Detection]], action: str) -> Any:
    if action in {"block", "require_approval"}:
        return None
    return _apply_by_path(payload, path_map, action=action)


def _apply_by_path(value: Any, path_map: dict[str, list[Detection]], *, action: str, path: str = "$") -> Any:
    if isinstance(value, str):
        detections = path_map.get(path, [])
        return _apply_text_action(value, detections, action=action)
    if isinstance(value, dict):
        return {
            key: _apply_by_path(item, path_map, action=action, path=_child_path(path, str(key)))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [
            _apply_by_path(item, path_map, action=action, path=f"{path}[{idx}]")
            for idx, item in enumerate(value)
        ]
    if isinstance(value, tuple):
        return tuple(
            _apply_by_path(item, path_map, action=action, path=f"{path}[{idx}]")
            for idx, item in enumerate(value)
        )
    return value


def _child_path(base: str, key: str) -> str:
    return f"{base}.{key}" if key.isidentifier() else f"{base}[{key!r}]"


def _apply_text_action(text: str, detections: list[Detection], *, action: str) -> str:
    if action == "allow":
        return text
    if action in {"block", "require_approval"}:
        return ""
    if action == "redact":
        if not detections:
            return text
        out = text
        for item in sorted(detections, key=lambda row: row.start, reverse=True):
            out = out[: item.start] + "[REDACTED]" + out[item.end :]
        return out
    return text
