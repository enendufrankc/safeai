"""Secret manager interface tests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from safeai import SafeAI
from safeai.core.audit import AuditLogger
from safeai.core.classifier import Classifier
from safeai.core.policy import PolicyEngine, normalize_rules
from safeai.secrets import (
    SecretAccessDeniedError,
    SecretBackendNotFoundError,
    SecretManager,
    SecretNotFoundError,
)
from safeai.secrets.capability import CapabilityTokenManager


class _DictSecretBackend:
    def __init__(self, values: dict[str, str]) -> None:
        self._values = dict(values)

    def get_secret(self, key: str) -> str:
        if key not in self._values:
            raise KeyError(key)
        return self._values[key]


def _policy_engine() -> PolicyEngine:
    return PolicyEngine(
        normalize_rules(
            [
                {
                    "name": "allow-default",
                    "boundary": ["action", "input", "output"],
                    "action": "allow",
                    "reason": "allow",
                    "priority": 1000,
                }
            ]
        )
    )


class SecretManagerTests(unittest.TestCase):
    def test_register_list_and_replace_backend(self) -> None:
        manager = SecretManager(capability_manager=CapabilityTokenManager())
        manager.register_backend("dict", _DictSecretBackend({"A": "1"}))
        self.assertIn("dict", manager.list_backends())
        self.assertIn("env", manager.list_backends())

        with self.assertRaises(ValueError):
            manager.register_backend("dict", _DictSecretBackend({"A": "2"}))

        manager.register_backend("dict", _DictSecretBackend({"A": "2"}), replace=True)
        self.assertTrue(manager.has_backend("dict"))

    def test_resolve_secret_with_capability_scope(self) -> None:
        capabilities = CapabilityTokenManager()
        manager = SecretManager(
            capability_manager=capabilities,
            backends={"dict": _DictSecretBackend({"SMTP_TOKEN": "super-secret-token"})},
        )
        token = capabilities.issue(
            agent_id="ops-bot",
            tool_name="send_email",
            actions=["invoke"],
            secret_keys=["SMTP_TOKEN"],
            ttl="10m",
            session_id="sess-1",
        )

        resolved = manager.resolve_secret(
            token_id=token.token_id,
            secret_key="SMTP_TOKEN",
            agent_id="ops-bot",
            tool_name="send_email",
            action="invoke",
            session_id="sess-1",
            backend="dict",
        )
        self.assertEqual(resolved.value, "super-secret-token")
        self.assertEqual(resolved.backend, "dict")
        self.assertEqual(resolved.key, "SMTP_TOKEN")
        self.assertNotIn("super-secret-token", repr(resolved))
        self.assertIn("value='***'", repr(resolved))

    def test_resolve_secret_denies_missing_or_unauthorized_scope(self) -> None:
        capabilities = CapabilityTokenManager()
        manager = SecretManager(
            capability_manager=capabilities,
            backends={"dict": _DictSecretBackend({"SMTP_TOKEN": "secret"})},
        )
        empty_scope = capabilities.issue(
            agent_id="ops-bot",
            tool_name="send_email",
            actions=["invoke"],
            ttl="10m",
        )
        with self.assertRaises(SecretAccessDeniedError):
            manager.resolve_secret(
                token_id=empty_scope.token_id,
                secret_key="SMTP_TOKEN",
                agent_id="ops-bot",
                tool_name="send_email",
                backend="dict",
            )

        scoped = capabilities.issue(
            agent_id="ops-bot",
            tool_name="send_email",
            actions=["invoke"],
            secret_keys=["PAYMENT_TOKEN"],
            ttl="10m",
        )
        with self.assertRaises(SecretAccessDeniedError):
            manager.resolve_secret(
                token_id=scoped.token_id,
                secret_key="SMTP_TOKEN",
                agent_id="ops-bot",
                tool_name="send_email",
                backend="dict",
            )

    def test_resolve_secret_reports_backend_or_key_errors(self) -> None:
        capabilities = CapabilityTokenManager()
        manager = SecretManager(
            capability_manager=capabilities,
            backends={"dict": _DictSecretBackend({"SMTP_TOKEN": "secret"})},
        )
        token = capabilities.issue(
            agent_id="ops-bot",
            tool_name="send_email",
            actions=["invoke"],
            secret_keys=["SMTP_TOKEN", "MISSING"],
            ttl="10m",
        )

        with self.assertRaises(SecretBackendNotFoundError):
            manager.resolve_secret(
                token_id=token.token_id,
                secret_key="SMTP_TOKEN",
                agent_id="ops-bot",
                tool_name="send_email",
                backend="unknown",
            )

        with self.assertRaises(SecretNotFoundError):
            manager.resolve_secret(
                token_id=token.token_id,
                secret_key="MISSING",
                agent_id="ops-bot",
                tool_name="send_email",
                backend="dict",
            )

    def test_safeai_api_exposes_secret_manager_flow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            sdk = SafeAI(
                policy_engine=_policy_engine(),
                classifier=Classifier(),
                audit_logger=AuditLogger(str(Path(tmp_dir) / "audit.log")),
            )
            sdk.register_secret_backend("dict", _DictSecretBackend({"SMTP_TOKEN": "s3cr3t"}))
            token = sdk.issue_capability_token(
                agent_id="ops-bot",
                tool_name="send_email",
                actions=["invoke"],
                secret_keys=["SMTP_TOKEN"],
                ttl="10m",
                session_id="sess-1",
            )

            resolved = sdk.resolve_secret(
                token_id=token.token_id,
                secret_key="SMTP_TOKEN",
                agent_id="ops-bot",
                tool_name="send_email",
                session_id="sess-1",
                backend="dict",
            )
            self.assertEqual(resolved.value, "s3cr3t")
            self.assertIn("dict", sdk.list_secret_backends())

            resolved_batch = sdk.resolve_secrets(
                token_id=token.token_id,
                secret_keys=["SMTP_TOKEN"],
                agent_id="ops-bot",
                tool_name="send_email",
                session_id="sess-1",
                backend="dict",
            )
            self.assertEqual(set(resolved_batch.keys()), {"SMTP_TOKEN"})


if __name__ == "__main__":
    unittest.main()
