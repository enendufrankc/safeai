# SafeAI: technology and data design

## 1. Technology decisions

### Primary language: Python 3.10+

Rationale:
- Dominant language in AI/ML ecosystems
- Most agent frameworks (LangChain, CrewAI, Google ADK) are Python-first
- Claude ADK has strong Python support
- Reduces friction for target users (AI product engineers)
- Pydantic, FastAPI, and other dependencies are Python-native

Trade-offs:
- Lower raw throughput than Go or Rust for proxy workloads
- Mitigated by async I/O (uvicorn), compiled regex, and stateless design
- If proxy performance becomes a bottleneck, the gateway mode can be ported to Go later. The protocol is HTTP, so the core library and gateway are already decoupled.

### Dependencies

| Dependency | Purpose | Version | License |
|------------|---------|---------|---------|
| pydantic | Schema validation, config, data models | 2.x | MIT |
| fastapi | HTTP proxy for sidecar/gateway modes | 0.100+ | MIT |
| uvicorn | ASGI server | 0.27+ | BSD |
| click | CLI framework | 8.x | BSD |
| structlog | Structured logging | 24.x | Apache 2.0 |
| pyyaml | Policy/config file parsing | 6.x | MIT |
| cryptography | Handle encryption, TLS | 42.x | Apache 2.0 / BSD |

Dependency philosophy:
- Minimize total dependencies
- No dependencies on specific AI frameworks (LangChain, etc.)
- No dependencies on specific cloud providers
- Every dependency must be actively maintained and permissively licensed

### Package structure

```
safeai/
├── __init__.py
├── core/
│   ├── classifier.py          # Data classification engine
│   ├── policy.py              # Policy engine
│   ├── scanner.py             # Input scanner
│   ├── interceptor.py         # Action interceptor
│   ├── guard.py               # Output guard
│   ├── memory.py              # Memory controller
│   └── audit.py               # Audit logger
├── middleware/
│   ├── base.py                # Base middleware protocol
│   ├── langchain.py           # LangChain adapter
│   ├── claude_adk.py          # Claude ADK adapter
│   ├── google_adk.py          # Google ADK adapter
│   └── generic.py             # Generic function wrapper
├── proxy/
│   ├── server.py              # FastAPI proxy server
│   ├── routes.py              # Proxy route handlers
│   └── ws.py                  # WebSocket support
├── secrets/
│   ├── base.py                # Secret backend protocol
│   ├── env.py                 # Environment variable backend
│   ├── vault.py               # HashiCorp Vault backend
│   └── aws.py                 # AWS Secrets Manager backend
├── cli/
│   ├── main.py                # CLI entry point
│   ├── init.py                # safeai init command
│   ├── validate.py            # safeai validate command
│   ├── scan.py                # safeai scan command
│   ├── logs.py                # safeai logs command
│   └── serve.py               # safeai serve command
├── config/
│   ├── loader.py              # Configuration loading
│   ├── models.py              # Config Pydantic models
│   └── defaults/              # Default policies and schemas
└── detectors/
    ├── base.py                # Detector protocol
    ├── email.py               # Email detector
    ├── phone.py               # Phone number detector
    ├── ssn.py                 # SSN detector
    ├── credit_card.py         # Credit card detector
    ├── api_key.py             # API key/token detector
    └── custom.py              # User-defined pattern detector
```

## 2. Data architecture

### 2.1 Data classification taxonomy

```
Data Tag Hierarchy:

public          ── Safe for any audience
internal        ── Safe within the organization
confidential    ── Restricted by role or policy
personal        ── Subject to privacy regulation
  ├── pii       ── Personally identifiable information
  ├── phi       ── Protected health information
  └── financial ── Financial account data
secret          ── Never exposed to agents
  ├── credential ── Passwords, keys, tokens
  └── token      ── Session/auth tokens
```

Tags are hierarchical. A policy targeting `personal` matches `pii`, `phi`, and `financial`.

### 2.2 Policy data model

```yaml
# Policy file schema
policy:
  name: string                    # Unique policy name
  description: string             # Human-readable description
  boundary: input | action | output | [list]
  priority: integer               # Lower = higher priority
  condition:
    data_tags: [string]           # Match if any of these tags present
    tools: [string]               # Match specific tools (action boundary)
    agents: [string]              # Match specific agent IDs
    direction: inbound | outbound # For proxy mode
  action: allow | redact | block | require_approval
  fallback_template: string       # Template for blocked responses
  reason: string                  # Human-readable reason (for audit)
```

### 2.3 Tool contract data model

```yaml
# Tool contract schema
contract:
  tool_name: string
  description: string
  accepts:
    tags: [string]                # Data tags this tool can receive
    fields: [string]              # Specific fields accepted
  emits:
    tags: [string]                # Data tags this tool may return
    fields: [string]              # Specific fields returned
  stores:
    fields: [string]              # What the tool persists
    retention: duration           # How long stored data lives
  side_effects:
    reversible: boolean
    requires_approval: boolean
    description: string
```

### 2.4 Memory schema data model

```yaml
# Memory schema
memory:
  name: string
  scope: session | user | global
  fields:
    - name: string
      type: string | integer | boolean | list | object
      tag: string                 # Data classification tag
      retention: duration         # Auto-purge after this period
      encrypted: boolean          # Store as encrypted handle
      required: boolean
  max_entries: integer            # Maximum stored items
  default_retention: duration     # Default if field doesn't specify
```

