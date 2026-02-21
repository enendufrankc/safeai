"""Tests for the safeai observe CLI commands."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from click.testing import CliRunner

from safeai.cli.observe import observe_group


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


class TestObserveAgentsCommand:
    def test_agents_with_events(self, runner: CliRunner) -> None:
        events = [
            {"agent_id": "agent-1", "timestamp": "2024-01-01T00:01:00+00:00", "boundary": "input", "action": "block"},
            {"agent_id": "agent-1", "timestamp": "2024-01-01T00:02:00+00:00", "boundary": "output", "action": "allow"},
            {"agent_id": "agent-2", "timestamp": "2024-01-01T00:03:00+00:00", "boundary": "input", "action": "allow"},
        ]
        with patch("safeai.cli.observe.SafeAI") as mock_cls:
            mock_sdk = mock_cls.from_config.return_value
            mock_sdk.query_audit.return_value = events
            result = runner.invoke(observe_group, ["agents", "--config", "safeai.yaml", "--last", "24h"])
            assert result.exit_code == 0
            assert "agent-1" in result.output
            assert "agent-2" in result.output

    def test_agents_no_activity(self, runner: CliRunner) -> None:
        with patch("safeai.cli.observe.SafeAI") as mock_cls:
            mock_sdk = mock_cls.from_config.return_value
            mock_sdk.query_audit.return_value = []
            result = runner.invoke(observe_group, ["agents", "--config", "safeai.yaml"])
            assert result.exit_code == 0
            assert "No agent activity" in result.output


class TestObserveSessionsCommand:
    def test_sessions_with_events(self, runner: CliRunner) -> None:
        events = [
            {
                "event_id": "evt_1",
                "boundary": "input",
                "action": "allow",
                "agent_id": "agent-1",
                "session_id": "sess-abc",
                "reason": "ok",
                "timestamp": "2024-01-01T00:01:00+00:00",
            },
        ]
        with patch("safeai.cli.observe.SafeAI") as mock_cls:
            mock_sdk = mock_cls.from_config.return_value
            mock_sdk.query_audit.return_value = events
            result = runner.invoke(
                observe_group, ["sessions", "--config", "safeai.yaml", "--session", "sess-abc"]
            )
            assert result.exit_code == 0
            assert "sess-abc" in result.output
            assert "1 events" in result.output

    def test_sessions_no_events(self, runner: CliRunner) -> None:
        with patch("safeai.cli.observe.SafeAI") as mock_cls:
            mock_sdk = mock_cls.from_config.return_value
            mock_sdk.query_audit.return_value = []
            result = runner.invoke(
                observe_group, ["sessions", "--config", "safeai.yaml", "--session", "sess-xyz"]
            )
            assert result.exit_code == 0
            assert "No events found" in result.output
