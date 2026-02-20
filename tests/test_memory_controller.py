"""Memory schema enforcement and retention tests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from safeai import SafeAI
from safeai.core.memory import MemoryController


def _memory_docs(default_retention: str = "1h") -> list[dict]:
    return [
        {
            "version": "v1alpha1",
            "memory": {
                "name": "unit-test-memory",
                "scope": "session",
                "max_entries": 2,
                "default_retention": default_retention,
                "fields": [
                    {"name": "nickname", "type": "string", "tag": "internal", "retention": "1h"},
                    {"name": "age", "type": "integer", "tag": "personal", "retention": "1h"},
                ],
            },
        }
    ]


class MemoryControllerTests(unittest.TestCase):
    def test_write_and_read_allowed_field(self) -> None:
        memory = MemoryController.from_documents(_memory_docs())
        self.assertTrue(memory.write("nickname", "frank", agent_id="agent-1"))
        self.assertEqual(memory.read("nickname", agent_id="agent-1"), "frank")

    def test_write_rejects_unknown_fields(self) -> None:
        memory = MemoryController.from_documents(_memory_docs())
        self.assertFalse(memory.write("unknown_key", "value", agent_id="agent-1"))

    def test_write_rejects_type_mismatch(self) -> None:
        memory = MemoryController.from_documents(_memory_docs())
        self.assertFalse(memory.write("age", "thirty", agent_id="agent-1"))
        self.assertIsNone(memory.read("age", agent_id="agent-1"))

    def test_max_entries_is_enforced(self) -> None:
        memory = MemoryController.from_documents(
            [
                {
                    "version": "v1alpha1",
                    "memory": {
                        "name": "unit-test-memory",
                        "scope": "session",
                        "max_entries": 1,
                        "default_retention": "1h",
                        "fields": [
                            {"name": "nickname", "type": "string", "tag": "internal"},
                            {"name": "age", "type": "integer", "tag": "personal"},
                        ],
                    },
                }
            ]
        )
        self.assertTrue(memory.write("nickname", "frank", agent_id="agent-1"))
        self.assertFalse(memory.write("age", 30, agent_id="agent-1"))

    def test_purge_expired_removes_entries(self) -> None:
        memory = MemoryController.from_documents(
            [
                {
                    "version": "v1alpha1",
                    "memory": {
                        "name": "unit-test-memory",
                        "scope": "session",
                        "max_entries": 10,
                        "default_retention": "1s",
                        "fields": [{"name": "nickname", "type": "string", "tag": "internal", "retention": "1s"}],
                    },
                }
            ]
        )
        self.assertTrue(memory.write("nickname", "frank", agent_id="agent-1"))
        self.assertEqual(memory.purge_expired(), 0)

        # Force expiration by manipulating stored entry.
        entry = memory._data["agent-1"]["nickname"]  # noqa: SLF001 - test-only assertion.
        memory._data["agent-1"]["nickname"] = entry.__class__(
            value=entry.value,
            expires_at=entry.expires_at.replace(year=2000),
            tag=entry.tag,
            encrypted=entry.encrypted,
        )
        self.assertEqual(memory.purge_expired(), 1)
        self.assertIsNone(memory.read("nickname", agent_id="agent-1"))

    def test_safeai_from_config_loads_memory_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            work = Path(tmp_dir)
            (work / "policies").mkdir(parents=True, exist_ok=True)
            (work / "schemas").mkdir(parents=True, exist_ok=True)

            (work / "safeai.yaml").write_text(
                "\n".join(
                    [
                        "version: v1alpha1",
                        "paths:",
                        "  policy_files:",
                        "    - policies/default.yaml",
                        "  memory_schema_files:",
                        "    - schemas/memory.yaml",
                        "audit:",
                        "  file_path: logs/audit.log",
                    ]
                ),
                encoding="utf-8",
            )
            (work / "policies" / "default.yaml").write_text(
                "\n".join(
                    [
                        "version: v1alpha1",
                        "policy:",
                        "  name: allow-all-input",
                        "  boundary: input",
                        "  action: allow",
                        "  reason: allow",
                    ]
                ),
                encoding="utf-8",
            )
            (work / "schemas" / "memory.yaml").write_text(
                "\n".join(
                    [
                        "version: v1alpha1",
                        "memory:",
                        "  name: app-memory",
                        "  scope: session",
                        "  max_entries: 10",
                        "  default_retention: 24h",
                        "  fields:",
                        "    - name: nickname",
                        "      type: string",
                        "      tag: internal",
                    ]
                ),
                encoding="utf-8",
            )

            sdk = SafeAI.from_config(work / "safeai.yaml")
            self.assertIsNotNone(sdk.memory)
            self.assertTrue(sdk.memory_write("nickname", "frank", agent_id="agent-1"))
            self.assertEqual(sdk.memory_read("nickname", agent_id="agent-1"), "frank")


if __name__ == "__main__":
    unittest.main()
