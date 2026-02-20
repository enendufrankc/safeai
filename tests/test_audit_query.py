"""Audit query interface tests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from click.testing import CliRunner

from safeai.cli.logs import logs_command
from safeai.core.audit import AuditEvent, AuditLogger


class AuditQueryTests(unittest.TestCase):
    def test_query_filters_by_boundary_action_and_agent(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            audit_path = Path(temp_dir) / "audit.log"
            logger = AuditLogger(str(audit_path))
            logger.emit(
                AuditEvent(
                    boundary="input",
                    action="allow",
                    policy_name="allow-input",
                    reason="allow",
                    data_tags=[],
                    agent_id="agent-1",
                )
            )
            logger.emit(
                AuditEvent(
                    boundary="output",
                    action="block",
                    policy_name="block-output",
                    reason="blocked",
                    data_tags=["secret"],
                    agent_id="agent-2",
                )
            )

            rows = logger.query(boundary="output", action="block", agent_id="agent-2", limit=10)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["policy_name"], "block-output")

    def test_query_last_duration(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            audit_path = Path(temp_dir) / "audit.log"
            logger = AuditLogger(str(audit_path))
            logger.emit(
                AuditEvent(
                    boundary="input",
                    action="allow",
                    policy_name="allow-input",
                    reason="allow",
                    data_tags=[],
                    agent_id="agent-1",
                )
            )

            rows = logger.query(last="1h")
            self.assertEqual(len(rows), 1)

    def test_logs_cli_query_outputs_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            audit_path = Path(temp_dir) / "audit.log"
            logger = AuditLogger(str(audit_path))
            logger.emit(
                AuditEvent(
                    boundary="output",
                    action="redact",
                    policy_name="redact-output",
                    reason="redacted",
                    data_tags=["personal"],
                    agent_id="agent-1",
                )
            )

            runner = CliRunner()
            result = runner.invoke(
                logs_command,
                ["--file", str(audit_path), "--tail", "5", "--boundary", "output", "--action", "redact"],
            )

            self.assertEqual(result.exit_code, 0, msg=result.output)
            self.assertIn('"boundary":"output"', result.output)
            self.assertIn('"action":"redact"', result.output)


if __name__ == "__main__":
    unittest.main()
