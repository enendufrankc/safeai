"""Tests for the SafeAI MCP server."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from safeai import SafeAI
from safeai.cli.init import init_command
from safeai.mcp.server import _handle_tool, _serializable


class SerializableTests(unittest.TestCase):
    """Test the _serializable helper."""

    def test_dict_passthrough(self) -> None:
        result = _serializable({"key": "value"})
        self.assertEqual(result, {"key": "value"})

    def test_non_dict_non_dataclass(self) -> None:
        result = _serializable("hello")
        self.assertEqual(result, {"value": "hello"})


class HandleToolTests(unittest.TestCase):
    """Test MCP tool dispatch against a real SafeAI instance."""

    def _build_sdk(self, work: Path) -> SafeAI:
        runner = CliRunner()
        result = runner.invoke(init_command, ["--path", str(work)])
        assert result.exit_code == 0, result.output
        return SafeAI.from_config(work / "safeai.yaml")

    def test_scan_input_clean(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            sdk = self._build_sdk(Path(tmp_dir))
            result = _handle_tool(sdk, "scan_input", {"text": "hello world"})
            self.assertIn("decision", result)

    def test_scan_input_blocks_secret(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            sdk = self._build_sdk(Path(tmp_dir))
            result = _handle_tool(
                sdk, "scan_input", {"text": "token=sk-ABCDEF1234567890ABCDEF"}
            )
            self.assertEqual(result["decision"]["action"], "block")

    def test_guard_output_clean(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            sdk = self._build_sdk(Path(tmp_dir))
            result = _handle_tool(sdk, "guard_output", {"text": "safe output"})
            self.assertIn("decision", result)

    def test_scan_structured(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            sdk = self._build_sdk(Path(tmp_dir))
            result = _handle_tool(
                sdk,
                "scan_structured",
                {"payload": {"key": "sk-ABCDEF1234567890ABCDEF"}},
            )
            self.assertEqual(result["decision"]["action"], "block")

    def test_query_audit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            sdk = self._build_sdk(Path(tmp_dir))
            result = _handle_tool(sdk, "query_audit", {"limit": 10})
            self.assertIn("entries", result)

    def test_list_policies(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            sdk = self._build_sdk(Path(tmp_dir))
            result = _handle_tool(sdk, "list_policies", {})
            self.assertIn("templates", result)

    def test_check_tool_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            sdk = self._build_sdk(Path(tmp_dir))
            result = _handle_tool(
                sdk,
                "check_tool",
                {"tool_name": "echo", "parameters": {}, "data_tags": []},
            )
            self.assertIn("decision", result)

    def test_unknown_tool(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            sdk = self._build_sdk(Path(tmp_dir))
            result = _handle_tool(sdk, "nonexistent_tool", {})
            self.assertIn("error", result)


class McpImportTests(unittest.TestCase):
    """Test MCP server creation with mocked mcp package."""

    def test_create_server_without_mcp_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            sdk = self._build_sdk(Path(tmp_dir))
            with patch("safeai.mcp.server.MCP_AVAILABLE", False):
                from safeai.mcp.server import create_mcp_server

                with self.assertRaises(ImportError):
                    create_mcp_server(sdk)

    def _build_sdk(self, work: Path) -> SafeAI:
        runner = CliRunner()
        result = runner.invoke(init_command, ["--path", str(work)])
        assert result.exit_code == 0, result.output
        return SafeAI.from_config(work / "safeai.yaml")


class McpCliTests(unittest.TestCase):
    """Test the MCP CLI command."""

    def test_mcp_command_without_mcp_package(self) -> None:
        from safeai.cli.mcp import mcp_command

        runner = CliRunner()
        result = runner.invoke(mcp_command, ["--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("MCP server", result.output)


if __name__ == "__main__":
    unittest.main()
