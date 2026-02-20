"""API key and token detector patterns."""

API_KEY_PATTERNS: list[tuple[str, str, str]] = [
    ("openai_key", "secret.credential", r"\bsk-[A-Za-z0-9]{20,}\b"),
    ("aws_access_key", "secret.credential", r"\bAKIA[0-9A-Z]{16}\b"),
    ("generic_token", "secret.token", r"\b(?:token|api[_-]?key|secret)\s*[:=]\s*[A-Za-z0-9_\-]{12,}\b"),
]
