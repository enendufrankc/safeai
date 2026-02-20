"""Policy engine unit tests for evaluation and reload behavior."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from safeai.core.policy import PolicyContext, PolicyEngine, PolicyRule, normalize_rules


class PolicyEngineEvaluationTests(unittest.TestCase):
    def test_evaluate_uses_first_matching_rule_by_priority(self) -> None:
        rules = normalize_rules(
            [
                {
                    "name": "allow-input-default",
                    "boundary": "input",
                    "priority": 100,
                    "action": "allow",
                    "reason": "default allow",
                },
                {
                    "name": "block-secret",
                    "boundary": "input",
                    "priority": 10,
                    "condition": {"data_tags": ["secret.credential"]},
                    "action": "block",
                    "reason": "secrets blocked",
                },
            ]
        )
        engine = PolicyEngine(rules)

        decision = engine.evaluate(
            PolicyContext(boundary="input", data_tags=["secret.credential"], agent_id="agent-1")
        )

        self.assertEqual(decision.action, "block")
        self.assertEqual(decision.policy_name, "block-secret")
        self.assertEqual(decision.reason, "secrets blocked")

    def test_evaluate_defaults_to_deny_when_no_rule_matches(self) -> None:
        rules = normalize_rules(
            [
                {
                    "name": "allow-input",
                    "boundary": "input",
                    "priority": 5,
                    "action": "allow",
                    "reason": "allow input",
                }
            ]
        )
        engine = PolicyEngine(rules)

        decision = engine.evaluate(PolicyContext(boundary="output", data_tags=[], agent_id="agent-1"))

        self.assertEqual(decision.action, "block")
        self.assertIsNone(decision.policy_name)
        self.assertEqual(decision.reason, "default deny")

    def test_evaluate_matches_tool_and_agent_conditions(self) -> None:
        rules = normalize_rules(
            [
                {
                    "name": "allow-approved-tool-agent",
                    "boundary": "action",
                    "priority": 1,
                    "condition": {"tools": ["calendar.create"], "agents": ["agent-007"]},
                    "action": "allow",
                    "reason": "approved",
                }
            ]
        )
        engine = PolicyEngine(rules)

        matched = engine.evaluate(
            PolicyContext(
                boundary="action",
                data_tags=[],
                agent_id="agent-007",
                tool_name="calendar.create",
            )
        )
        blocked = engine.evaluate(
            PolicyContext(
                boundary="action",
                data_tags=[],
                agent_id="agent-999",
                tool_name="calendar.create",
            )
        )

        self.assertEqual(matched.action, "allow")
        self.assertEqual(matched.policy_name, "allow-approved-tool-agent")
        self.assertEqual(blocked.action, "block")
        self.assertIsNone(blocked.policy_name)


class PolicyEngineReloadTests(unittest.TestCase):
    def test_reload_and_reload_if_changed_return_false_without_registration(self) -> None:
        engine = PolicyEngine()

        self.assertFalse(engine.reload())
        self.assertFalse(engine.reload_if_changed())

    def test_reload_if_changed_updates_rules_when_file_mtime_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            watch_file = Path(temp_dir) / "policy.yaml"
            watch_file.write_text("version: v1alpha1\n", encoding="utf-8")

            state = {"action": "block"}
            callback_calls: list[str] = []

            def loader() -> list[PolicyRule]:
                callback_calls.append(state["action"])
                return [
                    PolicyRule(
                        name="dynamic-rule",
                        boundary=["output"],
                        action=state["action"],
                        reason="dynamic",
                        condition={},
                        priority=1,
                    )
                ]

            engine = PolicyEngine(loader())
            engine.register_reload([watch_file], loader)
            context = PolicyContext(boundary="output", data_tags=[], agent_id="agent-1")

            self.assertEqual(engine.evaluate(context).action, "block")
            self.assertFalse(engine.reload_if_changed())

            state["action"] = "allow"
            now = watch_file.stat().st_mtime_ns
            os.utime(watch_file, ns=(now + 5_000_000, now + 5_000_000))

            self.assertTrue(engine.reload_if_changed())
            self.assertEqual(engine.evaluate(context).action, "allow")
            self.assertFalse(engine.reload_if_changed())
            self.assertEqual(callback_calls, ["block", "allow"])

    def test_reload_forces_callback_even_without_file_change(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            watch_file = Path(temp_dir) / "policy.yaml"
            watch_file.write_text("version: v1alpha1\n", encoding="utf-8")

            call_count = {"count": 0}

            def loader() -> list[PolicyRule]:
                call_count["count"] += 1
                return [
                    PolicyRule(
                        name="forced-rule",
                        boundary=["input"],
                        action="allow",
                        reason="forced",
                        condition={},
                        priority=1,
                    )
                ]

            engine = PolicyEngine()
            engine.register_reload([watch_file], loader)

            self.assertTrue(engine.reload())
            self.assertTrue(engine.reload())
            self.assertEqual(call_count["count"], 2)


if __name__ == "__main__":
    unittest.main()
