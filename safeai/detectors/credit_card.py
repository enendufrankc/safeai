# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 SafeAI Contributors
"""Credit card detector patterns."""

CREDIT_CARD_PATTERNS: list[tuple[str, str, str]] = [
    ("credit_card", "personal.financial", r"\b(?:\d[ -]*?){13,19}\b"),
]
