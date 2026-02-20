"""Email detector patterns."""

EMAIL_PATTERNS: list[tuple[str, str, str]] = [
    ("email", "personal.pii", r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
]
