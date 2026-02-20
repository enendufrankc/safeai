"""Custom detector helpers."""


def normalize_custom_patterns(items: list[dict]) -> list[tuple[str, str, str]]:
    """Normalize custom detector dictionaries into detector tuples."""
    normalized: list[tuple[str, str, str]] = []
    for item in items:
        name = str(item.get("name", "custom"))
        tag = str(item.get("tag", "internal"))
        pattern = str(item.get("pattern", ""))
        if pattern:
            normalized.append((name, tag, pattern))
    return normalized
