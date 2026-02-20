"""Classifier taxonomy and policy tag-hierarchy tests."""

from __future__ import annotations

import unittest

from safeai.core.classifier import Classifier
from safeai.core.policy import PolicyContext, PolicyEngine, expand_tag_hierarchy, normalize_rules


class TagHierarchyTests(unittest.TestCase):
    def test_expand_tag_hierarchy_includes_parents(self) -> None:
        tags = expand_tag_hierarchy(["personal.pii", "secret.token"])
        self.assertEqual(tags, {"personal", "personal.pii", "secret", "secret.token"})

    def test_parent_policy_tag_matches_child_detection_tag(self) -> None:
        classifier = Classifier()
        detections = classifier.classify_text("Contact me at alice@example.com")
        tags = sorted({item.tag for item in detections})
        self.assertIn("personal.pii", tags)

        engine = PolicyEngine(
            normalize_rules(
                [
                    {
                        "name": "redact-personal-output",
                        "boundary": "output",
                        "priority": 1,
                        "condition": {"data_tags": ["personal"]},
                        "action": "redact",
                        "reason": "personal data restricted",
                    }
                ]
            )
        )

        decision = engine.evaluate(PolicyContext(boundary="output", data_tags=tags, agent_id="agent-1"))
        self.assertEqual(decision.action, "redact")
        self.assertEqual(decision.policy_name, "redact-personal-output")

    def test_child_policy_tag_does_not_match_parent_only_context(self) -> None:
        engine = PolicyEngine(
            normalize_rules(
                [
                    {
                        "name": "allow-pii-only",
                        "boundary": "output",
                        "priority": 1,
                        "condition": {"data_tags": ["personal.pii"]},
                        "action": "allow",
                        "reason": "pii explicitly allowed",
                    }
                ]
            )
        )

        decision = engine.evaluate(
            PolicyContext(boundary="output", data_tags=["personal"], agent_id="agent-1")
        )
        self.assertEqual(decision.action, "block")
        self.assertIsNone(decision.policy_name)

    def test_condition_string_and_case_variants_are_handled(self) -> None:
        engine = PolicyEngine(
            normalize_rules(
                [
                    {
                        "name": "allow-secret-tool-agent",
                        "boundary": "action",
                        "priority": 1,
                        "condition": {
                            "data_tags": "SECRET",
                            "tools": "mail.send",
                            "agents": "Agent-1",
                        },
                        "action": "allow",
                        "reason": "edge-case compatibility",
                    }
                ]
            )
        )

        decision = engine.evaluate(
            PolicyContext(
                boundary="action",
                data_tags=[" secret.token "],
                agent_id="Agent-1",
                tool_name="mail.send",
            )
        )
        self.assertEqual(decision.action, "allow")
        self.assertEqual(decision.policy_name, "allow-secret-tool-agent")

    def test_hierarchy_normalization_ignores_empty_segments(self) -> None:
        engine = PolicyEngine(
            normalize_rules(
                [
                    {
                        "name": "block-secret",
                        "boundary": "input",
                        "priority": 1,
                        "condition": {"data_tags": ["secret"]},
                        "action": "block",
                        "reason": "secrets are blocked",
                    }
                ]
            )
        )

        decision = engine.evaluate(
            PolicyContext(boundary="input", data_tags=["secret..credential"], agent_id="agent-1")
        )
        self.assertEqual(decision.action, "block")
        self.assertEqual(decision.policy_name, "block-secret")


if __name__ == "__main__":
    unittest.main()
