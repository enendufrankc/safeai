"""Secret backend protocol."""

from __future__ import annotations

from typing import Protocol


class SecretBackend(Protocol):
    def get_secret(self, key: str) -> str:
        """Return a secret value for the key or raise KeyError."""
