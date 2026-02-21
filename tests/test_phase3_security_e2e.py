"""Phase 3 end-to-end security tests (approvals, secrets, encrypted handles)."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

import yaml
from click.testing import CliRunner

from safeai import SafeAI
from safeai.cli.init import init_command


class Phase3SecurityE2ETests(unittest.TestCase):
    def test_approvals_secrets_and_handles_end_to_end(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            work = Path(tmp_dir)
            init_result = CliRunner().invoke(init_command, ["--path", str(work)])
            self.assertEqual(init_result.exit_code, 0, msg=init_result.output)

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
                    "reason": "sensitive outbound email requires approval",
                },
            )
            policy_path.write_text(yaml.safe_dump(policy_doc, sort_keys=False), encoding="utf-8")

            memory_path = work / "schemas" / "memory.yaml"
            memory_doc = yaml.safe_load(memory_path.read_text(encoding="utf-8"))
            memory_doc["memory"]["fields"].append(
                {
                    "name": "api_token",
                    "type": "string",
                    "tag": "secret",
                    "retention": "1h",
                    "encrypted": True,
                    "required": False,
                }
            )
            memory_path.write_text(yaml.safe_dump(memory_doc, sort_keys=False), encoding="utf-8")

            os.environ["SMTP_TOKEN"] = "smtp-super-secret"
            try:
                sdk = SafeAI.from_config(work / "safeai.yaml")

                capability = sdk.issue_capability_token(
                    agent_id="default-agent",
                    tool_name="send_email",
                    actions=["invoke"],
                    secret_keys=["SMTP_TOKEN"],
                    ttl="10m",
                    session_id="sess-phase3",
                )
                resolved = sdk.resolve_secret(
                    token_id=capability.token_id,
                    secret_key="SMTP_TOKEN",
                    agent_id="default-agent",
                    tool_name="send_email",
                    session_id="sess-phase3",
                )
                self.assertEqual(resolved.value, "smtp-super-secret")

                first = sdk.intercept_tool_request(
                    "send_email",
                    {"to": "ops@example.com", "subject": "S", "body": "B"},
                    data_tags=["internal"],
                    agent_id="default-agent",
                    session_id="sess-phase3",
                )
                self.assertEqual(first.decision.action, "require_approval")
                pending = sdk.list_approval_requests(status="pending", limit=1)
                self.assertEqual(len(pending), 1)
                request_id = pending[0].request_id
                self.assertTrue(sdk.approve_request(request_id, approver_id="security-oncall", note="approved"))

                second = sdk.intercept_tool_request(
                    "send_email",
                    {"to": "ops@example.com", "subject": "S", "body": "B"},
                    data_tags=["internal"],
                    agent_id="default-agent",
                    session_id="sess-phase3",
                    approval_request_id=request_id,
                )
                self.assertEqual(second.decision.action, "allow")

                self.assertTrue(sdk.memory_write("api_token", "smtp-super-secret", agent_id="default-agent"))
                handle = sdk.memory_read("api_token", agent_id="default-agent")
                self.assertTrue(str(handle).startswith("hdl_"))
                self.assertNotEqual(handle, "smtp-super-secret")

                blocked = sdk.resolve_memory_handle(str(handle), agent_id="default-agent", session_id="sess-phase3")
                self.assertIsNone(blocked)

                events = sdk.query_audit(limit=200)
                encoded = json.dumps(events, sort_keys=True)
                self.assertNotIn("smtp-super-secret", encoded)
                self.assertIn("secret_resolve", encoded)
                self.assertIn("handle_resolve", encoded)
            finally:
                os.environ.pop("SMTP_TOKEN", None)


if __name__ == "__main__":
    unittest.main()
