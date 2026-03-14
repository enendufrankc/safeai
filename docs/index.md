---
description: "SafeAI — the runtime security layer for AI agents. Block secrets, redact PII, enforce policies, and control tools across any AI provider."
hide:
  - navigation
  - toc
---

<div class="hero" markdown>

<div class="hero-shell">
<pre class="hero-ascii" aria-hidden="true">███████  █████  ███████ ███████  █████  ██
██      ██   ██ ██      ██      ██   ██ ██
███████ ███████ █████   █████   ███████ ██
     ██ ██   ██ ██      ██      ██   ██ ██
███████ ██   ██ ██      ███████ ██   ██ ██</pre>
</div>

<p class="eyebrow">The runtime security layer for AI agents</p>

# SafeAI

<p class="tagline">Block secrets. Redact PII. Enforce policies. Control tools. Approve actions.<br>
Secure the full path from prompt to tool call to model output across any provider, framework, and deployment surface.</p>

<div class="hero-command">
<code>$ uv pip install safeai &amp;&amp; python -c "from safeai import SafeAI; SafeAI.quickstart()"</code>
</div>

</div>

<div class="badges" markdown>

<img src="https://img.shields.io/github/actions/workflow/status/enendufrankc/safeai/quality.yml?label=build&style=flat-square" alt="Build" width="90" height="20" loading="eager">
<img src="https://img.shields.io/badge/release-v0.8.2-blue?style=flat-square" alt="Release" width="100" height="20" loading="eager">
<img src="https://img.shields.io/pypi/v/safeai?style=flat-square&label=pypi" alt="PyPI" width="80" height="20" loading="eager">
<img src="https://img.shields.io/badge/license-Apache--2.0-green?style=flat-square" alt="License" width="120" height="20" loading="eager">
<img src="https://img.shields.io/github/stars/enendufrankc/safeai?style=flat-square" alt="Stars" width="70" height="20" loading="eager">

</div>

<div class="section-header" markdown>
<p class="section-kicker">Quick Start</p>
<h2>Two Lines. That's It.</h2>
</div>

<div class="quickstart-block" markdown>

```python
from safeai import SafeAI

ai = SafeAI.quickstart()
```

Now wrap any AI call:

```python
# Scan prompts before they leave
scan = ai.scan_input("Summarize this: API_KEY=sk-ABCDEF1234567890")
# => BLOCKED: Secrets must never cross any boundary.

# Guard responses before you use them
guard = ai.guard_output("Contact alice@example.com or call 555-123-4567")
print(guard.safe_output)
# => Contact [REDACTED] or call [REDACTED]
```

</div>

<div class="cta" markdown>

