# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 SafeAI Contributors
"""Email alert channel via SMTP."""

from __future__ import annotations

import logging
import os
import smtplib
from email.message import EmailMessage
from typing import Any

logger = logging.getLogger(__name__)


class EmailAlertChannel:
    """Send alerts as emails via SMTP.

    Configuration is read from constructor parameters first, falling back
    to environment variables when a parameter is not supplied.

    Environment variables:
        SAFEAI_SMTP_HOST      – SMTP server hostname (default: ``localhost``)
        SAFEAI_SMTP_PORT      – SMTP server port (default: ``587``)
        SAFEAI_SMTP_SENDER    – envelope-from / ``From`` header
        SAFEAI_SMTP_RECIPIENTS – comma-separated list of recipient addresses
        SAFEAI_SMTP_USER      – SMTP username for authentication (optional)
        SAFEAI_SMTP_PASSWORD  – SMTP password for authentication (optional)
        SAFEAI_SMTP_USE_TLS   – set to ``"true"`` to enable STARTTLS (default: ``true``)
    """

    def __init__(
        self,
        *,
        smtp_host: str | None = None,
        smtp_port: int | None = None,
        sender: str | None = None,
        recipients: list[str] | None = None,
        smtp_user: str | None = None,
        smtp_password: str | None = None,
        use_tls: bool | None = None,
        timeout: float = 10.0,
    ) -> None:
        self.smtp_host = smtp_host or os.environ.get("SAFEAI_SMTP_HOST", "localhost")
        self.smtp_port = smtp_port or int(os.environ.get("SAFEAI_SMTP_PORT", "587"))
        self.sender = sender or os.environ.get("SAFEAI_SMTP_SENDER", "")
        self.smtp_user = smtp_user or os.environ.get("SAFEAI_SMTP_USER")
        self.smtp_password = smtp_password or os.environ.get("SAFEAI_SMTP_PASSWORD")
        self.timeout = timeout

        if recipients is not None:
            self.recipients = list(recipients)
        else:
            raw = os.environ.get("SAFEAI_SMTP_RECIPIENTS", "")
            self.recipients = [r.strip() for r in raw.split(",") if r.strip()]

        if use_tls is not None:
            self.use_tls = use_tls
        else:
            self.use_tls = os.environ.get("SAFEAI_SMTP_USE_TLS", "true").lower() == "true"

    def _build_message(self, alert: dict[str, Any]) -> EmailMessage:
        rule_name = alert.get("rule_name", "Unknown Rule")
        rule_id = alert.get("rule_id", "?")
        count = alert.get("count", 0)
        window = alert.get("window", "?")
        alert_id = alert.get("alert_id", "?")

        msg = EmailMessage()
        msg["Subject"] = f"[SafeAI Alert] {rule_name} ({rule_id})"
        msg["From"] = self.sender
        msg["To"] = ", ".join(self.recipients)
        msg.set_content(
            f"SafeAI Alert\n"
            f"============\n"
            f"Rule:     {rule_name} ({rule_id})\n"
            f"Events:   {count} in {window}\n"
            f"Alert ID: {alert_id}\n"
        )
        return msg

    def send(self, alert: dict[str, Any]) -> bool:
        """Send an alert email. Returns ``True`` on success."""
        if not self.recipients:
            logger.warning("EmailAlertChannel: no recipients configured – skipping.")
            return False

        try:
            msg = self._build_message(alert)
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=self.timeout) as server:
                if self.use_tls:
                    server.starttls()
                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            return True
        except Exception:
            logger.exception("EmailAlertChannel: failed to send alert.")
            return False
