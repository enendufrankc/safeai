# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 SafeAI Contributors
"""PagerDuty alert channel via Events API v2."""

from __future__ import annotations

import json
import logging
import os
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

PAGERDUTY_EVENTS_URL = "https://events.pagerduty.com/v2/enqueue"


class PagerDutyAlertChannel:
    """Send alerts to PagerDuty using the Events API v2 ``trigger`` action.

    Configuration:
        routing_key – PagerDuty integration/routing key.  Resolved from the
        constructor parameter first, then ``SAFEAI_PAGERDUTY_ROUTING_KEY``.
    """

    def __init__(
        self,
        *,
        routing_key: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        self.routing_key = routing_key or os.environ.get("SAFEAI_PAGERDUTY_ROUTING_KEY", "")
        self.timeout = timeout

    def _build_payload(self, alert: dict[str, Any]) -> dict[str, Any]:
        rule_name = alert.get("rule_name", "Unknown Rule")
        rule_id = alert.get("rule_id", "?")
        count = alert.get("count", 0)
        window = alert.get("window", "?")
        alert_id = alert.get("alert_id", "?")

        severity = alert.get("severity", "critical")
        severity_map = {"low": "info", "medium": "warning", "high": "error", "critical": "critical"}
        pd_severity = severity_map.get(severity, "critical")

        return {
            "routing_key": self.routing_key,
            "event_action": "trigger",
            "dedup_key": f"safeai-{alert_id}",
            "payload": {
                "summary": f"SafeAI: {rule_name} ({rule_id}) – {count} events in {window}",
                "source": "safeai",
                "severity": pd_severity,
                "component": rule_id,
                "custom_details": alert,
            },
        }

    def send(self, alert: dict[str, Any]) -> bool:
        """Send a trigger event to PagerDuty. Returns ``True`` on success."""
        if not self.routing_key:
            logger.warning("PagerDutyAlertChannel: no routing_key configured – skipping.")
            return False

        try:
            payload = self._build_payload(alert)
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                PAGERDUTY_EVENTS_URL,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return 200 <= resp.status < 300
        except Exception:
            logger.exception("PagerDutyAlertChannel: failed to send alert.")
            return False