[Get Started](getting-started/installation.md){ .md-button .md-button--primary }
[View on GitHub](https://github.com/enendufrankc/safeai){ .md-button }
[Auto-Configure with Intelligence Layer](guides/intelligence.md){ .md-button }

</div>

---

<div class="section-header" markdown>
<p class="section-kicker">Capabilities</p>
<h2>Everything You Need to Secure AI Agents</h2>
</div>

<div class="feature-grid" markdown>

<div class="feature-card" markdown>
### :material-brain: Intelligence Layer
5 AI advisory agents for auto-config, policy recommendations, incident explanation, compliance mapping, and integration code generation. BYOM -- bring your own model.
</div>

<div class="feature-card" markdown>
### :material-shield-lock: Secret Detection
API keys, tokens, and credentials are blocked before they reach any LLM.
</div>

<div class="feature-card" markdown>
### :material-account-lock: PII Protection
Emails, phone numbers, SSNs, and credit cards are redacted or blocked automatically.
</div>

<div class="feature-card" markdown>
### :material-file-document-check: Policy Engine
Priority-based rules with tag hierarchies, hot reload, and custom rules in YAML.
</div>

<div class="feature-card" markdown>
### :material-handshake: Tool Contracts
Declare what each tool accepts and emits — undeclared tools are denied.
</div>

<div class="feature-card" markdown>
### :material-badge-account: Agent Identity
Bind agents to specific tools and clearance levels for fine-grained control.
</div>

<div class="feature-card" markdown>
### :material-check-decagram: Approval Workflows
Human-in-the-loop approval for high-risk actions with TTL and deduplication.
</div>

<div class="feature-card" markdown>
### :material-lock: Encrypted Memory
Schema-enforced agent memory with field-level encryption and auto-expiry.
</div>

<div class="feature-card" markdown>
### :material-key-chain: Capability Tokens
Scoped, time-limited tokens for secret access — agents never see raw credentials.
</div>

<div class="feature-card" markdown>
### :material-clipboard-text-clock: Audit Logging
Every decision logged with context hash, filterable by agent, action, tag, and time.
</div>

<div class="feature-card" markdown>
### :material-file-search: Structured Scanning
Scan nested JSON payloads and files, not just flat strings.
</div>

<div class="feature-card" markdown>
### :material-message-lock: Agent Messaging
Policy-gated agent-to-agent communication across trust boundaries.
</div>

<div class="feature-card" markdown>
### :material-alert-octagon: Dangerous Commands
Block `rm -rf /`, `DROP TABLE`, fork bombs, pipe-to-shell, and force pushes.
</div>

</div>

---

<div class="section-header" markdown>
<p class="section-kicker">Architecture</p>
<h2>How SafeAI Works</h2>
</div>

```text
  Users / Apps / Agents
            │
            ▼
  ┌──────────────────────┐
  │   Input Boundary     │  `scan_input`, `scan_structured_input`, `scan_file_input`
  │   Detect + classify  │  secrets, PII, policy tags, nested payloads, files
  └──────────┬───────────┘
             │
             ▼
  ┌──────────────────────┐
  │   Core Policy Plane  │  policy engine, classifier, audit, config loader
  │   Deterministic      │  hot reload, rule priorities, boundary-specific rules
  └───────┬───────┬──────┘
          │       │
          │       └──────────────┐
          ▼                      ▼
  ┌──────────────────────┐  ┌──────────────────────┐
  │  Action Boundary     │  │  Output Boundary     │
  │  intercept tool/API  │  │  `guard_output`      │
  │  calls + messages    │  │  redact / block /    │
  │  contracts, identity │  │  fallback response   │
  │  approvals, secrets  │  └──────────┬───────────┘
  └──────────┬───────────┘             │
             │                         ▼
             ▼                  Users / Apps / Agents
   Tools / APIs / Agent Peers

  Deployment surfaces: Python SDK, CLI, HTTP proxy/sidecar, gateway proxy, MCP server
  Optional control planes: dashboard, alerts, plugins, templates, intelligence advisors
```

SafeAI enforces security at the boundaries where data enters, exits, and crosses trust lines. Every prompt, tool call, agent message, file payload, and model response is evaluated before it moves to the next system.

### End-to-End Flow

1. Input enters through the SDK, proxy, CLI, or framework adapter.
2. Detectors classify secrets, PII, and custom policy tags.
3. The policy engine evaluates boundary-specific YAML rules and returns `allow`, `redact`, `block`, or `require_approval`.
4. Action requests are checked against tool contracts, agent identity bindings, secret access controls, and approval workflows.
5. Output is guarded before it reaches users, downstream tools, or other agents.
6. Every decision is written to audit logs and exposed to metrics, dashboard views, and intelligence workflows.

### Core Runtime Components

| Layer | What it does | Key modules |
|:---|:---|:---|
| Detection and classification | Finds secrets, PII, and custom matches in text, files, and structured payloads | `safeai/core/scanner.py`, `safeai/core/structured.py`, `safeai/core/classifier.py`, `safeai/detectors/*` |
| Policy enforcement | Applies deterministic boundary rules with priorities, tag matching, and hot reload | `safeai/core/policy.py`, `safeai/config/loader.py` |
| Action control | Governs tool calls, agent messaging, contracts, identity, and approvals | `safeai/core/interceptor.py`, `safeai/core/contracts.py`, `safeai/core/identity.py`, `safeai/core/approval.py` |
| Output protection | Redacts or blocks unsafe model output before release | `safeai/core/guard.py` |
| Audit and observability | Records every decision and exposes query/metrics surfaces | `safeai/core/audit.py`, `safeai/proxy/metrics.py`, `safeai/dashboard/*` |
| Secure state and secrets | Protects memory, secret access, and capability-token based retrieval | `safeai/core/memory.py`, `safeai/secrets/manager.py`, `safeai/secrets/capability.py` |
| Integration surfaces | Embeds SafeAI into frameworks, coding agents, APIs, and infrastructure | `safeai/middleware/*`, `safeai/proxy/*`, `safeai/mcp/server.py`, `safeai/agents/installers/*` |
| Advisory intelligence | Generates recommendations and staged configs without entering the enforcement path | `safeai/intelligence/*` |

### Deployment Model

SafeAI is designed so the same enforcement model can run in multiple places:

- In-process via the Python SDK for direct application integration.
- As a CLI and hook layer for local coding agents and developer workflows.
- As an HTTP sidecar or gateway proxy for language-agnostic enforcement.
- As an MCP server for MCP-compatible agent clients.
- With dashboard, alerts, templates, plugins, and intelligence agents layered on top for operations at scale.

### Design Guarantees

- Deterministic enforcement at runtime. AI does not make final security decisions.
- Policy-as-data with versioned YAML instead of hidden logic in application code.
- Framework-agnostic core with thin adapters around it.
- Full auditability across input, action, and output boundaries.
- Human approval for high-risk operations without exposing raw protected data to AI systems.

[Full architecture documentation :material-arrow-right:](project/architecture.md){ .architecture-link }

---

<div class="section-header" markdown>
<p class="section-kicker">Roadmap</p>
<h2>Platform Evolution</h2>
</div>

SafeAI has been built in phases, with each phase expanding the runtime while preserving the same boundary model.

### Delivered

| Phase | Status | Major outcomes |
|:---|:---|:---|
| Phase 1: Foundation | Complete | Core SDK, detectors, policy engine, output guard, audit logging, memory, validation CLI |
| Phase 2: Tool Control | Complete | Tool contracts, action-boundary interception, agent identity, richer audit context, LangChain adapter |
| Phase 3: Secrets and Approvals | Complete | Approval workflows, secret backends, encrypted handle resolution, Claude ADK and Google ADK support |
| Phase 4: Proxy and Scale | Complete | HTTP proxy, forwarding/gateway modes, metrics, production API surface |
| Phase 5: Dashboard and Enterprise | Complete | Dashboard APIs/UI, RBAC, tenant isolation, alerting scaffolds, enterprise operations model |
| Phase 6: Ecosystem and Community | Complete | Plugin system, CrewAI and AutoGen adapters, structured/file scanning, templates, coding-agent hooks, MCP |
| Phase 7: Intelligence Layer | Complete | BYOM intelligence backend, metadata sanitization, 5 advisory agents, staging workflow, proxy/dashboard intelligence endpoints |
| Phase 8: Skills and Ecosystem Hardening | Complete | Skills system with 8 packages, alerts CLI, observe CLI, SPDX compliance, JSON schemas, interactive init, PyPI publishing |

### Current Platform Scope

The project now covers the full agent security stack:

- Input scanning for text, files, and nested structured payloads.
- Action control for tool calls, API requests, and agent-to-agent messaging.
- Output redaction and blocking before release.
- Policy templates, plugins, secrets, encrypted memory, approvals, and audit trails.
- SDK, CLI, proxy, dashboard, coding-agent hooks, and MCP deployment surfaces.
- Intelligence workflows for auto-configuration, policy recommendation, incident explanation, compliance mapping, and integration generation.

### Planned Next

| Initiative | Direction |
|:---|:---|
| Go-based proxy | Lower-latency proxy runtime for high-throughput deployments |
| Cloud offering | Hosted policy management, audit storage, and dashboard operations |
| Browser extension | Client-side boundary enforcement for browser-based AI tools |
| Agent observability | Distributed tracing and richer cross-agent runtime visibility |

[Full roadmap :material-arrow-right:](project/roadmap.md){ .architecture-link }

---

## See It in Action

!!! example "Securing OpenClaw with SafeAI"
    A complete walkthrough running SafeAI as a sidecar alongside [OpenClaw](https://openclaw.ai/) — an open-source personal AI assistant with shell access, file system permissions, and messaging across WhatsApp, Telegram, Slack, Discord, and more.

    Covers: secret detection, PII protection, tool contracts, dangerous command blocking, structured payload scanning, audit logging, and proxy/sidecar deployment — all without modifying OpenClaw's source code.

    **[Read the full use case :material-arrow-right:](examples/openclaw.md)**

---

## Works With Everything

<div class="compat-table" markdown>

| AI Providers | Agent Frameworks | Coding Agents | Deployment |
|:---|:---|:---|:---|
| OpenAI | LangChain | Claude Code | Python SDK |
| Google Gemini | CrewAI | Cursor | REST API (sidecar) |
| Anthropic Claude | AutoGen | Copilot | Gateway proxy |
| Ollama | Google ADK | Any MCP client | MCP server |
| Any HTTP API | Claude ADK | | CLI hooks |

</div>

---

## Install SafeAI

=== "uv (recommended)"

    ```bash
    uv pip install safeai
    ```

=== "pip"

    ```bash
    pip install safeai
    ```

With extras:

=== "uv (recommended)"

    ```bash
    uv pip install "safeai[vault]"   # HashiCorp Vault backend
    uv pip install "safeai[aws]"     # AWS Secrets Manager backend
    uv pip install "safeai[mcp]"     # MCP server for coding agents
    uv pip install "safeai[all]"     # Everything
    ```

=== "pip"

    ```bash
    pip install safeai[vault]       # HashiCorp Vault backend
    pip install safeai[aws]         # AWS Secrets Manager backend
    pip install safeai[mcp]         # MCP server for coding agents
    pip install safeai[all]         # Everything
    ```

<div class="cta" markdown>

[Get Started :material-arrow-right:](getting-started/installation.md){ .md-button .md-button--primary }
[Read the Guides](guides/secret-detection.md){ .md-button }

</div>
