"""Phone detector patterns."""

PHONE_PATTERNS: list[tuple[str, str, str]] = [
    ("phone", "personal.pii", r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
]
