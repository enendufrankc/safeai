"""Vault and AWS secret backend tests."""

from __future__ import annotations

import unittest
from types import SimpleNamespace

from safeai.secrets.aws import AWSSecretBackend
from safeai.secrets.vault import VaultSecretBackend


class _FakeVaultKVV2:
    def __init__(self, values: dict[str, dict[str, str]]) -> None:
        self._values = values

    def read_secret_version(self, *, path: str, mount_point: str) -> dict[str, dict[str, dict[str, str]]]:
        _ = mount_point
        if path not in self._values:
            raise KeyError(path)
        return {"data": {"data": self._values[path]}}


class _FakeVaultKVV1:
    def __init__(self, values: dict[str, dict[str, str]]) -> None:
        self._values = values

    def read_secret(self, *, path: str, mount_point: str) -> dict[str, dict[str, str]]:
        _ = mount_point
        if path not in self._values:
            raise KeyError(path)
        return {"data": self._values[path]}


class _FakeVaultClient:
    def __init__(self, values: dict[str, dict[str, str]], *, authenticated: bool = True) -> None:
        self.secrets = SimpleNamespace(
            kv=SimpleNamespace(
                v1=_FakeVaultKVV1(values),
                v2=_FakeVaultKVV2(values),
            )
        )
        self._authenticated = authenticated

    def is_authenticated(self) -> bool:
        return self._authenticated


class _FakeAWSClient:
    def __init__(self, values: dict[str, dict[str, object]]) -> None:
        self._values = values

    def get_secret_value(self, *, SecretId: str) -> dict[str, object]:
        if SecretId not in self._values:
            raise KeyError(SecretId)
        return self._values[SecretId]


class SecretBackendsTests(unittest.TestCase):
    def test_vault_backend_reads_kv_v2_and_supports_field_selection(self) -> None:
        backend = VaultSecretBackend(
            client=_FakeVaultClient({"apps/email": {"value": "fallback", "token": "abc123"}}),
            mount_point="secret",
            kv_version=2,
        )
        self.assertEqual(backend.get_secret("apps/email"), "fallback")
        self.assertEqual(backend.get_secret("vault://apps/email#token"), "abc123")

    def test_vault_backend_reads_kv_v1(self) -> None:
        backend = VaultSecretBackend(
            client=_FakeVaultClient({"apps/email": {"value": "v1token"}}),
            mount_point="secret",
            kv_version=1,
        )
        self.assertEqual(backend.get_secret("apps/email"), "v1token")

    def test_vault_backend_rejects_unauthenticated_client(self) -> None:
        with self.assertRaises(RuntimeError):
            VaultSecretBackend(
                client=_FakeVaultClient({"apps/email": {"value": "x"}}, authenticated=False),
                mount_point="secret",
            )

    def test_vault_backend_reports_missing_secret_or_field(self) -> None:
        backend = VaultSecretBackend(client=_FakeVaultClient({"apps/email": {"value": "x"}}))
        with self.assertRaises(KeyError):
            backend.get_secret("missing/path")
        with self.assertRaises(KeyError):
            backend.get_secret("apps/email#token")

    def test_aws_backend_reads_plain_json_and_binary_secrets(self) -> None:
        backend = AWSSecretBackend(
            client=_FakeAWSClient(
                {
                    "plain/secret": {"SecretString": "value-1"},
                    "json/secret": {"SecretString": '{"token":"abc","user":"ops"}'},
                    "binary/secret": {"SecretBinary": b"raw-bytes"},
                }
            )
        )
        self.assertEqual(backend.get_secret("plain/secret"), "value-1")
        self.assertEqual(backend.get_secret("aws://json/secret#token"), "abc")
        self.assertEqual(backend.get_secret("binary/secret"), "raw-bytes")

    def test_aws_backend_reports_missing_secret_or_field(self) -> None:
        backend = AWSSecretBackend(
            client=_FakeAWSClient(
                {
                    "json/secret": {"SecretString": '{"token":"abc"}'},
                    "plain/secret": {"SecretString": "plain-value"},
                }
            )
        )
        with self.assertRaises(KeyError):
            backend.get_secret("missing/secret")
        with self.assertRaises(KeyError):
            backend.get_secret("json/secret#missing")
        with self.assertRaises(KeyError):
            backend.get_secret("plain/secret#token")


if __name__ == "__main__":
    unittest.main()
