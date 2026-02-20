"""Built-in detector registry."""

from safeai.detectors.api_key import API_KEY_PATTERNS
from safeai.detectors.credit_card import CREDIT_CARD_PATTERNS
from safeai.detectors.email import EMAIL_PATTERNS
from safeai.detectors.phone import PHONE_PATTERNS
from safeai.detectors.ssn import SSN_PATTERNS


def all_detectors() -> list[tuple[str, str, str]]:
    """Return (name, tag, pattern) detector tuples."""
    return [
        *EMAIL_PATTERNS,
        *PHONE_PATTERNS,
        *SSN_PATTERNS,
        *CREDIT_CARD_PATTERNS,
        *API_KEY_PATTERNS,
    ]
