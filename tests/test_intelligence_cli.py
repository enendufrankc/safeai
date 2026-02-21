"""Tests for the intelligence CLI commands."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from click.testing import CliRunner

from safeai.cli.intelligence import intelligence_group


def _make_config_file(tmpdir: str, *, enabled: bool = True) -> str:
    """Create a minimal safeai.yaml for testing."""
    cfg_path = Path(tmpdir) / "safeai.yaml"
    cfg_path.write_text(
        f"""\
version: v1alpha1
paths:
  policy_files:
    - policies/default.yaml
intelligence:
  enabled: {str(enabled).lower()}
  backend:
    provider: ollama
    model: llama3.2
    base_url: http://localhost:11434
""",
        encoding="utf-8",
    )
    # Create required policy file
    policies_dir = Path(tmpdir) / "policies"
    policies_dir.mkdir(exist_ok=True)
    (policies_dir / "default.yaml").write_text(
        "version: v1alpha1\npolicies:\n  - name: allow-all\n    boundary: [input, output, action]\n    priority: 1000\n    action: allow\n    reason: default\n",
        encoding="utf-8",
    )
    return str(cfg_path)


class IntelligenceGroupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = CliRunner()

    def test_help(self) -> None:
        result = self.runner.invoke(intelligence_group, ["--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("AI advisory commands", result.output)

    def test_auto_config_help(self) -> None:
        result = self.runner.invoke(intelligence_group, ["auto-config", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("--path", result.output)
        self.assertIn("--framework", result.output)
        self.assertIn("--output-dir", result.output)

    def test_recommend_help(self) -> None:
        result = self.runner.invoke(intelligence_group, ["recommend", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("--since", result.output)

    def test_explain_help(self) -> None:
        result = self.runner.invoke(intelligence_group, ["explain", "--help"])
        self.assertEqual(result.exit_code, 0)

    def test_compliance_help(self) -> None:
        result = self.runner.invoke(intelligence_group, ["compliance", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("--framework", result.output)

    def test_integrate_help(self) -> None:
        result = self.runner.invoke(intelligence_group, ["integrate", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("--target", result.output)


class DisabledIntelligenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = CliRunner()
        self.tmpdir = tempfile.mkdtemp()
        self.config_path = _make_config_file(self.tmpdir, enabled=False)

    def test_auto_config_disabled(self) -> None:
        result = self.runner.invoke(
            intelligence_group,
            ["auto-config", "--config", self.config_path],
        )
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("disabled", result.output.lower())

    def test_recommend_disabled(self) -> None:
        result = self.runner.invoke(
            intelligence_group,
            ["recommend", "--config", self.config_path],
        )
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("disabled", result.output.lower())

    def test_explain_disabled(self) -> None:
        result = self.runner.invoke(
            intelligence_group,
            ["explain", "evt_123", "--config", self.config_path],
        )
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("disabled", result.output.lower())

    def test_compliance_disabled(self) -> None:
        result = self.runner.invoke(
            intelligence_group,
            ["compliance", "--framework", "hipaa", "--config", self.config_path],
        )
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("disabled", result.output.lower())

    def test_integrate_disabled(self) -> None:
        result = self.runner.invoke(
            intelligence_group,
            ["integrate", "--target", "langchain", "--config", self.config_path],
        )
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("disabled", result.output.lower())


class EnabledIntelligenceCLITests(unittest.TestCase):
    """Test CLI commands with mocked AI backend."""

    def setUp(self) -> None:
        self.runner = CliRunner()
        self.tmpdir = tempfile.mkdtemp()
        self.config_path = _make_config_file(self.tmpdir, enabled=True)
        # Create a simple project to analyze
        Path(self.tmpdir, "app.py").write_text(
            "def main():\n    pass\n",
            encoding="utf-8",
        )

    @patch("safeai.intelligence.backend.httpx.Client")
    def test_auto_config_runs(self, mock_client_cls: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "model": "llama3.2",
            "message": {
                "role": "assistant",
                "content": "--- FILE: safeai.yaml ---\nversion: v1alpha1\n",
            },
        }
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        output_dir = str(Path(self.tmpdir) / "output")
        result = self.runner.invoke(
            intelligence_group,
            [
                "auto-config",
                "--path", self.tmpdir,
                "--output-dir", output_dir,
                "--config", self.config_path,
            ],
        )
        self.assertEqual(result.exit_code, 0, msg=result.output)
        self.assertIn("auto-config", result.output)

    @patch("safeai.intelligence.backend.httpx.Client")
    def test_compliance_runs(self, mock_client_cls: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "model": "llama3.2",
            "message": {
                "role": "assistant",
                "content": "--- FILE: policies/hipaa-compliance.yaml ---\npolicies: []\n",
            },
        }
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        output_dir = str(Path(self.tmpdir) / "output")
        result = self.runner.invoke(
            intelligence_group,
            [
                "compliance",
                "--framework", "hipaa",
                "--output-dir", output_dir,
                "--config", self.config_path,
            ],
        )
        self.assertEqual(result.exit_code, 0, msg=result.output)
        self.assertIn("compliance", result.output)


if __name__ == "__main__":
    unittest.main()
