# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 SafeAI Contributors
"""Detector typing primitives."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DetectorPattern:
    name: str
    tag: str
    pattern: str
