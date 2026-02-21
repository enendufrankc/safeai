# Proxy / Sidecar / Gateway

Run SafeAI as a standalone HTTP service alongside your agents. This mode requires **zero code changes** -- any language or framework can call the REST API.

---

## Modes

| Mode | Command | Use Case |
|------|---------|----------|
| **Sidecar** | `safeai serve --mode sidecar --port 8000` | Single agent on the same host |
| **Gateway** | `safeai serve --mode gateway` | Centralized enforcement for multiple agents |

```mermaid
graph LR
    subgraph "Sidecar Mode"
        A1[Agent] -->|HTTP| S1[SafeAI :8000]
    end

    subgraph "Gateway Mode"
        A2[Agent A] -->|HTTP| GW[SafeAI Gateway :8000]
        A3[Agent B] -->|HTTP| GW
        A4[Agent C] -->|HTTP| GW
    end
```

---

## Quick Start

### Start the Sidecar

```bash
safeai serve --mode sidecar --port 8000
```

### Test It

```bash
curl -X POST http://localhost:8000/v1/scan/input \
  -H "Content-Type: application/json" \
  -d '{"text": "Use key sk-ABCDEF1234567890"}'
```

Response:

```json
{
  "decision": "block",
  "violations": [
    {
      "type": "secret_detected",
      "detector": "api_key",
      "severity": "critical",
      "match": "sk-ABCDEF1234567890"
    }
  ]
}
```

---

## API Endpoints

### `POST /v1/scan/input`

Scan agent input (prompts, user messages, tool arguments) for policy violations.

**Request:**

```json
{
  "text": "The user's SSN is 123-45-6789",
  "agent_id": "support-agent",
  "context": {
    "tool": "send_email",
    "session_id": "abc-123"
  }
}
```

**Response:**

=== "Violation found"

    ```json
    {
      "decision": "block",
      "violations": [
        {
          "type": "pii_detected",
          "detector": "ssn",
          "severity": "high",
          "match": "123-45-6789"
        }
      ],
      "scan_duration_ms": 12
    }
    ```

=== "Clean input"

    ```json
    {
      "decision": "allow",
      "violations": [],
      "scan_duration_ms": 3
    }
    ```

---

### `POST /v1/guard/output`

Guard agent output (responses, tool results) before they reach the user or downstream system.

**Request:**

```json
{
  "text": "Here is the config: DATABASE_URL=postgresql://admin:p4ssw0rd@db.internal:5432/prod",
  "agent_id": "assistant",
  "context": {
    "tool": "read_config"
  }
}
```

**Response:**

```json
{
  "decision": "modify",
  "modified_text": "Here is the config: DATABASE_URL=[REDACTED]",
  "violations": [
    {
      "type": "secret_detected",
      "detector": "connection_string",
      "severity": "critical"
    }
  ],
  "scan_duration_ms": 8
}
```

---

### `POST /v1/intercept/tool`

Full tool-call interception -- validates the tool name, agent permissions, input, and contract before execution.

**Request:**

```json
{
  "tool": "execute_sql",
  "input": {
    "query": "SELECT * FROM users WHERE email = 'admin@company.com'"
  },
  "agent_id": "data-analyst",
  "session_id": "sess-456"
}
```

**Response:**

=== "Allowed"

    ```json
    {
      "decision": "allow",
      "tool": "execute_sql",
      "agent_id": "data-analyst"
    }
    ```

=== "Blocked by contract"

    ```json
    {
      "decision": "block",
      "tool": "execute_sql",
      "agent_id": "data-analyst",
      "reason": "Agent 'data-analyst' is not in the allowed_agents list for tool 'execute_sql'",
      "violations": [
        {
          "type": "contract_violation",
          "rule": "allowed_agents"
        }
      ]
    }
    ```

---

### `GET /v1/metrics`

Prometheus-style metrics endpoint for monitoring and alerting.

```bash
curl http://localhost:8000/v1/metrics
```

