# Alerting & Observability

SafeAI provides built-in alerting and observability so you can monitor agent behavior in real time, get notified when security boundaries are triggered, and export metrics for your existing monitoring stack. Alerts can be routed to files, webhooks, Slack, email, PagerDuty, and Opsgenie — all configured in a single YAML file.

## Quick Start

Get file-based alerts running in under two minutes:

```yaml title="alerts/default.yaml"
channels:
  - type: file
    path: logs/alerts.log
```

```python
from safeai import SafeAI

ai = SafeAI.from_config("safeai.yaml")

# Trigger a detectable event
result = ai.scan_input("API_KEY=sk-ABCDEF1234567890")
# Alert written to logs/alerts.log
```

```bash
# Verify the alert was recorded
cat logs/alerts.log
```

!!! tip "Start simple, add channels later"
    File-based alerting requires no external services. Once you're comfortable with the alert format, add Slack, email, or PagerDuty channels to the same configuration file.

## Alert Channels

SafeAI ships with six built-in alert channels. Each channel implements a `send` method and can be used independently or combined in a single configuration.

### File

Writes alert events as structured log lines to a local file.

```yaml title="alerts/default.yaml"
channels:
  - type: file
    path: logs/alerts.log
```

### Webhook

Posts alert payloads as JSON to any HTTP endpoint.

```yaml title="alerts/default.yaml"
channels:
  - type: webhook
    url: https://hooks.slack.com/services/XXX
```

### Slack

Sends formatted messages to a Slack channel using an incoming webhook.

```yaml title="alerts/default.yaml"
channels:
  - type: slack
    webhook_url: https://hooks.slack.com/services/XXX
    channel: "#security-alerts"
```

### Email

Delivers alert notifications via SMTP.

```yaml title="alerts/default.yaml"
channels:
  - type: email
    smtp_host: smtp.example.com
    smtp_port: 587
    from: safeai@example.com
    to: [security@example.com]
```

### PagerDuty

Creates incidents in PagerDuty using the Events API v2.

```yaml title="alerts/default.yaml"
channels:
  - type: pagerduty
    routing_key: YOUR_ROUTING_KEY
    severity: critical
```

### Opsgenie

Creates alerts in Opsgenie with configurable priority levels.

```yaml title="alerts/default.yaml"
channels:
  - type: opsgenie
    api_key: YOUR_API_KEY
    priority: P1
```

!!! warning "Keep credentials out of version control"
    Use environment variable references or a secrets manager for routing keys, API keys, and SMTP passwords. Never commit plain-text credentials to your repository.

### Channel Interface

All alert channels implement the same interface:

```python
from safeai.alerting.email import EmailAlertChannel
from safeai.alerting.pagerduty import PagerDutyAlertChannel
from safeai.alerting.opsgenie import OpsgenieAlertChannel

for cls in [EmailAlertChannel, PagerDutyAlertChannel, OpsgenieAlertChannel]:
    assert hasattr(cls, "send")
```

| Channel    | Module                          | Required Fields                          |
|------------|---------------------------------|------------------------------------------|
| File       | `safeai.alerting.file`          | `path`                                   |
| Webhook    | `safeai.alerting.webhook`       | `url`                                    |
| Slack      | `safeai.alerting.slack`         | `webhook_url`, `channel`                 |
| Email      | `safeai.alerting.email`         | `smtp_host`, `smtp_port`, `from`, `to`   |
| PagerDuty  | `safeai.alerting.pagerduty`     | `routing_key`, `severity`                |
| Opsgenie   | `safeai.alerting.opsgenie`      | `api_key`, `priority`                    |

## CLI Commands

### List Alerts

View recent alerts from the command line:

```bash
# List all alerts
safeai alerts list --config /path/to/safeai.yaml

# Using the module entrypoint
python -m safeai.cli.main alerts list --config /path/to/safeai.yaml
```

### Observe Agents

Monitor agent activity in real time:

```bash
# View agent activity from the last 24 hours
safeai observe agents --config /path/to/safeai.yaml --last 24h

# Using the module entrypoint
python -m safeai.cli.main observe agents --config /path/to/safeai.yaml --last 24h
```

### Observe Sessions

Inspect a specific session's events:

```bash
# View events for a specific session
safeai observe sessions --config /path/to/safeai.yaml --session sess-demo

# Using the module entrypoint
python -m safeai.cli.main observe sessions --config /path/to/safeai.yaml --session sess-demo
```

### Example CLI Output

```
$ safeai alerts list --config safeai.yaml
TIMESTAMP            CHANNEL    SEVERITY   SUMMARY
2026-03-15 09:12:04  slack      critical   Secret detected in input (agent: deploy-bot)
2026-03-15 09:10:22  file       warning    PII redacted in output (agent: support-bot)
2026-03-15 08:55:11  pagerduty  critical   Dangerous command blocked (agent: ops-bot)
```

```
$ safeai observe agents --config safeai.yaml --last 24h
AGENT           EVENTS   BLOCKED   REDACTED   APPROVED
deploy-bot      142      3         0          1
support-bot     89       0         12         0
analytics-bot   54       0         0          0
```

## Prometheus Metrics

SafeAI exposes a Prometheus-compatible metrics endpoint for integration with Grafana, Datadog, or any scrape-based monitoring system.

```bash
# Fetch metrics from the built-in endpoint
curl -s http://127.0.0.1:8910/v1/metrics
```

### Available Metrics

