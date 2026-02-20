"""Output fallback template tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from safeai.core.audit import AuditLogger
from safeai.core.classifier import Classifier
from safeai.core.guard import OutputGuard
from safeai.core.policy import PolicyEngine, normalize_rules


def _build_guard(rules: list[dict], audit_file: Path) -> OutputGuard:
    engine = PolicyEngine(normalize_rules(rules))
    return OutputGuard(classifier=Classifier(), policy_engine=engine, audit_logger=AuditLogger(str(audit_file)))


class OutputFallbackTests(unittest.TestCase):
    def test_block_without_fallback_returns_empty_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            guard = _build_guard(
                [
                    {
                        "name": "block-all-output",
                        "boundary": "output",
                        "priority": 1,
                        "action": "block",
                        "reason": "blocked by policy",
                    }
                ],
                Path(temp_dir) / "audit.log",
            )

            result = guard.guard("plain text", agent_id="agent-1")
            self.assertEqual(result.safe_output, "")
            self.assertFalse(result.fallback_used)

    def test_block_with_fallback_template_renders_context(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            audit_file = Path(temp_dir) / "audit.log"
            guard = _build_guard(
                [
                    {
                        "name": "block-all-output",
                        "boundary": "output",
                        "priority": 1,
                        "action": "block",
                        "reason": "blocked by policy",
                        "fallback_template": "I cannot share that. ({policy_name}: {reason})",
                    }
                ],
                audit_file,
            )

            result = guard.guard("plain text", agent_id="agent-1")
            self.assertEqual(result.safe_output, "I cannot share that. (block-all-output: blocked by policy)")
            self.assertTrue(result.fallback_used)
            self.assertEqual(result.decision.fallback_template, "I cannot share that. ({policy_name}: {reason})")

            payload = json.loads(audit_file.read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(payload["metadata"]["fallback_used"], True)

    def test_redact_with_fallback_can_embed_redacted_text(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            guard = _build_guard(
                [
                    {
                        "name": "redact-personal",
                        "boundary": "output",
                        "priority": 1,
                        "condition": {"data_tags": ["personal"]},
                        "action": "redact",
                        "reason": "personal data restricted",
                        "fallback_template": "Sanitized response: {redacted}",
                    }
                ],
                Path(temp_dir) / "audit.log",
            )

            result = guard.guard("Email me at alice@example.com", agent_id="agent-1")
            self.assertIn("Sanitized response:", result.safe_output)
            self.assertIn("[REDACTED]", result.safe_output)
            self.assertTrue(result.fallback_used)

    def test_redact_without_fallback_keeps_default_redaction(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            guard = _build_guard(
                [
                    {
                        "name": "redact-personal",
                        "boundary": "output",
                        "priority": 1,
                        "condition": {"data_tags": ["personal"]},
                        "action": "redact",
                        "reason": "personal data restricted",
                    }
                ],
                Path(temp_dir) / "audit.log",
            )

            result = guard.guard("Email me at alice@example.com", agent_id="agent-1")
            self.assertIn("[REDACTED]", result.safe_output)
            self.assertFalse(result.fallback_used)

    def test_unknown_template_fields_are_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            guard = _build_guard(
                [
                    {
                        "name": "block-all-output",
                        "boundary": "output",
                        "priority": 1,
                        "action": "block",
                        "reason": "blocked by policy",
                        "fallback_template": "Fallback {unknown} {reason}",
                    }
                ],
                Path(temp_dir) / "audit.log",
            )

            result = guard.guard("plain text", agent_id="agent-1")
            self.assertEqual(result.safe_output, "Fallback {unknown} blocked by policy")
            self.assertTrue(result.fallback_used)

    def test_invalid_template_safely_returns_literal_template(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            guard = _build_guard(
                [
                    {
                        "name": "block-all-output",
                        "boundary": "output",
                        "priority": 1,
                        "action": "block",
                        "reason": "blocked by policy",
                        "fallback_template": "bad {reason",
                    }
                ],
                Path(temp_dir) / "audit.log",
            )

            result = guard.guard("plain text", agent_id="agent-1")
            self.assertEqual(result.safe_output, "bad {reason")
            self.assertTrue(result.fallback_used)


if __name__ == "__main__":
    unittest.main()
