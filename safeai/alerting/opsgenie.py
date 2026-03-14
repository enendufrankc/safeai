# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 SafeAI Contributors
"""Opsgenie alert channel."""

from __future__ import annotations

import json
import logging
import os
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

OPSGENIE_API_URL = "https://api.opsgenie.com/v2/alerts"


class OpsgenieAlertChannel:
    """Send alerts to Opsgenie via the Alerts REST API.

    Configuration:
        api_key – Opsgenie API integration key.  Resolved from the
        constructor parameter first, then ``SAFEAI_OPSGENIE_API_KEY``.
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        self.api_key = api_key or os.environ.get("SAFEAI_OPSGENIE_API_KEY", "")
        self.timeout = timeout

    def _build_payload(self, alert: dict[str, Any]) -> dict[str, Any]:
        rule_name = alert.get("rule_name", "Unknown Rule")
        rule_id = alert.get("rule_id", "?")
        count = alert.get("count", 0)
        window = alert.get("window", "?")
        alert_id = alert.get("alert_id", "?")

        priority = alert.get("severity", "critical")
        priority_map = {"low": "P4", "medium": "P3", "high": "P2", "critical": "P1"}
        og_priority = priority_map.get(priority, "P1")

        return {
            "message": f"SafeAI: {rule_name} ({rule_id}) – {count} events in {window}",
            "alias": f"safeai-{alert_id}",
            "priority": og_priority,
            "source": "safeai",
            "tags": ["safeai", rule_id],
            "details": {
                "rule_name": rule_name,
                "rule_id": rule_id,
                "count": str(count),
                "window": window,
                "alert_id": alert_id,
            },
        }

    def send(self, alert: dict[str, Any]) -> bool:
        """Send an alert to Opsgenie. Returns ``True`` on success."""
        if not self.api_key:
            logger.warning("OpsgenieAlertChannel: no api_key configured – skipping.")
            return False

        try:
            payload = self._build_payload(alert)
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                OPSGENIE_API_URL,
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"GenieKey {self.api_key}",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return 200 <= resp.status < 300
        except Exception:
            logger.exception("OpsgenieAlertChannel: failed to send alert.")
            return False
