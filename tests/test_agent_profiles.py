"""Tests for agent profiles, registry, and installers."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from click.testing import CliRunner

from safeai.agents.profiles import (
    AgentProfile,
    get_profile,
    list_profiles,
    register_profile,
    resolve_tool_category,
)
from safeai.cli.setup import setup_group


class ProfileRegistryTests(unittest.TestCase):
    """Test the profile registry."""

    def test_get_claude_code_profile(self) -> None:
        profile = get_profile("claude-code")
        self.assertIsNotNone(profile)
        self.assertEqual(profile.name, "claude-code")
        self.assertEqual(profile.tool_map["Bash"], "shell")
        self.assertEqual(profile.tool_map["Write"], "file_write")
        self.assertEqual(profile.tool_map["Edit"], "file_edit")
        self.assertEqual(profile.tool_map["Read"], "file_read")
        self.assertEqual(profile.tool_map["Glob"], "search")
        self.assertEqual(profile.tool_map["Grep"], "search")
        self.assertEqual(profile.tool_map["WebFetch"], "web")
        self.assertEqual(profile.tool_map["Task"], "agent_dispatch")

    def test_get_cursor_profile(self) -> None:
        profile = get_profile("cursor")
        self.assertIsNotNone(profile)
        self.assertEqual(profile.name, "cursor")
        self.assertEqual(profile.tool_map["run_command"], "shell")
        self.assertEqual(profile.tool_map["write_file"], "file_write")

    def test_get_generic_profile(self) -> None:
        profile = get_profile("generic")
        self.assertIsNotNone(profile)
        self.assertEqual(profile.tool_map, {})

    def test_get_unknown_profile_returns_none(self) -> None:
        self.assertIsNone(get_profile("nonexistent-agent"))

    def test_list_profiles_returns_all_builtin(self) -> None:
        profiles = list_profiles()
        names = {p.name for p in profiles}
        self.assertIn("claude-code", names)
        self.assertIn("cursor", names)
        self.assertIn("generic", names)

    def test_register_custom_profile(self) -> None:
        custom = AgentProfile(
            name="test-agent",
            description="Test agent",
            tool_map={"execute": "shell"},
        )
        register_profile(custom)
        retrieved = get_profile("test-agent")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.tool_map["execute"], "shell")

    def test_resolve_tool_category_with_profile(self) -> None:
        profile = get_profile("claude-code")
        self.assertEqual(resolve_tool_category("Bash", profile), "shell")
        self.assertEqual(resolve_tool_category("Write", profile), "file_write")

    def test_resolve_tool_category_passthrough(self) -> None:
        profile = get_profile("generic")
        self.assertEqual(resolve_tool_category("custom_tool", profile), "custom_tool")

    def test_resolve_tool_category_no_profile(self) -> None:
        self.assertEqual(resolve_tool_category("anything", None), "anything")


class ClaudeCodeInstallerTests(unittest.TestCase):
    """Test the Claude Code hook installer."""

    def test_installs_hooks_to_settings_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            from safeai.agents.installers.claude_code import install

            install(config_path="safeai.yaml", project_path=tmp_dir)
            settings_file = Path(tmp_dir) / ".claude" / "settings.json"
            self.assertTrue(settings_file.exists())
            settings = json.loads(settings_file.read_text())
            self.assertIn("hooks", settings)
            self.assertIn("PreToolUse", settings["hooks"])
            self.assertIn("PostToolUse", settings["hooks"])
            # Verify hook commands contain safeai hook
            for event_hooks in settings["hooks"].values():
                self.assertTrue(any("safeai hook" in h for h in event_hooks))

    def test_preserves_existing_settings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            settings_dir = Path(tmp_dir) / ".claude"
            settings_dir.mkdir()
            settings_file = settings_dir / "settings.json"
            settings_file.write_text(json.dumps({"existing_key": True}))

            from safeai.agents.installers.claude_code import install

            install(config_path="safeai.yaml", project_path=tmp_dir)
            settings = json.loads(settings_file.read_text())
            self.assertTrue(settings["existing_key"])
            self.assertIn("hooks", settings)

    def test_idempotent_install(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            from safeai.agents.installers.claude_code import install

            install(config_path="safeai.yaml", project_path=tmp_dir)
            install(config_path="safeai.yaml", project_path=tmp_dir)
            settings_file = Path(tmp_dir) / ".claude" / "settings.json"
            settings = json.loads(settings_file.read_text())
            # Should not duplicate hooks
            for event_hooks in settings["hooks"].values():
                self.assertEqual(len(event_hooks), 1)


class CursorInstallerTests(unittest.TestCase):
    """Test the Cursor hook installer."""

    def test_installs_hooks_to_rules_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            from safeai.agents.installers.cursor import install

            install(config_path="safeai.yaml", project_path=tmp_dir)
            rules_file = Path(tmp_dir) / ".cursor" / "rules"
            self.assertTrue(rules_file.exists())
            content = rules_file.read_text()
            self.assertIn("safeai hook", content)
            self.assertIn("pre_tool_use", content)
            self.assertIn("post_tool_use", content)

    def test_idempotent_install(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            from safeai.agents.installers.cursor import install

            install(config_path="safeai.yaml", project_path=tmp_dir)
            install(config_path="safeai.yaml", project_path=tmp_dir)
            rules_file = Path(tmp_dir) / ".cursor" / "rules"
            content = rules_file.read_text()
            self.assertEqual(content.count("safeai hook"), 2)  # pre + post, not duplicated


class GenericInstallerTests(unittest.TestCase):
    """Test the generic installer."""

    def test_prints_instructions(self) -> None:
        runner = CliRunner()
        result = runner.invoke(setup_group, ["generic"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("safeai hook", result.output)
        self.assertIn("safeai mcp", result.output)


class SetupCommandTests(unittest.TestCase):
    """Test the setup CLI group."""

    def test_setup_claude_code(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            runner = CliRunner()
            result = runner.invoke(
                setup_group,
                ["claude-code", "--config", "safeai.yaml", "--path", tmp_dir],
            )
            self.assertEqual(result.exit_code, 0, msg=result.output)
            settings_file = Path(tmp_dir) / ".claude" / "settings.json"
            self.assertTrue(settings_file.exists())

    def test_setup_cursor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            runner = CliRunner()
            result = runner.invoke(
                setup_group,
                ["cursor", "--config", "safeai.yaml", "--path", tmp_dir],
            )
            self.assertEqual(result.exit_code, 0, msg=result.output)
            rules_file = Path(tmp_dir) / ".cursor" / "rules"
            self.assertTrue(rules_file.exists())

    def test_setup_generic(self) -> None:
        runner = CliRunner()
        result = runner.invoke(setup_group, ["generic"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("safeai hook", result.output)


if __name__ == "__main__":
    unittest.main()
