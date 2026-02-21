"""Tests for the safeai alerts CLI commands."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from click.testing import CliRunner

from safeai.cli.alerts import alerts_group


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def config_dir(tmp_path: Path) -> Path:
    """Create a minimal config directory with alert rules."""
    config_path = tmp_path / "safeai.yaml"
    alerts_dir = tmp_path / "alerts"
    alerts_dir.mkdir()
    rules_file = alerts_dir / "default.yaml"
    rules_file.write_text(
        yaml.safe_dump(
            {
                "version": "v1alpha1",
                "alert_rules": [
                    {
                        "rule_id": "high-blocks",
                        "name": "High Block Rate",
                        "threshold": 10,
                        "window": "15m",
                        "filters": {"actions": ["block"]},
                        "channels": ["file"],
                    }
                ],
            }
        )
    )
    config_path.write_text(
        yaml.safe_dump(
            {
                "version": "v1alpha1",
                "paths": {"policy_files": []},
                "dashboard": {
                    "alert_rules_file": "alerts/default.yaml",
                    "alert_log_file": "logs/alerts.log",
                },
            }
        )
    )
    return tmp_path


class TestAlertsListCommand:
    def test_list_rules(self, runner: CliRunner, config_dir: Path) -> None:
        result = runner.invoke(alerts_group, ["list", "--config", str(config_dir / "safeai.yaml")])
        assert result.exit_code == 0
        assert "high-blocks" in result.output
        assert "High Block Rate" in result.output

    def test_list_empty(self, runner: CliRunner, tmp_path: Path) -> None:
        config_path = tmp_path / "safeai.yaml"
        config_path.write_text(yaml.safe_dump({"version": "v1alpha1"}))
        result = runner.invoke(alerts_group, ["list", "--config", str(config_path)])
        assert result.exit_code == 0
        assert "No alert rules" in result.output


class TestAlertsAddCommand:
    def test_add_rule(self, runner: CliRunner, config_dir: Path) -> None:
        result = runner.invoke(
            alerts_group,
            [
                "add",
                "--config",
                str(config_dir / "safeai.yaml"),
                "--rule-id",
                "new-rule",
                "--name",
                "New Rule",
                "--threshold",
                "5",
                "--window",
                "1h",
            ],
        )
        assert result.exit_code == 0
        assert "saved" in result.output


class TestAlertsTestCommand:
    def test_test_no_events(self, runner: CliRunner, config_dir: Path) -> None:
        with patch("safeai.cli.alerts.SafeAI") as mock_cls:
            mock_sdk = mock_cls.from_config.return_value
            mock_sdk.query_audit.return_value = []
            result = runner.invoke(
                alerts_group,
                ["test", "--config", str(config_dir / "safeai.yaml"), "--last", "15m"],
            )
            assert result.exit_code == 0
            assert "No alerts triggered" in result.output