### 2.5 Audit event data model

```json
{
  "event_id": "evt_<ulid>",
  "timestamp": "ISO-8601",
  "boundary": "input | action | output | memory",
  "agent_id": "string",
  "session_id": "string",
  "policy_name": "string | null",
  "action": "allow | redact | block | require_approval | approve | deny",
  "data_tags": ["string"],
  "tool_name": "string | null",
  "detections": [
    {
      "detector": "string",
      "tag": "string",
      "confidence": "0.0-1.0"
    }
  ],
  "context_hash": "sha256:string",
  "reason": "string",
  "approver_id": "string | null",
  "metadata": {}
}
```

### 2.6 Data flow between components

```
Input Data ──▶ Classifier ──▶ Tagged Data ──▶ Policy Engine ──▶ Decision
                                                                   │
                                              ┌────────────────────┤
                                              ▼                    ▼
                                        Audit Logger         Action Applier
                                              │              (redact/block/allow)
                                              ▼                    │
                                        Audit Store               ▼
                                                            Filtered Data
```

Raw sensitive data flows through SafeAI transiently. SafeAI never persists it. Only tags, hashes, and decisions are stored.

## 3. Storage design

### 3.1 SafeAI's own storage needs

SafeAI stores very little:

| Data | Storage | Persistence |
|------|---------|-------------|
| Policies | YAML files (read-only) | Disk |
| Tool contracts | YAML files (read-only) | Disk |
| Memory schemas | YAML files (read-only) | Disk |
| Audit events | Pluggable backend | Configurable retention |
| Agent memory | Pluggable backend | Schema-defined retention |
| Capability tokens | In-memory | Expires with TTL |

### 3.2 Audit log storage

Default: Structured JSON to file or stdout.

Pluggable backends:
- File (rotating, compressed)
- SQLite (local, for development)
- PostgreSQL (production, multi-node)
- Cloud logging (CloudWatch, Stackdriver, etc.)
- OpenTelemetry collector

### 3.3 Agent memory storage

SafeAI wraps the agent's memory backend, not replaces it.

Supported backends:
- In-memory (default, session-scoped)
- Redis
- PostgreSQL
- Custom (via protocol/interface)

SafeAI adds:
- Schema validation layer
- Encryption for sensitive fields
- Retention enforcement
- Access logging

## 4. API design

### 4.1 SDK API (Python)

```python
# Core initialization
safeai = SafeAI.from_config("safeai.yaml")
safeai = SafeAI(policies=[...], contracts=[...])

# Middleware pattern
@safeai.guard
def my_tool_call(tool, params):
    ...

# Explicit boundary calls
result = safeai.scan_input(data)
result = safeai.intercept_tool(tool_name, params)
result = safeai.guard_output(response)

# Memory
safeai.memory.write("user_preference", "dark_mode", agent_id="bot-1")
value = safeai.memory.read("user_preference", agent_id="bot-1")

# Audit
events = safeai.audit.query(boundary="output", action="blocked", last="1h")
```

### 4.2 Proxy API (HTTP: sidecar/gateway)

```
POST /v1/scan/input
POST /v1/intercept/tool
POST /v1/guard/output
POST /v1/memory/write
GET  /v1/memory/read
GET  /v1/audit/query
GET  /v1/health
POST /v1/policies/reload
```

All endpoints accept and return JSON. Standard HTTP status codes. OpenAPI spec is auto-generated.

## 5. Integration patterns

### 5.1 LangChain integration

```python
from safeai.middleware.langchain import SafeAICallback

chain = LLMChain(
    llm=llm,
    prompt=prompt,
    callbacks=[SafeAICallback(safeai)]
)
```

### 5.2 Generic agent integration

```python
from safeai import SafeAI

safeai = SafeAI.from_config("safeai.yaml")

# Wrap any tool execution function
original_execute = agent.execute_tool
agent.execute_tool = safeai.wrap(original_execute)
```

### 5.3 HTTP proxy integration

No code changes needed. Route agent HTTP traffic through the SafeAI proxy:

```
# Agent config
TOOL_API_BASE=http://localhost:8910/proxy

# SafeAI proxy forwards to actual tools
safeai serve --upstream http://actual-tool-api:8080
```

## 6. Testing strategy

| Level | What | Tools |
|-------|------|-------|
| Unit | Individual classifiers, policy evaluation, schema validation | pytest |
| Integration | Full boundary flows (input → classify → policy → filter) | pytest + fixtures |
| Contract | Tool contract validation, policy schema validation | pydantic + pytest |
| Performance | Boundary crossing latency benchmarks | pytest-benchmark |
| Security | Classifier evasion, policy bypass attempts | Custom test suite |
| End-to-end | Full agent workflow with SafeAI middleware | pytest + mock agent |

## 7. Monitoring and observability

| Signal | Implementation |
|--------|---------------|
| Metrics | Prometheus-compatible counters (requests, decisions, latency) |
| Traces | OpenTelemetry spans per boundary crossing |
| Logs | Structured JSON (structlog) |
| Health | `/v1/health` endpoint with component status |
| Alerts | Configurable rules on policy violation frequency |
