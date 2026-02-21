"""Secret manager interface with capability-gated resolution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from safeai.secrets.base import (
    SecretAccessDeniedError,
    SecretBackend,
    SecretBackendNotFoundError,
    SecretNotFoundError,
)
from safeai.secrets.capability import CapabilityTokenManager
from safeai.secrets.env import EnvSecretBackend


@dataclass(frozen=True, repr=False)
class ResolvedSecret:
    """Secret payload and metadata for controlled tool injection."""

    key: str
    value: str
    backend: str
    token_id: str
    agent_id: str
    tool_name: str
    action: str
    session_id: str | None

    def __repr__(self) -> str:
        return (
            "ResolvedSecret("
            f"key={self.key!r}, "
            f"backend={self.backend!r}, "
            f"token_id={self.token_id!r}, "
            f"agent_id={self.agent_id!r}, "
            f"tool_name={self.tool_name!r}, "
            f"action={self.action!r}, "
            f"session_id={self.session_id!r}, "
            "value='***'"
            ")"
        )


class SecretManager:
    """Resolves scoped secrets from registered backends."""

    def __init__(
        self,
        *,
        capability_manager: CapabilityTokenManager | None = None,
        backends: Mapping[str, SecretBackend] | None = None,
    ) -> None:
        self._capabilities = capability_manager or CapabilityTokenManager()
        self._backends: dict[str, SecretBackend] = {"env": EnvSecretBackend()}
        if backends:
            for name, backend in backends.items():
                self.register_backend(name, backend, replace=True)

    def register_backend(self, name: str, backend: SecretBackend, *, replace: bool = False) -> None:
        normalized = _normalize_backend_name(name)
        if normalized in self._backends and not replace:
            raise ValueError(f"secret backend '{normalized}' is already registered")
        self._backends[normalized] = backend

    def list_backends(self) -> list[str]:
        return sorted(self._backends.keys())

    def has_backend(self, name: str) -> bool:
        return _normalize_backend_name(name) in self._backends

    def resolve_secret(
        self,
        *,
        token_id: str,
        secret_key: str,
        agent_id: str,
        tool_name: str,
        action: str = "invoke",
        session_id: str | None = None,
        backend: str = "env",
    ) -> ResolvedSecret:
        normalized_key = _normalize_secret_key(secret_key)
        resolved_backend = self._get_backend(backend)
        validated = self._capabilities.validate(
            token_id,
            agent_id=agent_id,
            tool_name=tool_name,
            action=action,
            session_id=session_id,
        )
        if not validated.allowed:
            raise SecretAccessDeniedError(validated.reason)
        token = validated.token
        if token is None:
            raise SecretAccessDeniedError("capability token is unavailable for secret resolution")

        allowed_keys = set(token.scope.secret_keys)
        if not allowed_keys:
            raise SecretAccessDeniedError("capability token does not grant secret-key access")
        if normalized_key not in allowed_keys:
            raise SecretAccessDeniedError(
                f"capability token does not allow secret key '{normalized_key}'"
            )

        try:
            value = resolved_backend.get_secret(normalized_key)
        except KeyError as exc:
            raise SecretNotFoundError(f"secret '{normalized_key}' not found in backend '{backend}'") from exc

        return ResolvedSecret(
            key=normalized_key,
            value=str(value),
            backend=_normalize_backend_name(backend),
            token_id=token.token_id,
            agent_id=token.agent_id,
            tool_name=token.scope.tool_name,
            action=str(action).strip().lower(),
            session_id=token.session_id,
        )

    def resolve_secrets(
        self,
        *,
        token_id: str,
        secret_keys: list[str],
        agent_id: str,
        tool_name: str,
        action: str = "invoke",
        session_id: str | None = None,
        backend: str = "env",
    ) -> dict[str, ResolvedSecret]:
        rows: dict[str, ResolvedSecret] = {}
        for key in secret_keys:
            resolved = self.resolve_secret(
                token_id=token_id,
                secret_key=key,
                agent_id=agent_id,
                tool_name=tool_name,
                action=action,
                session_id=session_id,
                backend=backend,
            )
            rows[resolved.key] = resolved
        return rows

    def _get_backend(self, name: str) -> SecretBackend:
        normalized = _normalize_backend_name(name)
        backend = self._backends.get(normalized)
        if backend is None:
            raise SecretBackendNotFoundError(f"secret backend '{normalized}' is not registered")
        return backend


def _normalize_backend_name(value: str) -> str:
    token = str(value).strip().lower()
    if not token:
        raise ValueError("backend name must not be empty")
    return token


def _normalize_secret_key(value: str) -> str:
    token = str(value).strip()
    if not token:
        raise ValueError("secret key must not be empty")
    return token
