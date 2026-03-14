# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 SafeAI Contributors
"""Topic restriction detector.

Configurable blocked-topic patterns. Ships with common enterprise defaults
(competitor discussion, legal advice, medical advice, financial advice).
Users extend via YAML config or plugins.

Tags follow the convention: restricted.<topic_name>
"""

from __future__ import annotations

# Built-in topic restriction patterns.
# Users add custom topics via policy YAML config.
TOPIC_RESTRICTION_PATTERNS: list[tuple[str, str, str]] = [
    # Competitor discussion
    (
        "competitor_discussion",
        "restricted.competitor",
        r"\b(?:switch(?:ing)?\s+to|migrate\s+to|better\s+than|compared?\s+(?:to|with)|vs\.?)\s+(?:competitor|rival|alternative)\b",
    ),
    # Legal advice
    (
        "legal_advice_request",
        "restricted.legal",
        r"\b(?:legal\s+advice|(?:should\s+i|can\s+i)\s+sue|file\s+a?\s*lawsuit|legal\s+liability|attorney|lawyer\s+recommend)\b",
    ),
    # Medical advice
    (
        "medical_advice_request",
        "restricted.medical",
        r"\b(?:(?:what|which)\s+(?:medication|drug|treatment)\s+should|diagnos(?:e|is)\s+(?:me|my)|medical\s+advice|prescri(?:be|ption)\s+(?:for|me))\b",
    ),
    # Financial advice
    (
        "financial_advice_request",
        "restricted.financial",
        r"\b(?:(?:should\s+i|can\s+i)\s+(?:invest|buy|sell)\s+(?:in\s+)?(?:stock|crypto|bitcoin)|financial\s+advice|guaranteed\s+(?:returns?|profit))\b",
    ),
    # Internal/confidential
    (
        "internal_info_request",
        "restricted.internal",
        r"\b(?:internal\s+(?:document|memo|policy|salary|compensation)|confidential\s+(?:data|info|document)|trade\s+secret)\b",
    ),
    # Weapons/explosives
    (
        "weapons_info",
        "restricted.weapons",
        r"\b(?:how\s+to\s+(?:make|build|create)\s+(?:a\s+)?(?:bomb|explosive|weapon|gun)|(?:build|assemble)\s+(?:a\s+)?(?:firearm|explosive\s+device))\b",
    ),
    # Illegal activities
    (
        "illegal_activity",
        "restricted.illegal",
        r"\b(?:how\s+to\s+(?:hack|break\s+into|steal|forge|counterfeit|launder)|(?:bypass|circumvent)\s+(?:security|authentication|encryption))\b",
    ),
]
