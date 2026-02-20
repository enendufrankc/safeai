"""End-to-end integration tests for core boundary flows."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import yaml
from click.testing import CliRunner

from safeai import SafeAI
from safeai.cli.init import init_command


class EndToEndFlowTests(unittest.TestCase):
    def test_full_flow_scan_guard_memory_audit_and_reload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            work = Path(tmp_dir)
            runner = CliRunner()
            init_result = runner.invoke(init_command, ["--path", str(work)])
            self.assertEqual(init_result.exit_code, 0, msg=init_result.output)

            sdk = SafeAI.from_config(work / "safeai.yaml")

            scan = sdk.scan_input("token=sk-ABCDEF1234567890ABCDEF")
            self.assertEqual(scan.decision.action, "block")
            self.assertEqual(scan.filtered, "")

            output = sdk.guard_output("Contact alice@example.com")
            self.assertEqual(output.decision.action, "redact")
            self.assertIn("[REDACTED]", output.safe_output)

            self.assertTrue(sdk.memory_write("user_preference", "en-US", agent_id="agent-1"))
            self.assertEqual(sdk.memory_read("user_preference", agent_id="agent-1"), "en-US")

            events = sdk.query_audit(limit=10)
            self.assertGreaterEqual(len(events), 2)

            policy_path = work / "policies" / "default.yaml"
            policy_doc = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
            policy_doc["policies"][1]["action"] = "allow"
            policy_path.write_text(yaml.safe_dump(policy_doc, sort_keys=False), encoding="utf-8")

            self.assertTrue(sdk.reload_policies())
            output_after_reload = sdk.guard_output("Contact bob@example.com")
            self.assertEqual(output_after_reload.decision.action, "allow")
            self.assertIn("bob@example.com", output_after_reload.safe_output)


if __name__ == "__main__":
    unittest.main()
