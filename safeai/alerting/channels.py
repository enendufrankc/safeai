"""Alert channel implementations for real-time notification delivery."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

import httpx


@runtime_checkable
class AlertChannel(Protocol):
    """Protocol for alert delivery channels."""

    def send(self, alert: dict[str, Any]) -> bool:
        """Send an alert. Returns True on success, False on failure."""
        ...


class FileChannel:
    """Append alerts as JSON lines to a file."""

    def __init__(self, file_path: str | Path) -> None:
        self.file_path = Path(file_path).expanduser()

    def send(self, alert: dict[str, Any]) -> bool:
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            with self.file_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(alert, separators=(",", ":"), ensure_ascii=True) + "\n")
            return True
        except Exception:
            return False


class WebhookChannel:
    """POST alerts as JSON to an HTTP endpoint."""

    def __init__(self, url: str, *, timeout: float = 5.0) -> None:
        self.url = url
        self.timeout = timeout

    def send(self, alert: dict[str, Any]) -> bool:
        try:
            response = httpx.post(
                self.url,
                json=alert,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"},
            )
            return 200 <= response.status_code < 300
        except Exception:
            return False


class SlackChannel:
    """POST alerts to a Slack incoming webhook."""

    def __init__(self, webhook_url: str, *, timeout: float = 5.0) -> None:
        self.webhook_url = webhook_url
        self.timeout = timeout

    def send(self, alert: dict[str, Any]) -> bool:
        rule_name = alert.get("rule_name", "Unknown Rule")
        count = alert.get("count", 0)
        window = alert.get("window", "?")
        rule_id = alert.get("rule_id", "?")
        text = (
            f":rotating_light: *SafeAI Alert*\n"
            f"*Rule:* {rule_name} (`{rule_id}`)\n"
            f"*Events:* {count} in {window}\n"
            f"*Alert ID:* {alert.get('alert_id', '?')}"
        )
        try:
            response = httpx.post(
                self.webhook_url,
                json={"text": text},
                timeout=self.timeout,
                headers={"Content-Type": "application/json"},
            )
            return 200 <= response.status_code < 300
        except Exception:
            return False


def dispatch_alert(
    alert: dict[str, Any],
    channels: list[AlertChannel],
) -> dict[str, bool]:
    """Dispatch an alert to multiple channels. Returns per-channel success map."""
    results: dict[str, bool] = {}
    for channel in channels:
        name = type(channel).__name__
        try:
            results[name] = channel.send(alert)
        except Exception:
            results[name] = False
    return results
