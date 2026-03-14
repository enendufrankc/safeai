---
description: "Deploy SafeAI as a sidecar proxy — HTTP endpoints, approval workflows, real-time WebSocket events, and the built-in dashboard."
---

# Proxy & API Deployment

SafeAI ships with a production-ready HTTP proxy built on FastAPI.
Run it as a **sidecar** next to your AI service or as a centralised
**gateway** — every scan, guard, intercept, memory, and audit operation
is available over REST with full OpenAPI documentation.

---

## 1 — Starting the Proxy

### Sidecar mode (default)

```bash
python -m safeai.cli.main serve \
  --mode sidecar \
  --host 127.0.0.1 \
  --port 8910 \
  --config safeai.yaml
```

### Gateway mode

Gateway mode optionally forwards allowed requests to an upstream LLM
provider:

```bash
python -m safeai.cli.main serve \
  --mode gateway \
  --host 0.0.0.0 \
  --port 8910 \
  --config safeai.yaml \
  --upstream-base-url https://api.openai.com
```

!!! tip
    In sidecar mode the proxy only exposes SafeAI endpoints.
    In gateway mode it can also forward traffic through
    `/v1/proxy/forward` after applying safety checks.

---

## 2 — Core HTTP Endpoints

All endpoints live under the `/v1` prefix.

### Health check

```bash
curl -s http://127.0.0.1:8910/v1/health | python -m json.tool
```

```json
{
  "status": "ok"
}
```

---

### Scan input

Scan raw text before it reaches the LLM.

```bash
curl -s -X POST http://127.0.0.1:8910/v1/scan/input \
  -H "Content-Type: application/json" \
  -d '{
    "text": "token=sk-ABCDEF1234567890ABCDEF",
    "agent_id": "default-agent"
  }' | python -m json.tool
```

```json
{
  "decision": {
    "action": "block",
    "reason": "Secret detected in input",
    "policy_name": "default-secret-detection"
  },
  "detections": [
    {
      "type": "secret",
      "value": "sk-ABCDEF1234567890ABCDEF",
      "location": { "start": 6, "end": 32 }
    }
  ]
}
```

---

### Scan structured input

Scan nested JSON payloads — detections include JSON-path locations.

```bash
curl -s -X POST http://127.0.0.1:8910/v1/scan/structured \
  -H "Content-Type: application/json" \
  -d '{
    "payload": {
      "request": {
        "token": "sk-ABCDEF1234567890ABCDEF",
        "message": "deploy to production"
      }
    },
    "agent_id": "default-agent"
  }' | python -m json.tool
```

```json
{
  "decision": {
    "action": "block",
    "reason": "Secret detected in structured input"
  },
  "detections": [
    {
      "type": "secret",
      "path": "$.request.token"
    }
  ]
}
```

---

### Scan file

Scan a file on disk (JSON files use structured mode automatically).

```bash
curl -s -X POST http://127.0.0.1:8910/v1/scan/file \
  -H "Content-Type: application/json" \
  -d '{
    "path": "data.json",
    "agent_id": "default-agent"
  }' | python -m json.tool
```

---

### Guard output

Redact PII and secrets before text reaches the user.

```bash
curl -s -X POST http://127.0.0.1:8910/v1/guard/output \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Contact alice@example.com or call 555-0100.",
    "agent_id": "default-agent"
  }' | python -m json.tool
```

```json
{
  "decision": {
    "action": "redact",
    "reason": "PII detected in output"
  },
  "safe_output": "Contact [EMAIL_REDACTED] or call [PHONE_REDACTED].",
  "detections": [
    { "type": "email", "value": "alice@example.com" },
    { "type": "phone", "value": "555-0100" }
  ]
}
```

---

### Intercept tool request

Validate a tool call against policies, contracts, and identity
declarations **before** the tool executes.

```bash
curl -s -X POST http://127.0.0.1:8910/v1/intercept/tool \
  -H "Content-Type: application/json" \
  -d '{
    "phase": "request",
    "tool_name": "shell_exec",
    "parameters": { "command": "rm -rf /" },
    "data_tags": ["destructive"],
    "agent_id": "default-agent",
    "session_id": "sess-001"
  }' | python -m json.tool
```

```json
{
  "decision": {
    "action": "block",
    "reason": "Destructive command blocked by policy"
  }
}
```

To guard the **response** from a tool, set `"phase": "response"` and
include the tool output in `"response"`.

---

### Memory write / read

```bash
# Write
curl -s -X POST http://127.0.0.1:8910/v1/memory/write \
  -H "Content-Type: application/json" \
  -d '{
    "key": "user_preference",
    "value": "en-US",
    "agent_id": "default-agent"
  }' | python -m json.tool
```

```json
{ "ok": true }
```

