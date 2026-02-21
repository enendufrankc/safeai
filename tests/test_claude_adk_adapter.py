"""Claude ADK adapter integration tests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from click.testing import CliRunner

from safeai import SafeAI
from safeai.cli.init import init_command
from safeai.middleware.langchain import SafeAIBlockedError


class ClaudeADKAdapterTests(unittest.TestCase):
    def _build_sdk(self, work: Path) -> SafeAI:
        init_result = CliRunner().invoke(init_command, ["--path", str(work)])
        self.assertEqual(init_result.exit_code, 0, msg=init_result.output)
        return SafeAI.from_config(work / "safeai.yaml")

    def test_wrap_tool_enforces_request_and_response_controls(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            sdk = self._build_sdk(Path(tmp_dir))
            adapter = sdk.claude_adk_adapter()
            seen: dict[str, object] = {}

            def tool_fn(**kwargs):
                seen.update(kwargs)
                return {"status": "sent", "message_id": "msg-1", "recipient": "alice@example.com"}

            wrapped = adapter.wrap_tool(
                "send_email",
                tool_fn,
                agent_id="default-agent",
                request_data_tags=["internal"],
            )
            result = wrapped(to="ops@example.com", subject="Subject", body="Body", priority="high")
            self.assertEqual(seen, {"to": "ops@example.com", "subject": "Subject", "body": "Body"})
            self.assertEqual(result, {"status": "sent", "message_id": "msg-1"})

    def test_wrap_tool_raises_for_unbound_agent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            sdk = self._build_sdk(Path(tmp_dir))
            adapter = sdk.claude_adk_adapter()

            def tool_fn(**kwargs):
                return {"status": "sent", "message_id": "msg-1"}

            wrapped = adapter.wrap_tool(
                "send_email",
                tool_fn,
                agent_id="unknown-agent",
                request_data_tags=["internal"],
            )
            with self.assertRaises(SafeAIBlockedError):
                wrapped(to="ops@example.com", subject="S", body="B")


if __name__ == "__main__":
    unittest.main()
