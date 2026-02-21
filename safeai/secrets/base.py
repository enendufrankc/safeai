"""Secret backend protocol and typed errors."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


class SecretError(RuntimeError):
    """Base class for all secret-resolution errors."""


class SecretBackendNotFoundError(SecretError):
    """Raised when a configured secret backend is not registered."""


class SecretNotFoundError(SecretError):
    """Raised when a backend cannot find a requested secret key."""


class SecretAccessDeniedError(SecretError):
    """Raised when capability scope does not allow secret resolution."""


@runtime_checkable
class SecretBackend(Protocol):
    def get_secret(self, key: str) -> str:
        """Return a secret value for the key or raise KeyError."""