```bash
# Read
curl -s -X POST http://127.0.0.1:8910/v1/memory/read \
  -H "Content-Type: application/json" \
  -d '{
    "key": "user_preference",
    "agent_id": "default-agent"
  }' | python -m json.tool
```

```json
{ "value": "en-US" }
```

---

### Audit log

```bash
curl -s "http://127.0.0.1:8910/v1/audit?limit=5" | python -m json.tool
```

---

### Metrics

Prometheus-format metrics for monitoring:

```bash
curl -s http://127.0.0.1:8910/v1/metrics
```

---

### Policy reload

```bash
curl -s -X POST http://127.0.0.1:8910/v1/policies/reload | python -m json.tool
```

```json
{ "reloaded": true }
```

| Endpoint | Method | Purpose |
|:---------|:-------|:--------|
| `/v1/health` | GET | Health check |
| `/v1/scan/input` | POST | Scan text input |
| `/v1/scan/structured` | POST | Scan nested JSON |
| `/v1/scan/file` | POST | Scan file on disk |
| `/v1/guard/output` | POST | Guard & redact output |
| `/v1/intercept/tool` | POST | Intercept tool request or response |
| `/v1/memory/write` | POST | Write to agent memory |
| `/v1/memory/read` | POST | Read from agent memory |
| `/v1/audit` | GET | Query audit events |
| `/v1/metrics` | GET | Prometheus metrics |
| `/v1/policies/reload` | POST | Hot-reload policies |

---

## 3 — Approval Workflow via API

Sensitive operations (e.g., accessing production databases) can require
human approval before proceeding.

### Step 1 — Trigger an approval-gated tool call

```bash
curl -s -X POST http://127.0.0.1:8910/v1/intercept/tool \
  -H "Content-Type: application/json" \
  -d '{
    "phase": "request",
    "tool_name": "database_query",
    "parameters": { "query": "DELETE FROM users WHERE active = false" },
    "data_tags": ["destructive", "pii"],
    "agent_id": "default-agent",
    "session_id": "sess-002"
  }' | python -m json.tool
```

```json
{
  "decision": {
    "action": "pending_approval",
    "reason": "Human approval required for destructive database operation"
  },
  "approval_request_id": "ar-a1b2c3d4"
}
```

### Step 2 — List pending approvals

```bash
curl -s "http://127.0.0.1:8910/v1/approvals?status=pending&limit=10" \
  | python -m json.tool
```

```json
[
  {
    "request_id": "ar-a1b2c3d4",
    "agent_id": "default-agent",
    "tool_name": "database_query",
    "status": "pending",
    "created_at": "2025-01-15T10:30:00Z"
  }
]
```

### Step 3 — Approve or deny

```bash
curl -s -X POST http://127.0.0.1:8910/v1/approvals/ar-a1b2c3d4/approve \
  -H "Content-Type: application/json" \
  -d '{
    "approver_id": "security-admin",
    "note": "Reviewed — safe to proceed with cleanup"
  }' | python -m json.tool
```

```json
{
  "request_id": "ar-a1b2c3d4",
  "status": "approved",
  "approver_id": "security-admin"
}
```

### Step 4 — Retry the tool call with approval

```bash
curl -s -X POST http://127.0.0.1:8910/v1/intercept/tool \
  -H "Content-Type: application/json" \
  -d '{
    "phase": "request",
    "tool_name": "database_query",
    "parameters": { "query": "DELETE FROM users WHERE active = false" },
    "data_tags": ["destructive", "pii"],
    "agent_id": "default-agent",
    "session_id": "sess-002",
    "approval_request_id": "ar-a1b2c3d4"
  }' | python -m json.tool
```

```json
{
  "decision": {
    "action": "allow",
    "reason": "Approved by security-admin"
  }
}
```

!!! note
    Approval TTL is configurable in `safeai.yaml` under
    `approvals.default_ttl`. Expired approvals are automatically
    rejected.

---

## 4 — Dashboard

SafeAI includes a built-in web dashboard for real-time monitoring,
audit browsing, and approval management.

### Accessing the dashboard

When the proxy is running with `dashboard.enabled: true` in
`safeai.yaml`, open:

```
http://127.0.0.1:8910/dashboard
```

### RBAC roles

The dashboard supports role-based access control via the
`x-safeai-user` and `x-safeai-tenant` headers:

| Role | Capabilities |
|:-----|:-------------|
| `admin` | Full access — policies, approvals, audit, config |
| `approver` | View audit, approve / deny requests |
| `auditor` | Read-only access to audit logs and metrics |
| `viewer` | Read-only dashboard access |

Configure users in `safeai.yaml`:

