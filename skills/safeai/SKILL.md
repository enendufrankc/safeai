---
name: safeai
description: >
  Complete SafeAI zero-trust security layer — everything in one install.
  Activates extended secrets detection (40+ patterns), prompt injection
  shielding, LangChain adapter, and a universal compliance policy set
  (HIPAA + PCI-DSS + GDPR baselines). Runs safeai init, applies intelligence
  auto-config, installs agent hooks, and starts the local observability
  dashboard. Use when the user wants to add SafeAI to a project, secure an
  AI agent, set up zero-trust guardrails, protect tool calls from secrets
  or prompt injection, enforce compliance policies, or deploy SafeAI to any
  project with Claude Code, Cursor, MCP, or generic agents.
tier: stable
owner: SafeAI Contributors
domain: security
functional-area: ai-safety
---

# SafeAI — Complete Setup

Deploys SafeAI as a zero-trust security layer in any project. One script handles everything.

## Quick Start

```bash
python scripts/setup.py --project-path /path/to/project
```

With observability + Claude Code + Anthropic intelligence:
```bash
python scripts/setup.py --project-path . \
  --agent claude-code \
  --observability \
  --provider anthropic
```

## What Gets Installed

| Step | What happens |
|------|-------------|
| 1 | `pip install safeai-sdk[mcp]` if not present |
| 2 | `safeai init` — scaffold `safeai.yaml`, `policies/`, `contracts/`, `agents/` |
| 3 | `plugins/safeai_complete.py` — all detectors + adapters activated |
| 4 | `policies/universal.yaml` — prompt injection, secrets, PHI, PII, PCI-DSS |
| 5 | Intelligence backend configured in `safeai.yaml` |
| 6 | `safeai intelligence auto-config --apply` — project-specific policies generated |
| 7 | Agent hooks (Claude Code / Cursor) or MCP server configured |
| 8 | Observability server started (optional) |

## What the Universal Policy Covers

| Threat | Boundary | Action |
|--------|----------|--------|
| Prompt injection / jailbreak | input, output | block |
| API keys, tokens, private keys | input, action, output | block |
| DB connection strings | input, action, output | block |
| Protected health info (PHI) | input, action | block |
| Cardholder data (PAN, CVV) | input, action | block |
| PII in responses | output | redact |

## Options

```
--project-path PATH     Target project directory (default: cwd)
--agent TYPE            claude-code | cursor | generic (auto-detected)
--binding TYPE          hooks | mcp (default: hooks)
--provider PROVIDER     openai | anthropic | ollama (default: openai)
--model MODEL           LLM model for intelligence
--api-key-env VAR       Env var holding API key
--observability         Start dashboard at localhost:8910
--obs-port PORT         Dashboard port (default: 8910)
--slack-webhook URL     Slack alerts
--no-intelligence       Skip auto-config
--dry-run               Preview without executing
```

## Observability Endpoints

| Endpoint | Purpose |
|----------|---------|
| `http://localhost:8910/dashboard` | Security operations dashboard |
| `GET /v1/metrics` | Prometheus metrics |
| `GET /v1/health` | Health + agent counts |
| `POST /v1/audit/query` | Queryable audit log |

## References

- `references/integration-patterns.md` — SDK, LangChain, CrewAI, AutoGen, Claude ADK snippets
- `references/policy-contracts.md` — Policy and contract authoring guide
- `references/observability.md` — Full monitoring and alerting reference
