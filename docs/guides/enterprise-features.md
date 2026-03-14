# Enterprise Features

SafeAI provides enterprise-grade security, observability, and governance primitives for production AI deployments — multi-tenant isolation, audit retention, secret backends, real-time streaming, and cost controls out of the box.

!!! tip "Quick start"
    Most enterprise features activate automatically from `safeai.yaml`. Drop in your tenant rules, secret backend, and alert channels — SafeAI handles the rest.
    ```bash
    python -m safeai.cli.main setup langchain   # scaffold a project
    python -m safeai.cli.main serve              # start the gateway
    ```

## Multi-Tenant Isolation

Tenant-scoped policies let you define per-organisation rules that override global defaults. When `tenant_id` matches a rule, that rule takes priority; otherwise the engine falls back to the global policy set.

```python
from safeai.core.policy import PolicyEngine, PolicyContext, PolicyRule

rules = [
    PolicyRule(
        name="global-block-secrets",
        boundary="input",
        data_tags=["secret.credential"],
        action="block",
    ),
    PolicyRule(
        name="acme-allow-pii",
        boundary="input",
        data_tags=["personal.pii"],
        action="allow",
        tenant_id="acme",
    ),
    PolicyRule(
        name="default-redact-pii",
        boundary="input",
        data_tags=["personal.pii"],
        action="redact",
    ),
]

engine = PolicyEngine(rules=rules)

# Acme tenant — tenant-specific rule wins
ctx = PolicyContext(boundary="input", data_tags=["personal.pii"], tenant_id="acme")
decision = engine.evaluate(ctx)   # → "allow"

# Default tenant — global redact rule applies
ctx = PolicyContext(boundary="input", data_tags=["personal.pii"], tenant_id="default")
decision = engine.evaluate(ctx)   # → "redact"
```

!!! info "Evaluation order"
    The policy engine evaluates rules in definition order. A tenant-scoped rule matching the current `tenant_id` is selected before any global rule with the same `data_tags`.

### Tenant Configuration

```yaml title="safeai.yaml"
tenants:
  acme:
    policies:
      - name: acme-allow-pii
        boundary: input
        data_tags: ["personal.pii"]
        action: allow
  default:
    policies:
      - name: default-redact-pii
        boundary: input
        data_tags: ["personal.pii"]
        action: redact
```

| Field | Type | Description |
|-------|------|-------------|
| `tenant_id` | `str` | Unique identifier scoped to an organisation or team |
| `boundary` | `str` | `input` or `output` — where the rule applies |
| `data_tags` | `list[str]` | Tags that trigger this rule (e.g. `personal.pii`, `secret.credential`) |
| `action` | `str` | One of `allow`, `block`, `redact`, `flag` |

## Audit Retention

SafeAI rotates and compresses audit logs automatically. Configure size limits, age thresholds, and compression in `safeai.yaml`.

```yaml title="safeai.yaml"
audit:
  max_size_mb: 100
  max_age_days: 90
  compress_rotated: true
```

```python
from safeai.config.models import SafeAIConfig

cfg = SafeAIConfig()
print(f"max_size={cfg.audit.max_size_mb}MB, max_age={cfg.audit.max_age_days}d")
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `max_size_mb` | `int` | `100` | Maximum log file size before rotation |
| `max_age_days` | `int` | `90` | Days to retain rotated logs |
| `compress_rotated` | `bool` | `true` | gzip-compress rotated log files |

!!! warning "Disk pressure"
    If `compress_rotated` is disabled and `max_age_days` is high, audit logs can consume significant disk space in high-throughput environments. Monitor your `/logs` directory.

## Secret Backends

SafeAI supports pluggable secret backends so credentials never live in plain-text config files. Choose from environment variables, HashiCorp Vault, or AWS Secrets Manager.

```yaml title="safeai.yaml"
secrets:
  backend: vault          # env | vault | aws
  vault:
    address: https://vault.internal:8200
    token_env: VAULT_TOKEN
    path: secret/data/safeai
  aws:
    region: us-east-1
    secret_name: safeai/prod
```

### Backend Reference

| Backend | Key | Required Fields |
|---------|-----|-----------------|
| `env` | Environment variables | Variable names mapped in `secrets.env_map` |
| `vault` | HashiCorp Vault | `address`, `token_env`, `path` |
| `aws` | AWS Secrets Manager | `region`, `secret_name` |

!!! tip "Local development"
    Use `backend: env` during development and switch to `vault` or `aws` for staging and production via environment-specific YAML overrides.

## Alert Channels

Route policy violations, budget overruns, and system events to your incident management stack.

```yaml title="safeai.yaml"
alerts:
  channels:
    - type: email
      to: ["security-team@example.com"]
      smtp_host: smtp.example.com
      smtp_port: 587
    - type: pagerduty
      routing_key: ${PAGERDUTY_KEY}
    - type: opsgenie
      api_key: ${OPSGENIE_KEY}
      region: us
