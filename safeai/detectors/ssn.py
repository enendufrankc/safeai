"""SSN detector patterns."""

SSN_PATTERNS: list[tuple[str, str, str]] = [
    ("ssn", "personal.pii", r"\b\d{3}-\d{2}-\d{4}\b"),
]
