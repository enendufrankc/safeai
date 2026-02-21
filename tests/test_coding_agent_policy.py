"""Tests for the coding-agent policy template."""

from __future__ import annotations

import unittest
from pathlib import Path

import yaml


class CodingAgentPolicyTests(unittest.TestCase):
    """Validate the coding-agent.yaml policy template."""

    @classmethod
    def setUpClass(cls) -> None:
        policy_path = (
            Path(__file__).resolve().parent.parent
            / "safeai"
            / "config"
            / "defaults"
            / "policies"
            / "templates"
            / "coding-agent.yaml"
        )
        cls.policy_path = policy_path
        cls.doc = yaml.safe_load(policy_path.read_text(encoding="utf-8"))

    def test_file_exists(self) -> None:
        self.assertTrue(self.policy_path.exists())

    def test_version_is_v1alpha1(self) -> None:
        self.assertEqual(self.doc["version"], "v1alpha1")

    def test_has_policies_list(self) -> None:
        self.assertIsInstance(self.doc["policies"], list)
        self.assertGreaterEqual(len(self.doc["policies"]), 5)

    def test_block_secrets_rule(self) -> None:
        rule = self._find_rule("block-secrets-everywhere")
        self.assertIsNotNone(rule)
        self.assertEqual(rule["action"], "block")
        self.assertEqual(rule["priority"], 10)
        self.assertIn("input", rule["boundary"])
        self.assertIn("output", rule["boundary"])
        self.assertIn("secret", rule["condition"]["data_tags"])

    def test_block_dangerous_commands_rule(self) -> None:
        rule = self._find_rule("block-dangerous-commands")
        self.assertIsNotNone(rule)
        self.assertEqual(rule["action"], "block")
        self.assertEqual(rule["priority"], 15)
        self.assertIn("dangerous.command", rule["condition"]["data_tags"])
        self.assertIn("shell", rule["condition"]["tools"])

    def test_redact_pii_output_rule(self) -> None:
        rule = self._find_rule("redact-pii-in-output")
        self.assertIsNotNone(rule)
        self.assertEqual(rule["action"], "redact")
        self.assertIn("personal", rule["condition"]["data_tags"])

    def test_require_approval_destructive_rule(self) -> None:
        rule = self._find_rule("require-approval-destructive")
        self.assertIsNotNone(rule)
        self.assertEqual(rule["action"], "require_approval")
        self.assertIn("destructive", rule["condition"]["data_tags"])

    def test_default_allow_is_last(self) -> None:
        policies = self.doc["policies"]
        last = policies[-1]
        self.assertEqual(last["name"], "allow-by-default")
        self.assertEqual(last["action"], "allow")
        self.assertEqual(last["priority"], 1000)

    def test_priorities_ascending(self) -> None:
        policies = self.doc["policies"]
        priorities = [p["priority"] for p in policies]
        self.assertEqual(priorities, sorted(priorities))

    def test_tools_include_generic_and_agent_specific(self) -> None:
        rule = self._find_rule("block-dangerous-commands")
        tools = rule["condition"]["tools"]
        # Generic category
        self.assertIn("shell", tools)
        # Agent-specific
        self.assertIn("Bash", tools)

    def _find_rule(self, name: str) -> dict | None:
        for policy in self.doc["policies"]:
            if policy["name"] == name:
                return policy
        return None


if __name__ == "__main__":
    unittest.main()