```

```python
from safeai.alerting.email import EmailAlertChannel
from safeai.alerting.pagerduty import PagerDutyAlertChannel
from safeai.alerting.opsgenie import OpsgenieAlertChannel
```

| Channel | Required Config | Description |
|---------|-----------------|-------------|
| `email` | `to`, `smtp_host`, `smtp_port` | SMTP-based email alerts |
| `pagerduty` | `routing_key` | PagerDuty Events API v2 |
| `opsgenie` | `api_key`, `region` | Opsgenie Alert API |

!!! danger "Keep secrets out of YAML"
    Always reference alert credentials via environment variables (`${VAR}`) or a [secret backend](#secret-backends) — never commit plain-text keys.

## WebSocket Streaming

Subscribe to real-time policy events over a persistent WebSocket connection. The `/v1/ws/events` endpoint streams decisions as they happen.

```python
import asyncio
import json
import websockets

async def stream_events():
    uri = "ws://127.0.0.1:8910/v1/ws/events"
    async with websockets.connect(uri) as ws:
        # Subscribe to input-boundary events
        await ws.send(json.dumps({"boundary": "input"}))
        async for message in ws:
            event = json.loads(message)
            print(f"[{event['timestamp']}] {event['action']} — {event['rule']}")

asyncio.run(stream_events())
```

| Field | Type | Description |
|-------|------|-------------|
| `boundary` | `str` | Filter events by `input`, `output`, or omit for all |
| `tenant_id` | `str` | Optional — restrict stream to a single tenant |

!!! info "Connection lifecycle"
    The server sends a heartbeat every 30 seconds. Clients that miss three consecutive heartbeats are disconnected automatically.

## MCP Write Operations

The Model Context Protocol (MCP) server exposes the following write-capable tools for programmatic governance:

| Tool | Description |
|------|-------------|
| `reload_policies` | Hot-reload policy rules from `safeai.yaml` without restarting |
| `approve` | Approve a pending action in the approval workflow |
| `deny` | Deny a pending action in the approval workflow |
| `list_plugins` | List all registered SafeAI plugins and their status |
| `check_budget` | Query remaining budget for a user or tenant |
| `health_check` | Return gateway health, uptime, and version info |

!!! tip "MCP + IDE integration"
    MCP tools are callable from any MCP-compatible client (e.g. Claude Desktop, VS Code Copilot). Use `reload_policies` after editing `safeai.yaml` to apply changes without downtime.

## OpenAPI Documentation

The SafeAI gateway auto-generates interactive API docs from its route definitions.

| Endpoint | Format |
|----------|--------|
| `/docs` | Swagger UI (interactive) |
| `/redoc` | ReDoc (read-optimised) |
| `/openapi.json` | Raw OpenAPI 3.x spec |

```bash
# Verify docs are live
curl -s http://127.0.0.1:8910/docs | head -5

# Fetch raw spec
curl -s http://127.0.0.1:8910/openapi.json | python -m json.tool | head -20
```

## Framework Setup

Scaffold SafeAI integration boilerplate for popular agent frameworks with a single command.

```bash
python -m safeai.cli.main setup langchain
python -m safeai.cli.main setup crewai
python -m safeai.cli.main setup autogen
```

| Framework | Generated Files | Description |
|-----------|----------------|-------------|
| `langchain` | `safeai_langchain.py`, config patches | LangChain callback + chain wrappers |
| `crewai` | `safeai_crewai.py`, config patches | CrewAI agent/task guardrails |
| `autogen` | `safeai_autogen.py`, config patches | AutoGen message-filter hooks |

!!! tip "Custom frameworks"
    You can extend the setup system with plugins. See [Creating Plugins](creating-plugins.md) for details.

## Cost Dashboard

Monitor AI spend per user, tenant, or model via the built-in cost dashboard endpoint.

```bash
curl -s http://127.0.0.1:8910/v1/dashboard/cost/summary \
  -H "x-safeai-user: admin" | python -m json.tool
```

The response includes:

| Field | Type | Description |
|-------|------|-------------|
| `total_cost` | `float` | Aggregate spend across all models |
| `by_model` | `dict` | Cost breakdown keyed by model name |
| `by_tenant` | `dict` | Cost breakdown keyed by tenant ID |
| `period` | `str` | Time window for the summary (e.g. `last_30d`) |

!!! warning "Authentication required"
    The cost dashboard requires the `x-safeai-user` header. Users without the `admin` or `billing` role receive a `403 Forbidden`.

### Routing Proxy

The gateway can also proxy requests to downstream LLM providers while enforcing policies, budgets, and audit logging transparently. Configure the proxy target in `safeai.yaml`:

```yaml title="safeai.yaml"
proxy:
  target: https://api.openai.com/v1
  timeout_seconds: 30
  retry:
    max_attempts: 3
    backoff_factor: 0.5
```

## See Also

- [Policy Engine](policy-engine.md)
- [Audit Logging](audit-logging.md)
- [Approval Workflows](approval-workflows.md)
- [Creating Plugins](creating-plugins.md)
- [Troubleshooting](troubleshooting.md)
