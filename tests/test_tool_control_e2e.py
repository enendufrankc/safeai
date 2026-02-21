"""End-to-end tool-control flow tests for Phase 2."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import yaml
from click.testing import CliRunner

from safeai import SafeAI
from safeai.cli.init import init_command


class ToolControlE2ETests(unittest.TestCase):
    def _build_sdk(self, work: Path) -> SafeAI:
        init_result = CliRunner().invoke(init_command, ["--path", str(work)])
        self.assertEqual(init_result.exit_code, 0, msg=init_result.output)

        config_path = work / "safeai.yaml"
        config_doc = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        config_doc["audit"]["file_path"] = str((work / "logs" / "audit.log").resolve())
        config_path.write_text(yaml.safe_dump(config_doc, sort_keys=False), encoding="utf-8")
        return SafeAI.from_config(config_path)

    def test_tool_request_response_flow_and_audit_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            work = Path(tmp_dir)
            sdk = self._build_sdk(work)

            request = sdk.intercept_tool_request(
                "send_email",
                {
                    "to": "ops@example.com",
                    "subject": "Subject",
                    "body": "Body",
                    "priority": "high",
                },
                data_tags=["internal"],
                agent_id="default-agent",
                session_id="sess-1",
                source_agent_id="default-agent",
                destination_agent_id="tool:send_email",
                action_type="tool_call",
            )
            self.assertEqual(request.decision.action, "allow")
            self.assertEqual(
                request.filtered_params,
                {"to": "ops@example.com", "subject": "Subject", "body": "Body"},
            )
            self.assertEqual(request.stripped_fields, ["priority"])

            response = sdk.intercept_tool_response(
                "send_email",
                {
                    "status": "sent",
                    "message_id": "msg-1",
                    "recipient": "alice@example.com",
                },
                agent_id="default-agent",
                request_data_tags=["internal"],
                session_id="sess-1",
                source_agent_id="tool:send_email",
                destination_agent_id="default-agent",
                action_type="tool_call",
            )
            self.assertEqual(response.filtered_response, {"status": "sent", "message_id": "msg-1"})
            self.assertEqual(response.stripped_fields, ["recipient"])
            self.assertEqual(response.decision.action, "redact")

            request_events = sdk.query_audit(
                boundary="action",
                phase="request",
                session_id="sess-1",
                limit=10,
            )
            self.assertGreaterEqual(len(request_events), 1)
            event = request_events[0]
            self.assertTrue(event["event_id"].startswith("evt_"))
            self.assertTrue(event["context_hash"].startswith("sha256:"))
            self.assertEqual(event["source_agent_id"], "default-agent")
            self.assertIn("parameter_keys", event["metadata"])
            self.assertIn("decision_source", event["metadata"])

            response_events = sdk.query_audit(
                boundary="action",
                phase="response",
                session_id="sess-1",
                limit=10,
            )
            self.assertGreaterEqual(len(response_events), 1)
            self.assertEqual(response_events[0]["metadata"]["phase"], "response")
            self.assertIn("stripped_fields", response_events[0]["metadata"])

    def test_tool_control_blocks_unknown_agent_and_tool(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            work = Path(tmp_dir)
            sdk = self._build_sdk(work)

            blocked_agent = sdk.intercept_tool_request(
                "send_email",
                {"to": "ops@example.com", "subject": "S", "body": "B"},
                data_tags=["internal"],
                agent_id="ghost-agent",
            )
            self.assertEqual(blocked_agent.decision.action, "block")
            self.assertEqual(blocked_agent.decision.policy_name, "agent-identity")

            blocked_tool = sdk.intercept_tool_request(
                "unknown_tool",
                {"input": "value"},
                data_tags=["internal"],
                agent_id="default-agent",
            )
            self.assertEqual(blocked_tool.decision.action, "block")
            self.assertEqual(blocked_tool.decision.policy_name, "tool-contract")


if __name__ == "__main__":
    unittest.main()
