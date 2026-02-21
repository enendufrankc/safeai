"""Action-boundary interceptor request/response enforcement tests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from safeai.core.audit import AuditLogger
from safeai.core.contracts import ToolContractRegistry, normalize_contracts
from safeai.core.interceptor import ActionInterceptor, ToolCall
from safeai.core.policy import PolicyEngine, normalize_rules


def _contract_registry(
    *,
    accepts_tags: list[str],
    accepts_fields: list[str] | None = None,
    emits_tags: list[str],
    emits_fields: list[str] | None = None,
) -> ToolContractRegistry:
    return ToolContractRegistry(
        normalize_contracts(
            [
                {
                    "version": "v1alpha1",
                    "contract": {
                        "tool_name": "send_email",
                        "accepts": {
                            "tags": accepts_tags,
                            "fields": accepts_fields or [],
                        },
                        "emits": {
                            "tags": emits_tags,
                            "fields": emits_fields or [],
                        },
                        "side_effects": {
                            "reversible": False,
                            "requires_approval": True,
                        },
                    },
                }
            ]
        )
    )


class ActionInterceptorTests(unittest.TestCase):
    def _build_interceptor(
        self,
        *,
        policy_rules: list[dict],
        contract_registry: ToolContractRegistry | None = None,
        audit_log: Path,
    ) -> ActionInterceptor:
        engine = PolicyEngine(normalize_rules(policy_rules))
        return ActionInterceptor(
            policy_engine=engine,
            audit_logger=AuditLogger(str(audit_log)),
            contract_registry=contract_registry,
        )

    def test_request_blocks_undeclared_tool(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            audit_log = Path(tmp_dir) / "audit.jsonl"
            interceptor = self._build_interceptor(
                policy_rules=[
                    {
                        "name": "allow-action-default",
                        "boundary": ["action"],
                        "action": "allow",
                        "reason": "allow",
                        "priority": 1000,
                    }
                ],
                contract_registry=ToolContractRegistry(),
                audit_log=audit_log,
            )
            result = interceptor.intercept_request(
                ToolCall(
                    tool_name="send_email",
                    agent_id="agent-1",
                    parameters={"to": "a@example.com"},
                    data_tags=["internal"],
                )
            )
            self.assertEqual(result.decision.action, "block")
            self.assertEqual(result.filtered_params, {})
            self.assertEqual(result.unauthorized_tags, ["internal"])

    def test_request_filters_fields_by_contract_accepts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            audit_log = Path(tmp_dir) / "audit.jsonl"
            interceptor = self._build_interceptor(
                policy_rules=[
                    {
                        "name": "allow-action-default",
                        "boundary": ["action"],
                        "action": "allow",
                        "reason": "allow",
                        "priority": 1000,
                    }
                ],
                contract_registry=_contract_registry(
                    accepts_tags=["internal"],
                    accepts_fields=["to", "subject"],
                    emits_tags=["internal"],
                ),
                audit_log=audit_log,
            )
            result = interceptor.intercept_request(
                ToolCall(
                    tool_name="send_email",
                    agent_id="agent-1",
                    parameters={
                        "to": "a@example.com",
                        "subject": "hello",
                        "body": "please send this",
                    },
                    data_tags=["internal"],
                )
            )
            self.assertEqual(result.decision.action, "allow")
            self.assertEqual(result.filtered_params, {"to": "a@example.com", "subject": "hello"})
            self.assertEqual(result.stripped_fields, ["body"])

    def test_response_strips_fields_not_declared_in_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            audit_log = Path(tmp_dir) / "audit.jsonl"
            logger = AuditLogger(str(audit_log))
            interceptor = ActionInterceptor(
                policy_engine=PolicyEngine(
                    normalize_rules(
                        [
                            {
                                "name": "allow-action-default",
                                "boundary": ["action"],
                                "action": "allow",
                                "reason": "allow",
                                "priority": 1000,
                            }
                        ]
                    )
                ),
                audit_logger=logger,
                contract_registry=_contract_registry(
                    accepts_tags=["internal"],
                    emits_tags=["internal"],
                    emits_fields=["status"],
                ),
            )
            result = interceptor.intercept_response(
                ToolCall(
                    tool_name="send_email",
                    agent_id="agent-1",
                    parameters={},
                    data_tags=["internal"],
                ),
                {"status": "sent", "message_id": "abc-123"},
            )
            self.assertEqual(result.filtered_response, {"status": "sent"})
            self.assertEqual(result.stripped_fields, ["message_id"])
            events = logger.query(boundary="action", tool_name="send_email")
            self.assertEqual(events[0]["metadata"]["stripped_fields"], ["message_id"])

    def test_response_strips_fields_with_unauthorized_emitted_tags(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            interceptor = self._build_interceptor(
                policy_rules=[
                    {
                        "name": "allow-action-default",
                        "boundary": ["action"],
                        "action": "allow",
                        "reason": "allow",
                        "priority": 1000,
                    }
                ],
                contract_registry=_contract_registry(
                    accepts_tags=["internal"],
                    emits_tags=["internal"],
                ),
                audit_log=Path(tmp_dir) / "audit.jsonl",
            )
            result = interceptor.intercept_response(
                ToolCall(
                    tool_name="send_email",
                    agent_id="agent-1",
                    parameters={},
                    data_tags=["internal"],
                ),
                {"status": "ok", "recipient": "alice@example.com"},
            )
            self.assertEqual(result.filtered_response, {"status": "ok"})
            self.assertEqual(result.stripped_fields, ["recipient"])
            self.assertEqual(result.stripped_tags, ["personal.pii"])

    def test_response_strips_fields_blocked_by_agent_policy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            interceptor = self._build_interceptor(
                policy_rules=[
                    {
                        "name": "block-personal-for-guest",
                        "boundary": ["action"],
                        "action": "block",
                        "reason": "guest cannot receive personal data",
                        "priority": 10,
                        "condition": {"agents": ["guest"], "data_tags": ["personal"]},
                    },
                    {
                        "name": "allow-action-default",
                        "boundary": ["action"],
                        "action": "allow",
                        "reason": "allow",
                        "priority": 1000,
                    },
                ],
                contract_registry=_contract_registry(
                    accepts_tags=["internal"],
                    emits_tags=["personal", "internal"],
                ),
                audit_log=Path(tmp_dir) / "audit.jsonl",
            )
            result = interceptor.intercept_response(
                ToolCall(
                    tool_name="send_email",
                    agent_id="guest",
                    parameters={},
                    data_tags=["internal"],
                ),
                {"recipient": "alice@example.com", "status": "ok"},
            )
            self.assertEqual(result.filtered_response, {"status": "ok"})
            self.assertEqual(result.stripped_fields, ["recipient"])
            self.assertIn("personal.pii", result.stripped_tags)


if __name__ == "__main__":
    unittest.main()