```yaml
dashboard:
  enabled: true
  rbac_enabled: true
  user_header: x-safeai-user
  tenant_header: x-safeai-tenant
  users:
    - user_id: security-admin
      role: admin
      tenants: ["*"]
    - user_id: security-approver
      role: approver
      tenants: ["default"]
```

---

## 5 — WebSocket Events

Subscribe to a real-time event stream for live monitoring, alerting, or
driving custom UIs.

### Connect

```bash
# Using websocat (or any WebSocket client)
websocat ws://127.0.0.1:8910/v1/events
```

### Event format

Events are JSON objects pushed to all connected clients:

```json
{
  "event": "scan.blocked",
  "timestamp": "2025-01-15T10:32:15Z",
  "agent_id": "default-agent",
  "detail": {
    "boundary": "input",
    "action": "block",
    "detection_type": "secret"
  }
}
```

### Common event types

| Event | Fired when |
|:------|:-----------|
| `scan.allowed` | Input scan passes all checks |
| `scan.blocked` | Input scan triggers a block |
| `guard.redacted` | Output guard redacts content |
| `intercept.blocked` | Tool call blocked by policy |
| `intercept.pending_approval` | Tool call awaiting human approval |
| `approval.approved` | An approval request is approved |
| `approval.denied` | An approval request is denied |
| `memory.write` | Agent writes to memory |
| `policy.reloaded` | Policies hot-reloaded from disk |

!!! tip
    Use WebSocket events to feed dashboards, Slack bots, or PagerDuty
    integrations. Each event includes enough context to triage without
    querying the audit log.

---

## 6 — OpenAPI Documentation

The proxy auto-generates interactive API documentation from its FastAPI
routes.

| URL | Format |
|:----|:-------|
| `http://127.0.0.1:8910/docs` | Swagger UI — interactive try-it-out console |
| `http://127.0.0.1:8910/redoc` | ReDoc — clean reference documentation |
| `http://127.0.0.1:8910/openapi.json` | Raw OpenAPI 3.x spec (JSON) |

### Fetch the spec programmatically

```bash
curl -s http://127.0.0.1:8910/openapi.json | python -m json.tool | head -20
```

```json
{
  "openapi": "3.1.0",
  "info": {
    "title": "SafeAI Proxy",
    "version": "0.1.0"
  },
  "paths": {
    "/v1/health": { "..." },
    "/v1/scan/input": { "..." },
    "/v1/guard/output": { "..." }
  }
}
```

Use the spec to auto-generate client SDKs in any language, import into
Postman, or validate requests in CI with spectral / openapi-diff.

---

## Running as a Service

=== "systemd (Linux)"

    ```ini
    [Unit]
    Description=SafeAI Proxy
    After=network.target

    [Service]
    ExecStart=/usr/bin/python -m safeai.cli.main serve \
      --mode sidecar --host 127.0.0.1 --port 8910 --config /etc/safeai/safeai.yaml
    Restart=on-failure
    User=safeai

    [Install]
    WantedBy=multi-user.target
    ```

=== "launchd (macOS)"

    ```xml
    <?xml version="1.0" encoding="UTF-8"?>
    <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
      "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
    <plist version="1.0">
    <dict>
      <key>Label</key>
      <string>com.safeai.proxy</string>
      <key>ProgramArguments</key>
      <array>
        <string>/usr/bin/python3</string>
        <string>-m</string>
        <string>safeai.cli.main</string>
        <string>serve</string>
        <string>--mode</string>
        <string>sidecar</string>
        <string>--host</string>
        <string>127.0.0.1</string>
        <string>--port</string>
        <string>8910</string>
        <string>--config</string>
        <string>/etc/safeai/safeai.yaml</string>
      </array>
      <key>RunAtLoad</key>
      <true/>
      <key>KeepAlive</key>
      <true/>
    </dict>
    </plist>
    ```

=== "Docker"

    ```dockerfile
    FROM python:3.12-slim
    RUN pip install safeai
    COPY safeai.yaml /app/safeai.yaml
    WORKDIR /app
    EXPOSE 8910
    CMD ["python", "-m", "safeai.cli.main", "serve", \
         "--mode", "sidecar", "--host", "0.0.0.0", "--port", "8910", \
         "--config", "safeai.yaml"]
    ```

---

## Next Steps

- [SDK Quick Start Examples](sdk-quickstart.md) — use all these endpoints from Python
- [Proxy / Sidecar Integration](../integrations/proxy-sidecar.md) — architecture patterns and deployment topologies
- [Approval Workflows Guide](../guides/approval-workflows.md) — advanced approval chains and escalation
- [Dashboard Reference](../reference/dashboard.md) — RBAC, alerting, and custom views
- [Plugins Integration](../integrations/plugins.md) — extend the proxy with custom detectors
- [API Reference — SafeAI](../reference/safeai.md) — full method signatures and types
