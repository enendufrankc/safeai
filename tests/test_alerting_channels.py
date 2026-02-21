"""Tests for alerting channels and dispatch."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from safeai.alerting.channels import (
    AlertChannel,
    FileChannel,
    SlackChannel,
    WebhookChannel,
    dispatch_alert,
)


def _sample_alert() -> dict:
    return {
        "alert_id": "alr_test_001",
        "rule_id": "rule-1",
        "rule_name": "High Block Rate",
        "threshold": 5,
        "window": "15m",
        "count": 7,
        "channels": ["file"],
        "timestamp": "2024-01-01T00:00:00+00:00",
    }


class TestFileChannel:
    def test_writes_json_line(self, tmp_path: Path) -> None:
        file_path = tmp_path / "alerts.log"
        channel = FileChannel(file_path)
        alert = _sample_alert()
        result = channel.send(alert)
        assert result is True
        assert file_path.exists()
        lines = file_path.read_text().strip().splitlines()
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed["alert_id"] == "alr_test_001"

    def test_appends_multiple_alerts(self, tmp_path: Path) -> None:
        file_path = tmp_path / "alerts.log"
        channel = FileChannel(file_path)
        channel.send(_sample_alert())
        channel.send({**_sample_alert(), "alert_id": "alr_test_002"})
        lines = file_path.read_text().strip().splitlines()
        assert len(lines) == 2

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        file_path = tmp_path / "nested" / "dir" / "alerts.log"
        channel = FileChannel(file_path)
        assert channel.send(_sample_alert()) is True
        assert file_path.exists()

    def test_implements_protocol(self) -> None:
        assert isinstance(FileChannel("/tmp/test.log"), AlertChannel)


class TestWebhookChannel:
    @patch("safeai.alerting.channels.httpx.post")
    def test_sends_post_request(self, mock_post: MagicMock) -> None:
        mock_post.return_value = MagicMock(status_code=200)
        channel = WebhookChannel("https://example.com/webhook")
        result = channel.send(_sample_alert())
        assert result is True
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        assert call_kwargs.kwargs["json"]["alert_id"] == "alr_test_001"

    @patch("safeai.alerting.channels.httpx.post")
    def test_returns_false_on_server_error(self, mock_post: MagicMock) -> None:
        mock_post.return_value = MagicMock(status_code=500)
        channel = WebhookChannel("https://example.com/webhook")
        result = channel.send(_sample_alert())
        assert result is False

    @patch("safeai.alerting.channels.httpx.post")
    def test_returns_false_on_exception(self, mock_post: MagicMock) -> None:
        mock_post.side_effect = Exception("connection refused")
        channel = WebhookChannel("https://example.com/webhook")
        result = channel.send(_sample_alert())
        assert result is False

    def test_implements_protocol(self) -> None:
        assert isinstance(WebhookChannel("https://example.com"), AlertChannel)


class TestSlackChannel:
    @patch("safeai.alerting.channels.httpx.post")
    def test_sends_slack_message(self, mock_post: MagicMock) -> None:
        mock_post.return_value = MagicMock(status_code=200)
        channel = SlackChannel("https://hooks.slack.com/services/T/B/X")
        result = channel.send(_sample_alert())
        assert result is True
        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs["json"]
        assert "text" in payload
        assert "High Block Rate" in payload["text"]

    @patch("safeai.alerting.channels.httpx.post")
    def test_returns_false_on_failure(self, mock_post: MagicMock) -> None:
        mock_post.return_value = MagicMock(status_code=403)
        channel = SlackChannel("https://hooks.slack.com/services/T/B/X")
        result = channel.send(_sample_alert())
        assert result is False

    def test_implements_protocol(self) -> None:
        assert isinstance(SlackChannel("https://hooks.slack.com"), AlertChannel)


class TestDispatchAlert:
    def test_dispatches_to_multiple_channels(self, tmp_path: Path) -> None:
        file_channel = FileChannel(tmp_path / "alerts.log")
        mock_channel = MagicMock()
        mock_channel.send.return_value = True
        type(mock_channel).__name__ = "MockChannel"
        results = dispatch_alert(_sample_alert(), [file_channel, mock_channel])
        assert results["FileChannel"] is True
        assert results["MockChannel"] is True

    def test_handles_mixed_results(self, tmp_path: Path) -> None:
        file_channel = FileChannel(tmp_path / "alerts.log")
        failing_channel = MagicMock()
        failing_channel.send.return_value = False
        type(failing_channel).__name__ = "FailChannel"
        results = dispatch_alert(_sample_alert(), [file_channel, failing_channel])
        assert results["FileChannel"] is True
        assert results["FailChannel"] is False

    def test_handles_exception_in_channel(self) -> None:
        error_channel = MagicMock()
        error_channel.send.side_effect = RuntimeError("boom")
        type(error_channel).__name__ = "ErrorChannel"
        results = dispatch_alert(_sample_alert(), [error_channel])
        assert results["ErrorChannel"] is False
