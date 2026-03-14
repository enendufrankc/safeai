# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 SafeAI Contributors
"""Real-time alerting channels and dispatch."""

from safeai.alerting.channels import (
    AlertChannel,
    FileChannel,
    SlackChannel,
    WebhookChannel,
    dispatch_alert,
)
from safeai.alerting.email import EmailAlertChannel
from safeai.alerting.opsgenie import OpsgenieAlertChannel
from safeai.alerting.pagerduty import PagerDutyAlertChannel

__all__ = [
    "AlertChannel",
    "EmailAlertChannel",
    "FileChannel",
    "OpsgenieAlertChannel",
    "PagerDutyAlertChannel",
    "SlackChannel",
    "WebhookChannel",
    "dispatch_alert",
]
