"""Phase 6 plugin system tests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from click.testing import CliRunner

from safeai import SafeAI
from safeai.cli.init import init_command

PLUGIN_SOURCE = """
from safeai.middleware.base import BaseMiddleware


SAFEAI_PLUGIN_NAME = "custom-risk-plugin"


class PluginEchoAdapter(BaseMiddleware):
    def middleware(self):
        return {"name": "PluginEchoAdapter"}


def safeai_detectors():
    return [("account_id", "personal.financial.account", r"\\bACC-[0-9]{6}\\b")]


def safeai_adapters():
    return {"plugin_echo": PluginEchoAdapter}


def safeai_policy_templates():
    return {
        "custom-plugin-pack": {
            "version": "v1alpha1",
            "policies": [
                {
                    "name": "custom-plugin-redact-account-id",
                    "boundary": ["output"],
                    "priority": 25,
                    "condition": {"data_tags": ["personal.financial.account"]},
                    "action": "redact",
                    "reason": "Account IDs should be redacted in outbound data.",
                }
            ],
        }
    }
"""


class PluginSystemTests(unittest.TestCase):
    def _build_sdk(self, work: Path) -> SafeAI:
        init_result = CliRunner().invoke(init_command, ["--path", str(work)])
        self.assertEqual(init_result.exit_code, 0, msg=init_result.output)
        plugin_dir = work / "plugins"
        plugin_dir.mkdir(parents=True, exist_ok=True)
        (plugin_dir / "custom_risk_plugin.py").write_text(PLUGIN_SOURCE, encoding="utf-8")
        return SafeAI.from_config(work / "safeai.yaml")

    def test_plugin_detectors_adapters_and_templates_are_loaded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            sdk = self._build_sdk(Path(tmp_dir))

            plugins = sdk.list_plugins()
            names = {row["name"] for row in plugins}
            self.assertIn("custom-risk-plugin", names)

            scan = sdk.scan_input("customer account ACC-123456 reviewed", agent_id="default-agent")
            tags = {item.tag for item in scan.detections}
            self.assertIn("personal.financial.account", tags)

            adapter_names = set(sdk.list_plugin_adapters())
            self.assertIn("plugin_echo", adapter_names)
            adapter = sdk.plugin_adapter("plugin_echo")
            self.assertEqual(adapter.middleware()["name"], "PluginEchoAdapter")

            templates = sdk.list_policy_templates()
            template_names = {row["name"] for row in templates}
            self.assertIn("custom-plugin-pack", template_names)
            payload = sdk.load_policy_template("custom-plugin-pack")
            self.assertIn("policies", payload)
            self.assertEqual(payload["policies"][0]["action"], "redact")


if __name__ == "__main__":
    unittest.main()
