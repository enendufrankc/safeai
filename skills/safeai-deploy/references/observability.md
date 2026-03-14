# SafeAI Observability Reference

## Table of Contents
1. [Starting the Server](#starting-the-server)
2. [All Endpoints](#all-endpoints)
3. [Prometheus Metrics](#prometheus-metrics)
4. [Audit Query API](#audit-query-api)
5. [Dashboard RBAC](#dashboard-rbac)
6. [Alert Rules](#alert-rules)
7. [CLI Observability Commands](#cli-observability-commands)
8. [safeai.yaml Config](#safaiyaml-config)

---

## Starting the Server

```bash
# Start (foreground)
safeai serve --host 127.0.0.1 --port 8910 --config safeai.yaml

# Start (background, log to file)
safeai serve --config safeai.yaml > logs/safeai-serve.log 2>&1 &

# Generated convenience script (created by deploy_safeai.py --observability)
./start-safeai-obs.sh
```

Default: `sidecar` mode on `127.0.0.1:8910`.

---

## All Endpoints

### Core

| Method | Path | Description |
|--------|------|-------------|
| GET | `/v1/health` | Health check + per-agent counters |
| GET | `/v1/metrics` | Prometheus text format |
| GET | `/v1/plugins` | List loaded plugins |
| GET | `/v1/policies/templates` | List policy templates |
| POST | `/v1/policies/reload` | Hot-reload policies from disk |

### Security Boundaries

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/scan/input` | Scan input text |
| POST | `/v1/scan/structured` | Scan JSON payload |
| POST | `/v1/scan/file` | Scan a file path |
| POST | `/v1/guard/output` | Guard output text |
| POST | `/v1/intercept/tool` | Intercept tool call |
| POST | `/v1/intercept/agent-message` | Intercept agent-to-agent message |

### Audit

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/audit/query` | Query audit events with filters |

### Dashboard

| Method | Path | Permission |
|--------|------|------------|
| GET | `/dashboard` | HTML UI |
| GET | `/v1/dashboard/overview` | KPI stats | dashboard:view |
| POST | `/v1/dashboard/events/query` | Query events | audit:read |
| GET | `/v1/dashboard/incidents` | Policy violations | incident:read |
| GET | `/v1/dashboard/approvals` | Pending approvals | approval:read |
| POST | `/v1/dashboard/approvals/{id}/approve` | Approve request | approval:decide |
| POST | `/v1/dashboard/approvals/{id}/deny` | Deny request | approval:decide |
| POST | `/v1/dashboard/compliance/report` | Compliance report | compliance:report |
| GET | `/v1/dashboard/observe/agents` | Agent activity | audit:read |
| GET | `/v1/dashboard/observe/agents/{agent_id}` | Agent detail | audit:read |
| GET | `/v1/dashboard/observe/sessions/{session_id}` | Session trace | audit:read |
| GET | `/v1/dashboard/observe/metrics` | Metrics summary | audit:read |
| GET | `/v1/dashboard/alerts/rules` | List alert rules | alert:read |
| POST | `/v1/dashboard/alerts/rules` | Create/update alert rule | alert:manage |
| GET | `/v1/dashboard/alerts/history` | Recent alerts | alert:read |
| POST | `/v1/dashboard/alerts/evaluate` | Trigger alert evaluation | alert:read |
| GET | `/v1/dashboard/tenants` | List tenant policy sets | tenant:read |
| PUT | `/v1/dashboard/tenants/{id}/policies` | Update tenant policies | tenant:manage |

### Intelligence

| Method | Path | Description |
|--------|------|-------------|
| GET | `/v1/intelligence/status` | Backend health |
| POST | `/v1/intelligence/explain` | AI explanation for an event |
| POST | `/v1/intelligence/recommend` | Policy recommendations |
| POST | `/v1/intelligence/compliance` | Compliance report |

---

## Prometheus Metrics

Available at `GET /v1/metrics` in Prometheus text exposition format.

### Metric Names

```
# Total requests through the proxy
safeai_proxy_requests_total{endpoint, status, protocol}

# Enforcement decisions
safeai_proxy_decisions_total{endpoint, action}
# action values: allow | block | redact | require_approval

# Request latency histogram
safeai_proxy_request_latency_seconds{endpoint}
# Buckets: 0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, +Inf
```

### Example output

```
safeai_proxy_requests_total{endpoint="/v1/scan/input",status="200",protocol="http"} 142
safeai_proxy_decisions_total{endpoint="/v1/scan/input",action="block"} 7
safeai_proxy_decisions_total{endpoint="/v1/scan/input",action="allow"} 135
safeai_proxy_request_latency_seconds_bucket{endpoint="/v1/scan/input",le="0.01"} 98
safeai_proxy_request_latency_seconds_sum{endpoint="/v1/scan/input"} 0.834
safeai_proxy_request_latency_seconds_count{endpoint="/v1/scan/input"} 142
```

### Prometheus scrape config

```yaml
scrape_configs:
  - job_name: safeai
    static_configs:
      - targets: ['127.0.0.1:8910']
    metrics_path: /v1/metrics
```

---

## Audit Query API

`POST /v1/audit/query` — returns matching audit events as JSON.

### Request filters

```json
{
  "boundary": "input",
  "action": "block",
  "policy_name": "block-secrets-input",
  "agent_id": "claude-code",
  "tool_name": "Bash",
  "data_tag": "secret.api_key",
  "session_id": "sess_abc123",
  "event_id": "evt_xyz",
  "source_agent_id": null,
  "destination_agent_id": null,
  "metadata_key": null,
  "metadata_value": null,
  "since": "2026-03-14T00:00:00Z",
  "until": null,
  "last": "1h",
  "limit": 100,
  "newest_first": true
}
```

All fields are optional. `last` accepts durations: `15m`, `2h`, `7d`.

### Response

```json
{
  "events": [
    {
      "event_id": "evt_...",
      "timestamp": "2026-03-14T10:23:45Z",
      "boundary": "input",
      "action": "block",
      "policy_name": "block-secrets-input",
      "reason": "Secrets must not enter the AI boundary",
      "data_tags": ["secret.api_key"],
      "agent_id": "claude-code",
      "tool_name": null,
      "session_id": "sess_abc123",
      "context_hash": "sha256:..."
    }
  ],
  "count": 1
}
```

### CLI equivalent

```bash
safeai logs --action block --last 1h --agent claude-code
safeai logs --data-tag secret.api_key --last 24h --json-output
safeai logs --detail evt_abc123
```

---

## Dashboard RBAC

Authentication is header-based (no cookies/sessions).

| Header | Value |
|--------|-------|
| `x-safeai-user` | User ID (must match a user in `safeai.yaml`) |
| `x-safeai-tenant` | Tenant ID (optional, scopes event visibility) |

### Role permissions

| Role | Permissions |
|------|-------------|
| `viewer` | dashboard:view, audit:read, incident:read, approval:read, compliance:report, tenant:read, alert:read |
| `approver` | viewer + approval:decide |
| `auditor` | same as viewer |
| `admin` | all permissions |

### Configuring users in safeai.yaml

```yaml
dashboard:
  enabled: true
  rbac_enabled: true
  users:
    - user_id: frank
      role: admin
      tenants: ["*"]
    - user_id: security-reviewer
      role: approver
      tenants: ["default"]
```

### Disable RBAC (development)

```yaml
dashboard:
  enabled: true
  rbac_enabled: false
```

---

## Alert Rules

Alert rules evaluate a sliding window of audit events and fire when a threshold is crossed.

### Create a rule via API

```bash
curl -X POST http://localhost:8910/v1/dashboard/alerts/rules \
  -H "x-safeai-user: admin" \
  -H "Content-Type: application/json" \
  -d '{
    "rule_id": "high-block-rate",
    "name": "High block rate",
    "threshold": 10,
    "window": "15m",
    "filters": {
      "actions": ["block"],
      "boundaries": ["input"]
    },
    "channels": ["file", "slack"]
  }'
```

### Alert rule fields

| Field | Description |
|-------|-------------|
| `rule_id` | Unique identifier |
| `name` | Human-readable name |
| `threshold` | Event count to trigger on |
| `window` | Sliding window: `15m`, `1h`, `24h` |
| `filters.boundaries` | Limit to specific boundaries |
| `filters.actions` | Limit to specific actions |
| `filters.policies` | Limit to specific policy names |
| `filters.agents` | Limit to specific agent IDs |
| `filters.tags` | Limit to specific data tags |
| `channels` | `file`, `slack`, `webhook` |

### Alert channels in safeai.yaml

```yaml
alerting:
  enabled: true
  cooldown_seconds: 60
  channels:
    slack_webhook_url: https://hooks.slack.com/services/...
    webhook_url: https://my-siem.internal/ingest
```

---

## CLI Observability Commands

```bash
# Watch recent audit events
safeai logs --last 15m

# Filter by boundary and action
safeai logs --boundary input --action block --last 1h

# Filter by agent
safeai logs --agent claude-code --last 24h

# Filter by data tag
safeai logs --data-tag secret.api_key

# Full event detail
safeai logs --detail <event-id>

# Agent activity summary
safeai observe agents --last 24h

# Full session trace
safeai observe sessions --session <session-id>
```

---

## safeai.yaml Config

Full observability-related configuration:

```yaml
audit:
  file_path: logs/audit.log

approvals:
  file_path: logs/approvals.log
  default_ttl: 30m

dashboard:
  enabled: true
  rbac_enabled: true
  user_header: x-safeai-user
  tenant_header: x-safeai-tenant
  tenant_policy_file: tenants/policy-sets.yaml
  alert_rules_file: alerts/default.yaml
  alert_log_file: logs/alerts.log
  users:
    - user_id: admin
      role: admin
      tenants: ["*"]

alerting:
  enabled: true
  default_channels: [file]
  cooldown_seconds: 60
  channels:
    slack_webhook_url: null
    webhook_url: null
```
