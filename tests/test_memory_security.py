"""Phase 3 memory retention and encrypted handle tests."""

from __future__ import annotations

import tempfile
import unittest
from datetime import timezone
from pathlib import Path

from safeai import SafeAI
from safeai.core.audit import AuditLogger
from safeai.core.classifier import Classifier
from safeai.core.memory import MemoryController
from safeai.core.policy import PolicyEngine, normalize_rules


def _memory_docs(*, tag: str = "internal", encrypted: bool = True, retention: str = "1h") -> list[dict]:
    return [
        {
            "version": "v1alpha1",
            "memory": {
                "name": "phase3-memory",
                "scope": "session",
                "max_entries": 100,
                "default_retention": retention,
                "fields": [
                    {
                        "name": "secret_value",
                        "type": "string",
                        "tag": tag,
                        "retention": retention,
                        "encrypted": encrypted,
                    }
                ],
            },
        }
    ]


def _policy_engine(*, block_secret: bool = False) -> PolicyEngine:
    rules = []
    if block_secret:
        rules.append(
            {
                "name": "block-secret-actions",
                "boundary": ["action"],
                "priority": 10,
                "condition": {"data_tags": ["secret"]},
                "action": "block",
                "reason": "secrets blocked",
            }
        )
    rules.append(
        {
            "name": "allow-default",
            "boundary": ["action", "input", "output"],
            "priority": 1000,
            "action": "allow",
            "reason": "allow",
        }
    )
    return PolicyEngine(normalize_rules(rules))


class MemorySecurityTests(unittest.TestCase):
    def test_encrypted_memory_field_returns_handle_and_resolves_for_owner(self) -> None:
        memory = MemoryController.from_documents(_memory_docs(tag="internal", encrypted=True))
        self.assertTrue(memory.write("secret_value", "abc123", agent_id="agent-1"))
        handle = memory.read("secret_value", agent_id="agent-1")
        self.assertIsInstance(handle, str)
        self.assertTrue(str(handle).startswith("hdl_"))
        self.assertEqual(memory.resolve_handle(str(handle), agent_id="agent-1"), "abc123")
        with self.assertRaises(PermissionError):
            memory.resolve_handle(str(handle), agent_id="agent-2")

    def test_expired_encrypted_entries_are_removed_from_handle_store(self) -> None:
        memory = MemoryController.from_documents(_memory_docs(tag="internal", encrypted=True, retention="1s"))
        self.assertTrue(memory.write("secret_value", "abc123", agent_id="agent-1"))
        handle = str(memory.read("secret_value", agent_id="agent-1"))

        entry = memory._data["agent-1"]["secret_value"]  # noqa: SLF001 - intentional test visibility.
        memory._data["agent-1"]["secret_value"] = entry.__class__(
            value=entry.value,
            expires_at=entry.expires_at.replace(year=2000),
            tag=entry.tag,
            encrypted=entry.encrypted,
        )
        self.assertEqual(memory.purge_expired(), 1)
        self.assertIsNone(memory.handle_metadata(handle))
        with self.assertRaises(KeyError):
            memory.resolve_handle(handle, agent_id="agent-1")

    def test_safeai_handle_resolution_is_policy_gated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            sdk = SafeAI(
                policy_engine=_policy_engine(block_secret=True),
                classifier=Classifier(),
                audit_logger=AuditLogger(str(Path(tmp_dir) / "audit.log")),
                memory_controller=MemoryController.from_documents(_memory_docs(tag="secret", encrypted=True)),
            )
            self.assertTrue(sdk.memory_write("secret_value", "super-secret", agent_id="agent-1"))
            handle = sdk.memory_read("secret_value", agent_id="agent-1")
            self.assertTrue(str(handle).startswith("hdl_"))
            self.assertIsNone(sdk.resolve_memory_handle(str(handle), agent_id="agent-1"))

    def test_memory_auto_purge_emits_audit_event(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            sdk = SafeAI(
                policy_engine=_policy_engine(),
                classifier=Classifier(),
                audit_logger=AuditLogger(str(Path(tmp_dir) / "audit.log")),
                memory_controller=MemoryController.from_documents(_memory_docs(tag="internal", encrypted=False)),
            )
            self.assertTrue(sdk.memory_write("secret_value", "kept", agent_id="agent-1"))

            entry = sdk.memory._data["agent-1"]["secret_value"]  # noqa: SLF001 - test-only access.
            sdk.memory._data["agent-1"]["secret_value"] = entry.__class__(
                value=entry.value,
                expires_at=entry.expires_at.replace(year=2000, tzinfo=timezone.utc),
                tag=entry.tag,
                encrypted=entry.encrypted,
            )
            self.assertIsNone(sdk.memory_read("secret_value", agent_id="agent-1"))
            events = sdk.query_audit(boundary="memory", phase="retention_purge", limit=10)
            self.assertGreaterEqual(len(events), 1)
            self.assertGreaterEqual(int(events[0]["metadata"]["purged_count"]), 1)


if __name__ == "__main__":
    unittest.main()
