"""Environment variable secret backend."""

from __future__ import annotations

import os


class EnvSecretBackend:
    def get_secret(self, key: str) -> str:
        value = os.getenv(key)
        if value is None:
            raise KeyError(f"Secret not found: {key}")
        return value
