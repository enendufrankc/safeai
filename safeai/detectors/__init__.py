# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 SafeAI Contributors
"""Built-in detector registry."""

from safeai.detectors.api_key import API_KEY_PATTERNS
from safeai.detectors.credit_card import CREDIT_CARD_PATTERNS
from safeai.detectors.dangerous_commands import DANGEROUS_COMMAND_PATTERNS
from safeai.detectors.email import EMAIL_PATTERNS
from safeai.detectors.phone import PHONE_PATTERNS
from safeai.detectors.prompt_injection import PROMPT_INJECTION_PATTERNS
from safeai.detectors.ssn import SSN_PATTERNS
from safeai.detectors.topic_restriction import TOPIC_RESTRICTION_PATTERNS
from safeai.detectors.toxicity import TOXICITY_PATTERNS


def all_detectors() -> list[tuple[str, str, str]]:
    """Return (name, tag, pattern) detector tuples."""
    return [
        *EMAIL_PATTERNS,
        *PHONE_PATTERNS,
        *SSN_PATTERNS,
        *CREDIT_CARD_PATTERNS,
        *API_KEY_PATTERNS,
        *PROMPT_INJECTION_PATTERNS,
        *TOXICITY_PATTERNS,
        *DANGEROUS_COMMAND_PATTERNS,
        *TOPIC_RESTRICTION_PATTERNS,
    ]
