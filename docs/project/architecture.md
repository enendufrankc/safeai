# Architecture

This page describes SafeAI's internal module structure, boundary model, and core design decisions.

---

## Module Structure

```
safeai/
  __init__.py              # Package root, version
  __main__.py              # python -m safeai entry point
  api.py                   # Public SDK interface (SafeAI class)

  cli/                     # CLI commands
    main.py                # Click group and entry point
    init.py                # safeai init
    scan.py                # safeai scan
    validate.py            # safeai validate
    logs.py                # safeai logs
    serve.py               # safeai serve
    hook.py                # safeai hook
    setup.py               # safeai setup
    approvals.py           # safeai approvals
    templates.py           # safeai templates
    mcp.py                 # safeai mcp

  core/                    # Enforcement engine
    models.py              # Shared data models (ScanResult, etc.)
    classifier.py          # Content classifier (PII, secrets, tags)
    policy.py              # Policy engine (rules, priorities, matching)
    interceptor.py         # Action-boundary interceptor
    guard.py               # Output guard
    scanner.py             # Input boundary scanner
    structured.py          # Structured payload and file scanning
    audit.py               # Audit logger and query interface
    memory.py              # Encrypted memory controller
    approval.py            # Approval workflow manager
    contracts.py           # Tool contract registry
    identity.py            # Agent identity registry

  config/                  # Configuration
    loader.py              # YAML config loading and hot reload
    models.py              # Config schema (Pydantic models)
    defaults/              # Default scaffold files
      plugins/example.py   # Plugin starter template

  detectors/               # Content detectors
    base.py                # BaseDetector abstract class
    api_key.py             # API key patterns
    credit_card.py         # Credit card numbers
    email.py               # Email addresses
    phone.py               # Phone numbers
    ssn.py                 # Social Security Numbers
    custom.py              # User-defined regex detectors

  middleware/              # Framework adapters
    base.py                # BaseMiddleware abstract class
    langchain.py           # LangChain adapter
    crewai.py              # CrewAI adapter
    autogen.py             # AutoGen adapter
    claude_adk.py          # Claude ADK adapter
    google_adk.py          # Google ADK adapter
    generic.py             # Generic middleware

  secrets/                 # Secret management
    base.py                # BaseSecretBackend abstract class
    manager.py             # Secret resolution manager
    env.py                 # Environment variable backend
    vault.py               # HashiCorp Vault backend
    aws.py                 # AWS Secrets Manager backend
    capability.py          # Capability token system

  proxy/                   # HTTP proxy server
    server.py              # FastAPI app factory
    routes.py              # REST API endpoints
    metrics.py             # Prometheus-style metrics
    ws.py                  # WebSocket support

  dashboard/               # Enterprise dashboard
    routes.py              # Dashboard API endpoints
    service.py             # Dashboard business logic

  plugins/                 # Plugin system
    manager.py             # Plugin loader and discovery

  templates/               # Policy templates
    catalog.py             # Template catalog and discovery

  agents/                  # Coding agent support
    profiles.py            # Agent profile definitions
    installers/            # Hook installers
      claude_code.py       # Claude Code installer
      cursor.py            # Cursor installer
      generic.py           # Generic installer

  mcp/                     # Model Context Protocol
    server.py              # MCP server implementation

  schemas/                 # JSON schemas
    v1alpha1/              # Schema version
```

---

## Boundary Model

SafeAI enforces security at three boundaries. Every piece of data flowing through an AI system passes through at least one of these boundaries.

```
                    +-------------------+
    User Input ---->|  INPUT BOUNDARY   |----> Agent
                    +-------------------+
                           |
                    +-------------------+
    Agent -------->|  ACTION BOUNDARY  |----> Tool / API / Agent
                    +-------------------+
                           |
                    +-------------------+
    Agent -------->|  OUTPUT BOUNDARY  |----> User
                    +-------------------+
```

### Input Boundary

Scans content entering the agent. Detects secrets, PII, injection attempts, and policy-violating content before the agent processes it.

**Components:** `core/scanner.py`, `core/structured.py`, `detectors/*`

### Action Boundary

Intercepts tool calls, API requests, and agent-to-agent messages. Enforces tool contracts, agent identity checks, clearance tags, and approval gates.

**Components:** `core/interceptor.py`, `core/contracts.py`, `core/identity.py`, `core/approval.py`

### Output Boundary

Guards content leaving the agent. Applies output policies, redaction, fallback templates, and field-level filtering before responses reach users or downstream systems.

**Components:** `core/guard.py`, `core/policy.py`

---

## Component Descriptions

### Policy Engine (`core/policy.py`)

Evaluates rules against scan results to determine the enforcement action. Supports:

- Rule priorities (higher priority wins)
- Hierarchical data-tag matching (`personal` matches `personal.pii`)
- Boundary-specific rules (input, action, output)
- Hot reload without restart

### Classifier (`core/classifier.py`)

Runs all registered detectors against input text and aggregates detection results with data tags and confidence scores.

### Interceptor (`core/interceptor.py`)

The action-boundary enforcement point. Validates tool calls against contracts, checks agent identity and clearance, evaluates policies, and triggers approval gates when needed.

### Audit Logger (`core/audit.py`)

Records every enforcement decision with full context: event ID, context hash, session/source/destination IDs, matched policy, detection tags, and the action taken. Supports time-range queries and event detail retrieval.

### Memory Controller (`core/memory.py`)

Manages encrypted agent memory with schema validation, per-agent isolation, retention policies, and automatic expiry purge.

### Approval Manager (`core/approval.py`)

Manages the human-in-the-loop approval workflow. Creates approval requests when policies require it, tracks request state, and validates approval/denial decisions.

### Secret Manager (`secrets/manager.py`)

Resolves secrets through pluggable backends (environment variables, Vault, AWS Secrets Manager) with audit logging that never exposes secret payloads.

### Capability Token System (`secrets/capability.py`)

Issues scoped, time-limited tokens that grant access to specific secrets or operations. Tokens have fine-grained scopes and TTLs.

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Boundary model over middleware chain** | Three explicit boundaries (input, action, output) map directly to the data flow in agent systems, making policies easier to reason about than a flat middleware stack. |
| **Policy-as-data (YAML) over policy-as-code** | YAML policies can be reviewed by security teams without reading Python. They can be version-controlled, diffed, and hot-reloaded independently of application code. |
| **Framework-agnostic core** | The core engine has zero framework dependencies. Framework-specific adapters are thin wrappers in `middleware/`, making it trivial to add new frameworks. |
| **Deterministic enforcement** | Given the same input and policy, SafeAI always produces the same decision. No probabilistic or ML-based filtering in the enforcement path. |
| **Audit everything** | Every boundary decision is logged with full context. This is non-negotiable for compliance and incident investigation. |
| **Plugin system over monolith** | Custom detectors, adapters, and policy templates are loaded via entry points, keeping the core package small and extensible. |
