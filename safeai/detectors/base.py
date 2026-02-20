"""Detector typing primitives."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DetectorPattern:
    name: str
    tag: str
    pattern: str