| Metric                              | Type      | Description                                    |
|-------------------------------------|-----------|------------------------------------------------|
| `safeai_alerts_total`               | Counter   | Total alerts fired, labeled by channel         |
| `safeai_scans_total`                | Counter   | Total input/output scans performed             |
| `safeai_blocks_total`               | Counter   | Total blocked events by boundary               |
| `safeai_redactions_total`           | Counter   | Total redacted events by boundary              |
| `safeai_active_sessions`            | Gauge     | Number of currently active sessions            |
| `safeai_policy_evaluations_total`   | Counter   | Total policy evaluations performed             |
| `safeai_scan_duration_seconds`      | Histogram | Scan latency distribution                      |

### Configuration

```yaml title="safeai.yaml"
observability:
  metrics:
    enabled: true
    endpoint: /v1/metrics
    port: 8910
```

!!! info "Scrape interval"
    Configure your Prometheus server to scrape `http://<host>:8910/v1/metrics` at your preferred interval. A 15-second scrape interval works well for most deployments.

## Alert Configuration

The full alert configuration lives in `alerts/default.yaml`. You can combine multiple channels so that a single event triggers notifications across all of them.

```yaml title="alerts/default.yaml"
channels:
  - type: file
    path: logs/alerts.log
  - type: webhook
    url: https://hooks.slack.com/services/XXX
  - type: slack
    webhook_url: https://hooks.slack.com/services/XXX
    channel: "#security-alerts"
  - type: email
    smtp_host: smtp.example.com
    smtp_port: 587
    from: safeai@example.com
    to: [security@example.com]
  - type: pagerduty
    routing_key: YOUR_ROUTING_KEY
    severity: critical
  - type: opsgenie
    api_key: YOUR_API_KEY
    priority: P1
```

### Channel Configuration Reference

| Field          | Channels              | Description                                |
|----------------|-----------------------|--------------------------------------------|
| `type`         | All                   | Channel type identifier                    |
| `path`         | File                  | Output file path for alert logs            |
| `url`          | Webhook               | HTTP endpoint to POST alert payloads       |
| `webhook_url`  | Slack                 | Slack incoming webhook URL                 |
| `channel`      | Slack                 | Target Slack channel                       |
| `smtp_host`    | Email                 | SMTP server hostname                       |
| `smtp_port`    | Email                 | SMTP server port                           |
| `from`         | Email                 | Sender email address                       |
| `to`           | Email                 | List of recipient email addresses          |
| `routing_key`  | PagerDuty             | PagerDuty Events API v2 routing key        |
| `severity`     | PagerDuty             | Incident severity (`critical`, `error`, `warning`, `info`) |
| `api_key`      | Opsgenie              | Opsgenie API key                           |
| `priority`     | Opsgenie              | Alert priority (`P1`–`P5`)                 |

## Custom Alert Rules

Define policies that trigger alerts on specific events using the policy engine:

```yaml title="safeai.yaml"
policies:
  - name: alert-on-secret-detection
    boundary: input
    priority: 300
    condition:
      data_tags: [secret]
    action: block
    alert: true
    reason: "Secret detected — alert dispatched to all channels"

  - name: alert-on-dangerous-command
    boundary: tool_request
    priority: 250
    condition:
      data_tags: [dangerous_command]
    action: block
    alert: true
    reason: "Dangerous command blocked — incident created"

  - name: alert-on-pii-leak
    boundary: output
    priority: 200
    condition:
      data_tags: [personal.pii]
    action: redact
    alert: true
    reason: "PII detected in output — redacted and alert sent"
```

!!! tip "Selective alerting"
    Set `alert: true` only on high-priority policies to avoid notification fatigue. Use file-based logging for lower-severity events and reserve Slack, PagerDuty, and Opsgenie for critical incidents.

## Observability Dashboard

SafeAI's observe commands give you a real-time view of agent behavior and session activity without leaving the terminal.

### Agent Monitoring

Track which agents are active, how many events they generate, and what actions are being taken:

```bash
# Live agent overview
safeai observe agents --config safeai.yaml --last 1h

# Filter to a specific agent
safeai observe agents --config safeai.yaml --agent deploy-bot --last 24h
```

### Session Monitoring

Drill into individual sessions to trace the full sequence of events:

```bash
# Inspect a specific session
safeai observe sessions --config safeai.yaml --session sess-demo
```

```
$ safeai observe sessions --config safeai.yaml --session sess-demo
SESSION: sess-demo  AGENT: support-bot  STARTED: 2026-03-15 08:30:00

EVENT  TIMESTAMP            BOUNDARY     ACTION    POLICY
1      2026-03-15 08:30:12  input        allow     —
2      2026-03-15 08:30:14  output       redact    redact-pii-output
3      2026-03-15 08:30:18  tool_request allow     —
4      2026-03-15 08:30:22  output       block     block-secrets-output
```

### Architecture Overview

```
Agent Activity ──► SafeAI Core ──► Policy Engine ──► Alert Dispatcher
                       │                                    │
                   Audit Log                         ┌──────┼──────┐
                       │                             │      │      │
                   Prometheus              Slack   Email  PagerDuty
                   /v1/metrics
```

1. Agent actions flow through SafeAI's core scanning and policy engine.
2. Policy matches produce audit entries and, when `alert: true`, dispatch alerts.
3. The alert dispatcher fans out to all configured channels simultaneously.
4. Prometheus metrics are updated on every scan, block, and redaction event.

## See Also

- [API Reference — Alerting](../reference/alerting.md)
- [API Reference — Dashboard](../reference/dashboard.md)
- [Audit Logging guide](audit-logging.md) for detailed event history
- [Policy Engine guide](policy-engine.md) for defining alert-triggering rules
- [Intelligence Layer guide](intelligence.md) for AI-powered incident explanation
