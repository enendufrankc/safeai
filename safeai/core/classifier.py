"""Regex-based detector execution."""

from __future__ import annotations

import re
from dataclasses import dataclass

from safeai.core.models import DetectionModel
from safeai.detectors import all_detectors


@dataclass(frozen=True)
class Detection:
    detector: str
    tag: str
    start: int
    end: int
    value: str


class Classifier:
    """Runs built-in and custom regex detectors against text."""

    def __init__(self, patterns: list[tuple[str, str, str]] | None = None) -> None:
        pattern_defs = patterns or all_detectors()
        self._compiled: list[tuple[str, str, re.Pattern[str]]] = [
            (name, tag, re.compile(pattern, flags=re.IGNORECASE)) for name, tag, pattern in pattern_defs
        ]

    def classify_text(self, text: str) -> list[Detection]:
        detections: list[Detection] = []
        for name, tag, pattern in self._compiled:
            for match in pattern.finditer(text):
                validated = DetectionModel(
                    detector=name,
                    tag=tag,
                    start=match.start(),
                    end=match.end(),
                    value=match.group(0),
                )
                detections.append(Detection(**validated.model_dump()))
        return sorted(detections, key=lambda item: (item.start, item.end))
