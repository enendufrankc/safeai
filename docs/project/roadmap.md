# Roadmap

SafeAI's development is organized into phases. Each phase builds on the previous one, adding capabilities while maintaining backward compatibility.

---

## Phase 1: Foundation (Core SDK) :white_check_mark:

**Version: 0.1.0rc1**

Established the core scanning and enforcement engine.

- Input boundary scanning with built-in detectors (API keys, PII, credit cards, SSNs, emails, phones)
- Policy engine with YAML rules, priorities, and hierarchical data-tag matching
- Output guard with fallback templates for block and redact actions
- Schema-bound memory controller with retention and expiry
- Audit logger with query interface and CLI filters
- Policy hot reload without restart
- `safeai init`, `safeai scan`, `safeai validate`, `safeai logs` CLI commands
- Unit, integration, and performance gate tests
- CI quality workflow

---

## Phase 2: Tool Control :white_check_mark:

**Version: 0.2.0**

Added action-boundary enforcement for tool calls and agent identity.

- Tool contract registry with schema-backed validation
- Action-boundary request contract checks and response field filtering
- Agent identity registry with tool binding and clearance-tag enforcement
- Full action-boundary audit payloads (event ID, context hash, session metadata)
- Advanced `safeai logs` querying (data tags, phases, sessions, event detail)
- Production LangChain adapter
- Agent identity schema and default scaffold

---

## Phase 3: Secrets and Approvals :white_check_mark:

**Version: 0.3.0**

Introduced secret management, approval workflows, and additional framework support.

- Approval workflow manager with persistent state and validation bindings
- Runtime approval gates for `require_approval` policy outcomes
- `safeai approvals list|approve|deny` CLI commands
- Secret resolution with audit events (no payload exposure)
- Encrypted memory handle storage with per-agent resolution
- Memory retention purge automation
- Claude ADK and Google ADK adapters
- Optional dependency groups for Vault and AWS backends

---

## Phase 4: Proxy and Scale :white_check_mark:

**Version: 0.4.0**

Built the HTTP proxy for language-agnostic deployment.

- Full proxy HTTP API surface (input scan, output guard, tool interception, memory, audit, policy reload)
- Upstream forwarding mode with pre-scan and post-guard
- Gateway mode with source/destination agent context
- Prometheus-style request counters, decision counters, and latency histograms at `/v1/metrics`
- `safeai serve` with mode, config, and upstream options
- Proxy integration and benchmark suites

---

## Phase 5: Dashboard and Enterprise :white_check_mark:

**Version: 0.5.0**

Added visibility and multi-tenant enterprise features.

- Dashboard backend APIs (overview, incidents, approval queue, compliance reports)
- Browser dashboard UI at `/dashboard`
- RBAC and tenant-isolation controls
- Multi-tenant policy-set storage
- Alert rule configuration and event log sink
- Dashboard scaffolding in `safeai init`

---

## Phase 6: Ecosystem and Community :white_check_mark:

**Version: 0.6.0**

Expanded extensibility and community infrastructure.

- Plugin loading system for custom detectors, adapters, and policy templates
- CrewAI and AutoGen adapters
- Structured payload and file-content scanning APIs
- Policy template catalog (finance, healthcare, support)
- `safeai templates list|show` CLI commands
- Contributor onboarding playbook
- Universal coding agent hook and setup system
- MCP server integration

---

## Future

The following items are planned but not yet scheduled:

| Initiative | Description |
|-----------|-------------|
| **Go-based proxy** | High-performance proxy implementation in Go for latency-sensitive deployments |
| **Cloud offering** | Managed SafeAI service with hosted policy management, audit storage, and dashboard |
| **Browser extension** | Client-side boundary enforcement for browser-based AI interfaces |
| **Policy marketplace** | Community-contributed policy template library with discovery and ratings |
| **Compliance packs** | Pre-built policy sets for SOC 2, HIPAA, GDPR, and PCI DSS |
| **Real-time alerting** | Webhook and Slack/Teams integrations for enforcement event notifications |
| **Agent observability** | Distributed tracing integration for boundary decisions across multi-agent systems |

!!! info "Want to influence the roadmap?"
    Open a [feature request issue](https://github.com/enendufrankc/safeai/issues/new) or start a [discussion](https://github.com/enendufrankc/safeai/discussions) to share your use case and priorities.
