"""AWS Secrets Manager backend."""

from __future__ import annotations

import base64
import json
import os
from typing import Any


class AWSSecretBackend:
    """Resolve secrets from AWS Secrets Manager."""

    def __init__(
        self,
        *,
        client: Any | None = None,
        region_name: str | None = None,
    ) -> None:
        self._client = client or self._build_client(region_name=region_name)

    def get_secret(self, key: str) -> str:
        secret_id, field = _parse_key(key)
        try:
            response = self._client.get_secret_value(SecretId=secret_id)
        except Exception as exc:  # pragma: no cover - exercised through tests with fake clients
            raise KeyError(f"Secret not found: {secret_id}") from exc

        if response.get("SecretString") is not None:
            value = str(response["SecretString"])
            if not field:
                return value
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError as exc:
                raise KeyError(
                    f"Secret '{secret_id}' is not JSON and cannot resolve field '{field}'"
                ) from exc
            if not isinstance(parsed, dict) or field not in parsed:
                raise KeyError(f"Secret '{secret_id}' has no field '{field}'")
            return str(parsed[field])

        if response.get("SecretBinary") is not None:
            raw = response["SecretBinary"]
            if field:
                raise KeyError(f"Binary secret '{secret_id}' cannot resolve field '{field}'")
            decoded = raw if isinstance(raw, (bytes, bytearray)) else base64.b64decode(raw)
            return decoded.decode("utf-8")

        raise KeyError(f"Secret '{secret_id}' returned no data")

    @staticmethod
    def _build_client(*, region_name: str | None) -> Any:
        try:
            import boto3  # type: ignore
        except Exception as exc:  # pragma: no cover - depends on environment extras
            raise RuntimeError("AWS backend requires optional dependency 'boto3'") from exc

        resolved_region = region_name or os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION")
        if not resolved_region:
            raise ValueError(
                "AWS region is required (pass region_name=... or set AWS_REGION/AWS_DEFAULT_REGION)"
            )
        return boto3.client("secretsmanager", region_name=resolved_region)


def _parse_key(raw_key: str) -> tuple[str, str | None]:
    token = str(raw_key).strip()
    if not token:
        raise ValueError("secret key must not be empty")

    prefix = "aws://"
    if token.lower().startswith(prefix):
        token = token[len(prefix) :]

    secret_id, has_delim, field = token.partition("#")
    normalized_id = secret_id.strip()
    if not normalized_id:
        raise ValueError("AWS secret id must not be empty")
    normalized_field = field.strip() if has_delim and field.strip() else None
    return normalized_id, normalized_field
