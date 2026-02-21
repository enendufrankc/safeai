"""Secret backend integrations."""

from safeai.secrets.aws import AWSSecretBackend
from safeai.secrets.base import (
    SecretAccessDeniedError,
    SecretBackend,
    SecretBackendNotFoundError,
    SecretError,
    SecretNotFoundError,
)
from safeai.secrets.capability import CapabilityTokenManager, CapabilityValidationResult
from safeai.secrets.env import EnvSecretBackend
from safeai.secrets.manager import ResolvedSecret, SecretManager
from safeai.secrets.vault import VaultSecretBackend

__all__ = [
    "SecretBackend",
    "SecretError",
    "SecretBackendNotFoundError",
    "SecretNotFoundError",
    "SecretAccessDeniedError",
    "CapabilityTokenManager",
    "CapabilityValidationResult",
    "AWSSecretBackend",
    "EnvSecretBackend",
    "VaultSecretBackend",
    "ResolvedSecret",
    "SecretManager",
]
