"""Phase 6 policy template pack tests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from click.testing import CliRunner

from safeai import SafeAI
from safeai.cli.init import init_command
from safeai.cli.main import cli


class PolicyTemplateTests(unittest.TestCase):
    def _build_sdk(self, work: Path) -> SafeAI:
        init_result = CliRunner().invoke(init_command, ["--path", str(work)])
        self.assertEqual(init_result.exit_code, 0, msg=init_result.output)
        return SafeAI.from_config(work / "safeai.yaml")

    def test_builtin_template_packs_are_available(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            sdk = self._build_sdk(Path(tmp_dir))
            templates = sdk.list_policy_templates()
            names = {row["name"] for row in templates}
            self.assertIn("finance", names)
            self.assertIn("healthcare", names)
            self.assertIn("support", names)
            finance = sdk.load_policy_template("finance")
            self.assertIn("policies", finance)
            self.assertGreaterEqual(len(finance["policies"]), 1)

    def test_templates_cli_list_and_show(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            work = Path(tmp_dir)
            init_result = CliRunner().invoke(init_command, ["--path", str(work)])
            self.assertEqual(init_result.exit_code, 0, msg=init_result.output)
            runner = CliRunner()

            listed = runner.invoke(cli, ["templates", "list", "--config", str(work / "safeai.yaml")])
            self.assertEqual(listed.exit_code, 0, msg=listed.output)
            self.assertIn("finance", listed.output)

            shown = runner.invoke(
                cli,
                ["templates", "show", "--config", str(work / "safeai.yaml"), "--name", "healthcare"],
            )
            self.assertEqual(shown.exit_code, 0, msg=shown.output)
            self.assertIn("healthcare-redact-phi-in-output", shown.output)


if __name__ == "__main__":
    unittest.main()
