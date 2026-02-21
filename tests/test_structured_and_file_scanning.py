"""Phase 6 structured payload and file scanning tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import yaml
from click.testing import CliRunner

from safeai import SafeAI
from safeai.cli.init import init_command


class StructuredAndFileScanningTests(unittest.TestCase):
    def _build_sdk(self, work: Path, *, redact_input_personal: bool = False) -> SafeAI:
        init_result = CliRunner().invoke(init_command, ["--path", str(work)])
        self.assertEqual(init_result.exit_code, 0, msg=init_result.output)
        if redact_input_personal:
            policy_path = work / "policies" / "default.yaml"
            policy_doc = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
            policies = list(policy_doc.get("policies", []))
            policies.insert(
                1,
                {
                    "name": "redact-personal-data-in-input",
                    "boundary": ["input"],
                    "priority": 15,
                    "condition": {"data_tags": ["personal", "personal.pii"]},
                    "action": "redact",
                    "reason": "Personal data should be redacted in structured input.",
                },
            )
            policy_doc["policies"] = policies
            policy_path.write_text(yaml.safe_dump(policy_doc, sort_keys=False), encoding="utf-8")
        return SafeAI.from_config(work / "safeai.yaml")

    def test_structured_scan_blocks_secret_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            sdk = self._build_sdk(Path(tmp_dir))
            payload = {
                "request": {
                    "token": "sk-ABCDEF1234567890ABCDEF",
                    "summary": "run this deployment",
                }
            }
            result = sdk.scan_structured_input(payload, agent_id="default-agent")
            self.assertEqual(result.decision.action, "block")
            self.assertIsNone(result.filtered)
            self.assertGreaterEqual(len(result.detections), 1)
            paths = {item.path for item in result.detections}
            self.assertIn("$.request.token", paths)

    def test_structured_and_file_scan_can_redact_personal_data(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            work = Path(tmp_dir)
            sdk = self._build_sdk(work, redact_input_personal=True)

            structured = sdk.scan_structured_input(
                {"contact": {"email": "alice@example.com", "message": "hello"}},
                agent_id="default-agent",
            )
            self.assertEqual(structured.decision.action, "redact")
            self.assertIn("[REDACTED]", structured.filtered["contact"]["email"])

            json_path = work / "sample.json"
            json_path.write_text(
                json.dumps({"secret": "sk-ABCDEF1234567890ABCDEF", "message": "ship it"}, ensure_ascii=True),
                encoding="utf-8",
            )
            json_result = sdk.scan_file_input(json_path, agent_id="default-agent")
            self.assertEqual(json_result["mode"], "structured")
            self.assertEqual(json_result["decision"]["action"], "block")

            text_path = work / "sample.txt"
            text_path.write_text("Please email alice@example.com for review", encoding="utf-8")
            text_result = sdk.scan_file_input(text_path, agent_id="default-agent")
            self.assertEqual(text_result["mode"], "text")
            self.assertEqual(text_result["decision"]["action"], "redact")
            self.assertIn("[REDACTED]", text_result["filtered"])


if __name__ == "__main__":
    unittest.main()