```
# HELP safeai_requests_total Total number of requests processed
# TYPE safeai_requests_total counter
safeai_requests_total{endpoint="scan_input",decision="allow"} 1523
safeai_requests_total{endpoint="scan_input",decision="block"} 47
safeai_requests_total{endpoint="guard_output",decision="allow"} 1498
safeai_requests_total{endpoint="guard_output",decision="modify"} 72
safeai_requests_total{endpoint="intercept_tool",decision="allow"} 891
safeai_requests_total{endpoint="intercept_tool",decision="block"} 23

# HELP safeai_violations_total Total violations detected by type
# TYPE safeai_violations_total counter
safeai_violations_total{type="secret_detected"} 31
safeai_violations_total{type="pii_detected"} 58
safeai_violations_total{type="contract_violation"} 28

# HELP safeai_scan_duration_seconds Scan duration histogram
# TYPE safeai_scan_duration_seconds histogram
safeai_scan_duration_seconds_bucket{le="0.01"} 3012
safeai_scan_duration_seconds_bucket{le="0.05"} 3089
safeai_scan_duration_seconds_bucket{le="0.1"} 3091
safeai_scan_duration_seconds_sum 42.7
safeai_scan_duration_seconds_count 3091
```

!!! tip "Grafana dashboard"
    Point your Prometheus scraper at `/v1/metrics` and import the SafeAI Grafana dashboard for real-time visibility into agent behavior.

---

## Gateway Mode

Gateway mode adds multi-tenant features for centralized enforcement:

```bash
safeai serve --mode gateway --port 8000
```

### Multi-Agent Routing

The gateway uses the `agent_id` field in each request to apply agent-specific policies:

```json
{
  "text": "Process this order",
  "agent_id": "order-processor"
}
```

### Health Check

```bash
curl http://localhost:8000/v1/health
```

```json
{
  "status": "healthy",
  "version": "0.6.0",
  "mode": "gateway",
  "uptime_seconds": 3600,
  "agents_seen": ["order-processor", "support-agent", "data-analyst"]
}
```

---

## Client Examples

=== "Python"

    ```python
    import requests

    response = requests.post(
        "http://localhost:8000/v1/scan/input",
        json={
            "text": "My API key is sk-abc123",
            "agent_id": "my-agent",
        },
    )

    result = response.json()
    if result["decision"] == "block":
        print(f"Blocked: {result['violations']}")
    ```

=== "JavaScript"

    ```javascript
    const response = await fetch("http://localhost:8000/v1/scan/input", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text: "My API key is sk-abc123",
        agent_id: "my-agent",
      }),
    });

    const result = await response.json();
    if (result.decision === "block") {
      console.log("Blocked:", result.violations);
    }
    ```

=== "Go"

    ```go
    payload := map[string]string{
        "text":     "My API key is sk-abc123",
        "agent_id": "my-agent",
    }
    body, _ := json.Marshal(payload)

    resp, _ := http.Post(
        "http://localhost:8000/v1/scan/input",
        "application/json",
        bytes.NewBuffer(body),
    )

    var result map[string]interface{}
    json.NewDecoder(resp.Body).Decode(&result)
    ```

=== "curl"

    ```bash
    curl -X POST http://localhost:8000/v1/scan/input \
      -H "Content-Type: application/json" \
      -d '{"text": "Use key sk-ABCDEF1234567890", "agent_id": "test"}'
    ```

---

## Configuration

```yaml
# safeai.yaml
server:
  host: "0.0.0.0"
  port: 8000
  mode: sidecar           # or "gateway"
  workers: 4
  cors_origins: ["*"]

policy:
  default_action: block
  secret_detection:
    enabled: true
  pii_protection:
    enabled: true
    action: redact

metrics:
  enabled: true
  endpoint: /v1/metrics

audit:
  enabled: true
  log_inputs: true
  log_outputs: true
```

---

## Docker

```dockerfile
FROM python:3.11-slim
RUN pip install safeai
COPY safeai.yaml /app/safeai.yaml
WORKDIR /app
EXPOSE 8000
CMD ["safeai", "serve", "--mode", "sidecar", "--port", "8000"]
```

```bash
docker build -t safeai-sidecar .
docker run -p 8000:8000 safeai-sidecar
```

---

## Next Steps

- [Coding Agents](coding-agents.md) -- hook-based integration for Claude Code and Cursor
- [Plugins](plugins.md) -- extend SafeAI with custom detectors
- [Audit Logging](../guides/audit-logging.md) -- query the decision log
