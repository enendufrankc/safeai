<!-- prettier-ignore -->
<div align="center">

<img src="https://raw.githubusercontent.com/enendufrankc/safeai/main/docs/assets/banner.png" alt="SafeAI Banner" width="100%" />

# SafeAI

*Runtime security layer for AI agents*

[![Build Status](https://img.shields.io/github/actions/workflow/status/enendufrankc/safeai/quality.yml?style=flat-square&label=Build)](https://github.com/enendufrankc/safeai/actions)
[![PyPI](https://img.shields.io/pypi/v/safeai-sdk?style=flat-square)](https://pypi.org/project/safeai-sdk/)
![Python](https://img.shields.io/badge/Python->=3.10-3776ab?style=flat-square&logo=python&logoColor=white)
[![Documentation](https://img.shields.io/badge/Documentation-00a3ee?style=flat-square)](https://enendufrankc.github.io/safeai/)
[![License](https://img.shields.io/badge/License-Apache--2.0-green?style=flat-square)](LICENSE)

[Overview](#overview) · [Quick Start](#quick-start) · [Features](#features) · [Integrations](#integrations) · [Documentation](#documentation)

</div>

Block secrets. Redact PII. Enforce policies. Control tool calls. Require approvals. Works with any model stack, framework, and deployment style.

## Overview

SafeAI enforces security policies at three runtime boundaries, keeping decisions close to execution where incidents actually happen:

```
                    ┌──────────────────────────────────┐
 User / Agent  ───▶ │  INPUT BOUNDARY   (scan_input)   │ ───▶ AI Provider
                    │  ACTION BOUNDARY  (intercept)    │      (OpenAI, Gemini,
 AI Provider   ◀─── │  OUTPUT BOUNDARY  (guard_output) │ ◀───  Claude, etc.)
                    └──────────────────────────────────┘
                               SafeAI Runtime
```

- **Input** — scans prompts and payloads before they reach the model
- **Action** — intercepts tool calls and agent-to-agent messages
- **Output** — guards model responses before they are returned

Every decision is logged to an immutable audit trail.

> [!NOTE]
> SafeAI focuses on runtime policy enforcement. It does not replace model safety training, provide content moderation, or act as a network firewall. See the full [documentation](https://enendufrankc.github.io/safeai/) for details.

## Quick Start

### Install

```bash
pip install safeai-sdk
```

Optional extras:

```bash
pip install "safeai-sdk[vault]"   # HashiCorp Vault backend
pip install "safeai-sdk[aws]"     # AWS Secrets Manager backend
pip install "safeai-sdk[mcp]"     # MCP server support
pip install "safeai-sdk[all]"     # Everything
```

### Use the SDK

```python
from safeai import SafeAI

ai = SafeAI.quickstart()

# Input boundary — detect and block secrets
scan = ai.scan_input("Summarize this: token=sk-ABCDEF1234567890ABCDEF")
print(scan.decision.action)  # "block"

# Output boundary — redact PII from responses
guard = ai.guard_output("Contact alice@example.com for details.")
print(guard.safe_output)     # "Contact [REDACTED] for details."
```

### Scaffold a project

For full policy and runtime control, scaffold a config directory:

```bash
safeai init --path .
```

This generates `safeai.yaml`, default policies, contracts, agent identities, plugins, and alert rules. Then load from config:

```python
ai = SafeAI.from_config("safeai.yaml")
```

### Run as a proxy

```bash
safeai serve --mode sidecar --host 127.0.0.1 --port 8910 --config safeai.yaml
```

```bash
# Health check
curl http://127.0.0.1:8910/v1/health

# Scan input
curl -s -X POST http://127.0.0.1:8910/v1/scan/input \
  -H "content-type: application/json" \
  -d '{"text":"hello world","agent_id":"default-agent"}'
```

## Features

| Area | What it does |
|---|---|
| **Detection** | Built-in detectors for secrets and PII (`email`, `phone`, `ssn`, `credit_card`, `api_key`) with hierarchical tags |
| **Policy engine** | Priority-based first-match YAML rules with schema validation and hot reload |
| **Input / Output controls** | Prompt scanning, response guarding, redaction, blocking, and allow-listing |
| **Tool contracts** | Request validation, response filtering, undeclared tool denial, per-field stripping |
| **Agent identity** | Agent registry with tool bindings and clearance-tag enforcement |
| **Approvals** | Human-in-the-loop `require_approval` gate with persistent queue and approve/deny flow |
| **Secrets management** | Capability-token scoping with TTL/session binding; Env, Vault, and AWS backends |
| **Memory security** | Schema-enforced encrypted storage with retention and auto-purge |
| **Audit trail** | Append-only JSON logs with rich filters (boundary, agent, tool, session, time) |
| **Proxy runtime** | Sidecar and gateway modes with upstream forwarding and policy reload |
| **Skills system** | Installable packages for GDPR, HIPAA, PCI-DSS, prompt injection, and more |
| **Dashboard** | Web UI for incidents, approvals, compliance summaries, and tenant/RBAC controls |
| **Alerting** | File, webhook, and Slack channels with Prometheus-style metrics at `/v1/metrics` |
| **Intelligence layer** | AI advisory agents for auto-config, policy recommendations, incident explanation, and compliance mapping |

<details>
<summary><strong>Detailed request flow</strong></summary>

```
  ┌─────────────┐
  │  Your App   │
  │  or Agent   │
  └──────┬──────┘
         │
         ▼
  ┌──────────────────────────────────────────────────────────┐
  │                    INPUT BOUNDARY                        │
  │  scan_input() / scan_structured_input() / scan_file()   │
  │                                                          │
  │  Detectors ──▶ Policy Engine ──▶ Decision                │
  │  + Contracts · Identities · Approvals · Secrets          │
  └──────────────────────────┬───────────────────────────────┘
                             │
                             ▼
  ┌──────────────────────────────────────────────────────────┐
  │                   ACTION BOUNDARY                        │
  │  intercept_tool_request() / intercept_agent_message()    │
  │  + Capability tokens (scoped permissions per tool call)  │
  └──────────────────────────┬───────────────────────────────┘
                             │
                             ▼
                      [ LLM / Tool ]
                             │
                             ▼
  ┌──────────────────────────────────────────────────────────┐
  │                   OUTPUT BOUNDARY                        │
  │  guard_output() / intercept_tool_response()              │
  │  + Fallback templates (safe replacement text)            │
  └──────────────────────────┬───────────────────────────────┘
                             │
                             ▼
                       Audit Trail
```

</details>

## Integrations

SafeAI provides built-in adapters for popular AI frameworks and coding agents:

| Type | Supported |
|---|---|
| **Frameworks** | LangChain, CrewAI, AutoGen, Claude ADK, Google ADK |
| **Coding agents** | Claude Code, Cursor (via `safeai setup`) |
| **IDE / MCP** | Any MCP-compatible client (via `safeai mcp`) |
| **Proxy** | Sidecar and gateway modes for any HTTP-based stack |

```python
from safeai import SafeAI
from safeai.middleware.langchain import wrap_langchain_tool

ai = SafeAI.from_config("safeai.yaml")
safe_tool = wrap_langchain_tool(ai, my_tool, agent_id="default-agent")
```

## CLI Reference

```bash
safeai init --path .                          # Scaffold config and policies
safeai validate --config safeai.yaml          # Validate configuration
safeai scan --boundary input --input "text"   # Scan from the command line
safeai serve --mode sidecar --port 8910       # Start the proxy server
safeai setup claude-code --config safeai.yaml # Install into Claude Code
safeai setup cursor --config safeai.yaml      # Install into Cursor
safeai mcp --config safeai.yaml               # Start MCP server
safeai hook --config safeai.yaml              # Universal hook adapter

safeai approvals list --status pending        # Manage approvals
safeai templates list                         # Browse policy templates
safeai intelligence auto-config --path .      # AI-powered auto-configuration
safeai skills add prompt-injection-shield     # Install a skill package
safeai observe agents                         # Agent observability
safeai alerts add --channel slack --url ...   # Configure alerting
```

> [!TIP]
> Run `safeai --help` or see the full [CLI reference](https://enendufrankc.github.io/safeai/cli/) for all commands and options.

## Plugins

Extend SafeAI with custom detectors, adapters, and policy templates by dropping modules into `plugins/`:

```python
def safeai_detectors():
    return [(r"my-pattern", "custom.tag", "my_detector")]

def safeai_policy_templates():
    return [{"name": "my-template", "template": {"version": "v1alpha1", "policies": []}}]
```

Built-in template packs: `finance`, `healthcare`, `support`.

## Documentation

| Resource | Link |
|---|---|
| Getting started | [Installation](https://enendufrankc.github.io/safeai/getting-started/installation/) · [Quickstart](https://enendufrankc.github.io/safeai/getting-started/quickstart/) · [Configuration](https://enendufrankc.github.io/safeai/getting-started/configuration/) |
| Guides | [Policy Engine](https://enendufrankc.github.io/safeai/guides/policy-engine/) · [Tool Contracts](https://enendufrankc.github.io/safeai/guides/tool-contracts/) · [Agent Identity](https://enendufrankc.github.io/safeai/guides/agent-identity/) · [Audit Logging](https://enendufrankc.github.io/safeai/guides/audit-logging/) |
| Integrations | [LangChain](https://enendufrankc.github.io/safeai/integrations/langchain/) · [CrewAI](https://enendufrankc.github.io/safeai/integrations/crewai/) · [AutoGen](https://enendufrankc.github.io/safeai/integrations/autogen/) · [Coding Agents](https://enendufrankc.github.io/safeai/integrations/coding-agents/) |
| Reference | [CLI](https://enendufrankc.github.io/safeai/cli/) · [API](https://enendufrankc.github.io/safeai/reference/safeai/) · [Architecture](https://enendufrankc.github.io/safeai/project/architecture/) |

## Local Development

```bash
git clone https://github.com/enendufrankc/safeai.git
cd safeai
pip install -e ".[dev,all]"
```

Run the quality gates:

```bash
ruff check safeai tests        # Lint
mypy safeai                    # Type check
python -m pytest tests/ -v     # Test
```
