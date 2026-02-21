"""HashiCorp Vault KV secret backend."""

from __future__ import annotations

import os
from typing import Any


class VaultSecretBackend:
    """Resolve secrets from HashiCorp Vault KV mounts."""

    def __init__(
        self,
        *,
        client: Any | None = None,
        url: str | None = None,
        token: str | None = None,
        namespace: str | None = None,
        verify: bool | str = True,
        timeout: int = 5,
        mount_point: str = "secret",
        kv_version: int = 2,
    ) -> None:
        if kv_version not in {1, 2}:
            raise ValueError("kv_version must be 1 or 2")
        self.mount_point = str(mount_point).strip() or "secret"
        self.kv_version = kv_version
        self._client = client or self._build_client(
            url=url,
            token=token,
            namespace=namespace,
            verify=verify,
            timeout=timeout,
        )
        self._assert_authenticated()

    def get_secret(self, key: str) -> str:
        path, field = _parse_key(key)
        payload = self._read_payload(path)
        if field not in payload:
            raise KeyError(f"Secret not found: {path}#{field}")
        return str(payload[field])

    def _read_payload(self, path: str) -> dict[str, Any]:
        try:
            if self.kv_version == 2:
                response = self._client.secrets.kv.v2.read_secret_version(
                    path=path,
                    mount_point=self.mount_point,
                )
                data = response.get("data", {})
                payload = data.get("data", {})
            else:
                response = self._client.secrets.kv.v1.read_secret(
                    path=path,
                    mount_point=self.mount_point,
                )
                payload = response.get("data", {})
        except Exception as exc:  # pragma: no cover - exercised through tests with fake clients
            raise KeyError(f"Secret not found: {path}") from exc

        if not isinstance(payload, dict):
            raise KeyError(f"Secret payload is invalid for path '{path}'")
        return payload

    def _assert_authenticated(self) -> None:
        checker = getattr(self._client, "is_authenticated", None)
        if checker is None:
            return
        try:
            authenticated = bool(checker())
        except Exception as exc:  # pragma: no cover - defensive path
            raise RuntimeError("Vault authentication check failed") from exc
        if not authenticated:
            raise RuntimeError("Vault authentication failed")

    @staticmethod
    def _build_client(
        *,
        url: str | None,
        token: str | None,
        namespace: str | None,
        verify: bool | str,
        timeout: int,
    ) -> Any:
        try:
            import hvac  # type: ignore
        except Exception as exc:  # pragma: no cover - depends on environment extras
            raise RuntimeError("Vault backend requires optional dependency 'hvac'") from exc

        resolved_url = url or os.getenv("VAULT_ADDR")
        resolved_token = token or os.getenv("VAULT_TOKEN")
        if not resolved_url:
            raise ValueError("Vault URL is required (pass url=... or set VAULT_ADDR)")
        if not resolved_token:
            raise ValueError("Vault token is required (pass token=... or set VAULT_TOKEN)")
        return hvac.Client(
            url=resolved_url,
            token=resolved_token,
            namespace=namespace,
            verify=verify,
            timeout=timeout,
        )


def _parse_key(raw_key: str) -> tuple[str, str]:
    token = str(raw_key).strip()
    if not token:
        raise ValueError("secret key must not be empty")

    prefix = "vault://"
    if token.lower().startswith(prefix):
        token = token[len(prefix) :]

    path, _, field = token.partition("#")
    normalized_path = path.strip().strip("/")
    if not normalized_path:
        raise ValueError("Vault secret path must not be empty")
    normalized_field = field.strip() or "value"
    return normalized_path, normalized_field
