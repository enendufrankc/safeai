"""Approval workflow runtime and CLI tests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import yaml
from click.testing import CliRunner

from safeai import SafeAI
from safeai.cli.init import init_command
from safeai.cli.main import cli
from safeai.core.approval import ApprovalManager
from safeai.core.audit import AuditLogger
from safeai.core.contracts import ToolContractRegistry, normalize_contracts
from safeai.core.interceptor import ActionInterceptor, ToolCall
from safeai.core.policy import PolicyEngine, normalize_rules


def _contract_registry() -> ToolContractRegistry:
    return ToolContractRegistry(
        normalize_contracts(
            [
                {
                    "version": "v1alpha1",
                    "contract": {
                        "tool_name": "send_email",
                        "accepts": {"tags": ["internal"], "fields": ["to", "subject", "body"]},
                        "emits": {"tags": ["internal"], "fields": ["status"]},
                        "side_effects": {"reversible": False, "requires_approval": False},
                    },
                }
            ]
        )
    )


class ApprovalWorkflowTests(unittest.TestCase):
    def test_policy_requires_approval_then_allows_after_decision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            approvals = ApprovalManager(file_path=root / "approvals.log", default_ttl="30m")
            interceptor = ActionInterceptor(
                policy_engine=PolicyEngine(
                    normalize_rules(
                        [
                            {
                                "name": "email-requires-approval",
                                "boundary": ["action"],
                                "priority": 10,
                                "condition": {"tools": ["send_email"], "data_tags": ["internal"]},
                                "action": "require_approval",
                                "reason": "email send requires approval",
                            },
                            {
                                "name": "allow-default-action",
                                "boundary": ["action"],
                                "priority": 1000,
                                "action": "allow",
                                "reason": "allow",
                            },
                        ]
                    )
                ),
                audit_logger=AuditLogger(str(root / "audit.log")),
                contract_registry=_contract_registry(),
                approval_manager=approvals,
            )

            call = ToolCall(
                tool_name="send_email",
                agent_id="ops-bot",
                parameters={"to": "ops@example.com", "subject": "s", "body": "b"},
                data_tags=["internal"],
                session_id="sess-1",
            )
            pending = interceptor.intercept_request(call)
            self.assertEqual(pending.decision.action, "require_approval")

            rows = approvals.list_requests(status="pending")
            self.assertEqual(len(rows), 1)
            self.assertTrue(approvals.approve(rows[0].request_id, approver_id="security-oncall", note="ok"))

            allowed = interceptor.intercept_request(
                ToolCall(
                    tool_name="send_email",
                    agent_id="ops-bot",
                    parameters={"to": "ops@example.com", "subject": "s", "body": "b"},
                    data_tags=["internal"],
                    session_id="sess-1",
                    approval_request_id=rows[0].request_id,
                )
            )
            self.assertEqual(allowed.decision.action, "allow")

    def test_cli_can_approve_pending_request_from_persistent_store(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            work = Path(tmp_dir)
            runner = CliRunner()
            init_result = runner.invoke(init_command, ["--path", str(work)])
            self.assertEqual(init_result.exit_code, 0, msg=init_result.output)

            config_path = work / "safeai.yaml"
            policy_path = work / "policies" / "default.yaml"
            policy_doc = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
            policy_doc["policies"].insert(
                0,
                {
                    "name": "email-requires-approval",
                    "boundary": ["action"],
                    "priority": 5,
                    "condition": {"tools": ["send_email"], "data_tags": ["internal"]},
                    "action": "require_approval",
                    "reason": "send email approval gate",
                },
            )
            policy_path.write_text(yaml.safe_dump(policy_doc, sort_keys=False), encoding="utf-8")

            sdk = SafeAI.from_config(config_path)
            first = sdk.intercept_tool_request(
                "send_email",
                {"to": "ops@example.com", "subject": "S", "body": "B"},
                data_tags=["internal"],
                agent_id="default-agent",
                session_id="sess-2",
            )
            self.assertEqual(first.decision.action, "require_approval")
            pending = sdk.list_approval_requests(status="pending", limit=1)
            self.assertEqual(len(pending), 1)
            request_id = pending[0].request_id

            approve_result = runner.invoke(
                cli,
                [
                    "approvals",
                    "approve",
                    request_id,
                    "--config",
                    str(config_path),
                    "--approver",
                    "security-oncall",
                    "--note",
                    "approved via cli",
                ],
            )
            self.assertEqual(approve_result.exit_code, 0, msg=approve_result.output)

            sdk_reloaded = SafeAI.from_config(config_path)
            second = sdk_reloaded.intercept_tool_request(
                "send_email",
                {"to": "ops@example.com", "subject": "S", "body": "B"},
                data_tags=["internal"],
                agent_id="default-agent",
                session_id="sess-2",
                approval_request_id=request_id,
            )
            self.assertEqual(second.decision.action, "allow")


if __name__ == "__main__":
    unittest.main()
