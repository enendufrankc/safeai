"""Tests for the metadata sanitizer."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from safeai.intelligence.sanitizer import (
    BANNED_METADATA_KEYS,
    SAFE_METADATA_KEYS,
    CodebaseStructure,
    MetadataSanitizer,
    SanitizedAuditAggregate,
    SanitizedAuditEvent,
)


class SanitizedAuditEventTests(unittest.TestCase):
    def test_frozen_dataclass(self) -> None:
        event = SanitizedAuditEvent(event_id="evt_1", boundary="input")
        self.assertEqual(event.event_id, "evt_1")
        with self.assertRaises(AttributeError):
            event.event_id = "changed"  # type: ignore[misc]

    def test_default_values(self) -> None:
        event = SanitizedAuditEvent()
        self.assertEqual(event.event_id, "")
        self.assertEqual(event.data_tags, ())
        self.assertEqual(event.safe_metadata, {})


class SanitizeEventTests(unittest.TestCase):
    def setUp(self) -> None:
        self.sanitizer = MetadataSanitizer()

    def test_passthrough_keys(self) -> None:
        event = {
            "event_id": "evt_123",
            "timestamp": "2025-01-01T00:00:00Z",
            "boundary": "input",
            "action": "block",
            "policy_name": "block-secrets",
            "reason": "secret detected",
            "data_tags": ["secret.credential"],
            "agent_id": "agent-1",
            "tool_name": "shell",
            "session_id": "sess-1",
        }
        result = self.sanitizer.sanitize_event(event)
        self.assertEqual(result.event_id, "evt_123")
        self.assertEqual(result.boundary, "input")
        self.assertEqual(result.action, "block")
        self.assertEqual(result.data_tags, ("secret.credential",))

    def test_banned_keys_stripped(self) -> None:
        event = {
            "event_id": "evt_1",
            "boundary": "input",
            "action": "block",
            "metadata": {
                "secret_key": "SUPER_SECRET_123",
                "capability_token_id": "tok_abc",
                "matched_value": "sk-1234abcd",
                "raw_content": "the full message with secrets",
                "raw_input": "user input text",
                "raw_output": "assistant response text",
                "phase": "secret_resolve",
                "result": "allow",
            },
        }
        result = self.sanitizer.sanitize_event(event)
        # Banned keys must not appear
        for banned_key in BANNED_METADATA_KEYS:
            self.assertNotIn(banned_key, result.safe_metadata)
        # Safe keys should pass through
        self.assertEqual(result.safe_metadata.get("phase"), "secret_resolve")
        self.assertEqual(result.safe_metadata.get("result"), "allow")

    def test_no_raw_content_leaks(self) -> None:
        """Property test: no banned key value should appear anywhere in the sanitized event."""
        secret_values = {
            "secret_key": "MY_API_KEY_VALUE",
            "capability_token_id": "cap_tok_123456",
            "matched_value": "sk-proj-abc123def456",
            "raw_content": "This is the full unredacted content with PII john@example.com",
            "raw_input": "Full input prompt with secrets",
            "raw_output": "Full output response with PII",
        }
        event = {
            "event_id": "evt_1",
            "boundary": "input",
            "action": "block",
            "metadata": {
                **secret_values,
                "phase": "scan",
                "action_type": "input_scan",
            },
        }
        result = self.sanitizer.sanitize_event(event)
        result_str = str(result)
        for key, value in secret_values.items():
            self.assertNotIn(
                value,
                result_str,
                f"Banned value for '{key}' leaked into sanitized event",
            )

    def test_safe_metadata_keys_pass(self) -> None:
        metadata = {k: f"value_{k}" for k in SAFE_METADATA_KEYS}
        event = {"event_id": "evt_1", "boundary": "input", "action": "allow", "metadata": metadata}
        result = self.sanitizer.sanitize_event(event)
        for key in SAFE_METADATA_KEYS:
            self.assertIn(key, result.safe_metadata)

    def test_missing_metadata(self) -> None:
        event = {"event_id": "evt_1", "boundary": "input", "action": "allow"}
        result = self.sanitizer.sanitize_event(event)
        self.assertEqual(result.safe_metadata, {})

    def test_missing_fields_default_to_empty_string(self) -> None:
        result = self.sanitizer.sanitize_event({})
        self.assertEqual(result.event_id, "")
        self.assertEqual(result.boundary, "")
        self.assertEqual(result.data_tags, ())


class AggregateEventsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.sanitizer = MetadataSanitizer()
        self.events = [
            {"action": "block", "boundary": "input", "policy_name": "p1", "agent_id": "a1", "tool_name": "t1", "data_tags": ["secret"]},
            {"action": "allow", "boundary": "output", "policy_name": "p2", "agent_id": "a1", "tool_name": "t2", "data_tags": ["personal"]},
            {"action": "block", "boundary": "input", "policy_name": "p1", "agent_id": "a2", "tool_name": "t1", "data_tags": ["secret", "personal"]},
        ]

    def test_total_events(self) -> None:
        agg = self.sanitizer.aggregate_events(self.events)
        self.assertEqual(agg.total_events, 3)

    def test_events_by_action(self) -> None:
        agg = self.sanitizer.aggregate_events(self.events)
        self.assertEqual(agg.events_by_action["block"], 2)
        self.assertEqual(agg.events_by_action["allow"], 1)

    def test_events_by_boundary(self) -> None:
        agg = self.sanitizer.aggregate_events(self.events)
        self.assertEqual(agg.events_by_boundary["input"], 2)
        self.assertEqual(agg.events_by_boundary["output"], 1)

    def test_events_by_tag(self) -> None:
        agg = self.sanitizer.aggregate_events(self.events)
        self.assertEqual(agg.events_by_tag["secret"], 2)
        self.assertEqual(agg.events_by_tag["personal"], 2)

    def test_empty_events(self) -> None:
        agg = self.sanitizer.aggregate_events([])
        self.assertEqual(agg.total_events, 0)
        self.assertEqual(agg.events_by_action, {})

    def test_aggregate_accuracy(self) -> None:
        """All action counts should sum to total_events."""
        agg = self.sanitizer.aggregate_events(self.events)
        self.assertEqual(sum(agg.events_by_action.values()), agg.total_events)
        self.assertEqual(sum(agg.events_by_boundary.values()), agg.total_events)


class CodebaseStructureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.sanitizer = MetadataSanitizer()
        self.tmpdir = tempfile.mkdtemp()
        # Create a small Python project
        Path(self.tmpdir, "main.py").write_text(
            "import os\nfrom pathlib import Path\n\n"
            "class MyApp:\n    pass\n\n"
            "def run():\n    pass\n",
            encoding="utf-8",
        )
        Path(self.tmpdir, "utils.py").write_text(
            "import json\n\ndef helper():\n    pass\n",
            encoding="utf-8",
        )
        Path(self.tmpdir, "pyproject.toml").write_text(
            '[project]\nname = "test"\ndependencies = [\n  "click>=8.1",\n  "httpx>=0.27",\n]\n',
            encoding="utf-8",
        )

    def test_finds_python_files(self) -> None:
        structure = self.sanitizer.extract_codebase_structure(self.tmpdir)
        py_files = [f for f in structure.file_paths if f.endswith(".py")]
        self.assertGreaterEqual(len(py_files), 2)

    def test_extracts_classes(self) -> None:
        structure = self.sanitizer.extract_codebase_structure(self.tmpdir)
        self.assertIn("MyApp", structure.class_names)

    def test_extracts_functions(self) -> None:
        structure = self.sanitizer.extract_codebase_structure(self.tmpdir)
        self.assertIn("run", structure.function_names)
        self.assertIn("helper", structure.function_names)

    def test_extracts_imports(self) -> None:
        structure = self.sanitizer.extract_codebase_structure(self.tmpdir)
        self.assertIn("os", structure.imports)
        self.assertIn("json", structure.imports)

    def test_extracts_dependencies(self) -> None:
        structure = self.sanitizer.extract_codebase_structure(self.tmpdir)
        self.assertIn("click", structure.dependencies)
        self.assertIn("httpx", structure.dependencies)

    def test_finds_config_files(self) -> None:
        structure = self.sanitizer.extract_codebase_structure(self.tmpdir)
        toml_files = [f for f in structure.file_paths if f.endswith(".toml")]
        self.assertGreaterEqual(len(toml_files), 1)

    def test_skips_hidden_directories(self) -> None:
        hidden = Path(self.tmpdir, ".hidden")
        hidden.mkdir()
        Path(hidden, "secret.py").write_text("x = 1\n", encoding="utf-8")
        structure = self.sanitizer.extract_codebase_structure(self.tmpdir)
        self.assertNotIn(".hidden/secret.py", structure.file_paths)


if __name__ == "__main__":
    unittest.main()
