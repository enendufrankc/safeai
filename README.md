<p align="center">
  <img src="public/image/image.png" alt="SafeAI Banner" width="100%" />
</p>

<h3 align="center">SECURE. INTELLIGENT. TRUSTED.</h3>

<p align="center">
  <a href="https://github.com/enendufrankc/safeai/actions/workflows/quality.yml"><img src="https://img.shields.io/github/actions/workflow/status/enendufrankc/safeai/quality.yml?label=build&style=flat-square" alt="Build"></a>
  <a href="https://github.com/enendufrankc/safeai/releases"><img src="https://img.shields.io/badge/release-v0.6.0-blue?style=flat-square" alt="Release"></a>
  <a href="https://pypi.org/project/safeai/"><img src="https://img.shields.io/pypi/v/safeai?style=flat-square&label=pypi" alt="PyPI"></a>
  <a href="https://opensource.org/licenses/Apache-2.0"><img src="https://img.shields.io/badge/license-Apache--2.0-green?style=flat-square" alt="License"></a>
  <a href="https://github.com/enendufrankc/safeai/stargazers"><img src="https://img.shields.io/github/stars/enendufrankc/safeai?style=flat-square" alt="Stars"></a>
</p>

<p align="center">
  <b>The runtime security layer for AI agents.</b><br>
  Block secrets. Redact PII. Enforce policies. Control tool calls. Require approvals.<br>
  Works with any model stack, framework, and deployment style.
</p>

---

## Table of Contents

- [What SafeAI Is](#what-safeai-is)
- [Capability Overview](#capability-overview)
- [Install](#install)
- [Quick Start (SDK)](#quick-start-sdk)
- [Scaffold a Full Config Project](#scaffold-a-full-config-project)
- [Run as a Proxy API](#run-as-a-proxy-api)
- [CLI Commands](#cli-commands)
- [Framework and Agent Integrations](#framework-and-agent-integrations)
- [Plugins and Policy Templates](#plugins-and-policy-templates)
- [Dashboard and Enterprise Operations](#dashboard-and-enterprise-operations)
- [Documentation Map](#documentation-map)
- [Contributing, Security, and Governance](#contributing-security-and-governance)
- [Local Development](#local-development)
- [License](#license)

## What SafeAI Is

SafeAI enforces policy at three runtime boundaries:

- `input`: before user or agent data reaches a model.
- `action`: before and after tool execution, and during agent-to-agent messaging.
- `output`: before model output is returned or forwarded.

That model keeps policy decisions close to execution, where incidents actually happen.

```
                    +----------------------------------+
 User / Agent  ---> |  INPUT BOUNDARY   (scan_input)  | ---> AI Provider
                    |  ACTION BOUNDARY  (intercept)   |      (OpenAI, Gemini,
 AI Provider   <--- |  OUTPUT BOUNDARY  (guard_output)| <---  Claude, etc.)
                    +----------------------------------+
                              SafeAI Runtime
```

Current status: Sprint 0 through Phase 6 complete, with `v0.6.0` release gate passed.

## Capability Overview

SafeAI is intentionally broad. This is the complete capability set currently implemented:

| Area | Capabilities |
|---|---|
| Detection and classification | Built-in detectors for secrets and personal data (`email`, `phone`, `ssn`, `credit_card`, `api_key`) with hierarchical tags |
| Policy engine | Priority-based first-match rules, YAML policies, schema validation, hot reload, fallback output templates |
| Input and output controls | Prompt scanning (`scan_input`), response guarding (`guard_output`), redaction/block/allow enforcement |
| Structured and file scanning | Nested payload scanning (`scan_structured_input`) and file scanning (`scan_file_input`) for JSON and text |
| Tool boundary enforcement | Request contract checks, response filtering, undeclared tool denial, per-field stripping |
| Agent identity | Agent registry, tool binding, clearance-tag enforcement |
| Agent messaging | Source/destination-aware, policy-gated agent-to-agent message interception |
| Approvals | `require_approval` runtime gate with persistent queue and explicit approve/deny flow |
| Secrets access | Capability-token TTL/scope/session binding, secret manager abstraction, Env/Vault/AWS backends |
| Memory security | Schema-enforced memory controller, encrypted handle storage, retention and purge workflow |
| Auditability | Append-only JSON logs, rich query filters (boundary/action/agent/tool/tag/session/time/metadata), context hashes and event IDs |
| Proxy runtime | Sidecar and gateway modes, upstream forwarding, health endpoint, policy reload endpoint |
| Observability | Prometheus-style metrics (`/v1/metrics`) with request/decision counters and latency buckets |
| Integrations | LangChain, CrewAI, AutoGen, Claude ADK, Google ADK, coding-agent hooks, MCP server |
| Extensibility | Plugin loader for detectors/adapters/templates, built-in policy template catalog (`finance`, `healthcare`, `support`) |
| Operations UI | Web dashboard (`/dashboard`) for incidents, approvals, compliance summaries, tenant/RBAC controls, alerts |

## Install

```bash
uv pip install safeai
```

Or with pip:

```bash
pip install safeai
```

Optional extras:

```bash
uv pip install "safeai[vault]"   # HashiCorp Vault backend
uv pip install "safeai[aws]"     # AWS Secrets Manager backend
uv pip install "safeai[mcp]"     # MCP server support
uv pip install "safeai[all]"     # Vault + AWS + MCP
uv pip install "safeai[dev]"     # local development tooling
```

## Quick Start (SDK)

For fast adoption with no config files:

```python
from safeai import SafeAI

ai = SafeAI.quickstart()
```

Then enforce both ends of the model call:

```python
# Input boundary
scan = ai.scan_input("Summarize this: token=sk-ABCDEF1234567890ABCDEF")
print(scan.decision.action, scan.decision.reason)

# Output boundary
guard = ai.guard_output("Contact alice@example.com")
print(guard.safe_output)
```

Structured payload example:

```python
payload = {"user": {"email": "alice@example.com"}, "note": "hello world"}
result = ai.scan_structured_input(payload, agent_id="default-agent")
print(result.decision.action)
print(result.filtered)
```

## Scaffold a Full Config Project

When you need full policy and runtime control:

```bash
safeai init --path .
```

This scaffolds:

- `safeai.yaml`
- `policies/default.yaml`
- `contracts/example.yaml`
- `schemas/memory.yaml`
- `agents/default.yaml`
- `plugins/example.py`
- `tenants/policy-sets.yaml`
- `alerts/default.yaml`

Use config mode via:

```python
from safeai import SafeAI

ai = SafeAI.from_config("safeai.yaml")
```

## Run as a Proxy API

Start the proxy:

```bash
safeai serve --mode sidecar --host 127.0.0.1 --port 8910 --config safeai.yaml
```

Health check:

```bash
curl http://127.0.0.1:8910/v1/health
```

Hello world scan:

```bash
curl -s -X POST http://127.0.0.1:8910/v1/scan/input \
  -H "content-type: application/json" \
  -d '{"text":"hello world","agent_id":"default-agent"}'
```

Core HTTP endpoints:

- `GET /v1/health`
- `GET /v1/metrics`
- `POST /v1/scan/input`
- `POST /v1/scan/structured`
- `POST /v1/scan/file`
- `POST /v1/guard/output`
- `POST /v1/intercept/tool`
- `POST /v1/intercept/agent-message`
- `POST /v1/memory/write`
- `POST /v1/memory/read`
- `POST /v1/memory/resolve-handle`
- `POST /v1/memory/purge-expired`
- `POST /v1/audit/query`
- `POST /v1/policies/reload`
- `GET /v1/plugins`
- `GET /v1/policies/templates`
- `GET /v1/policies/templates/{template_name}`
- `POST /v1/proxy/forward`
- `GET /dashboard`

## CLI Commands

Daily commands you will actually use:

```bash
safeai init --path .
safeai validate --config safeai.yaml
safeai scan --boundary input --input "hello world"
safeai logs --tail 20 --json-output
safeai serve --mode sidecar --port 8910

safeai approvals list --status pending
safeai approvals approve <request_id> --approver security-lead
safeai approvals deny <request_id> --approver security-lead --note "policy mismatch"

safeai templates list
safeai templates show --name healthcare --format yaml

safeai setup claude-code --config safeai.yaml --path .
safeai setup cursor --config safeai.yaml --path .
safeai setup generic --config safeai.yaml

safeai hook --config safeai.yaml
safeai mcp --config safeai.yaml
```

## Framework and Agent Integrations

Built-in adapters:

- LangChain
- CrewAI
- AutoGen
- Claude ADK
- Google ADK

Coding-agent integration:

- universal hook adapter (`safeai hook`)
- installer commands for Claude Code and Cursor (`safeai setup ...`)
- MCP server (`safeai mcp`) for MCP-compatible clients

Quick adapter example:

```python
from safeai import SafeAI
from safeai.middleware.langchain import wrap_langchain_tool

ai = SafeAI.from_config("safeai.yaml")
safe_tool = wrap_langchain_tool(ai, my_tool, agent_id="default-agent")
```

## Plugins and Policy Templates

Phase 6 added extensibility as first-class behavior.

Plugin model:

- load plugin modules from `plugins/*.py` (configurable in `safeai.yaml`)
- extend detector patterns
- register adapters
- contribute policy templates

Template catalog:

- built-in packs: `finance`, `healthcare`, `support`
- list with `safeai templates list`
- inspect with `safeai templates show --name <template>`
- proxy discovery endpoints via `/v1/policies/templates*`

Minimal plugin shape:

```python
def safeai_detectors():
    return [
        (r"my-custom-pattern", "custom.tag", "custom_detector"),
    ]

def safeai_adapters():
    return {
        "my-adapter": lambda safeai: object(),
    }

def safeai_policy_templates():
    return [
        {
            "name": "my-template",
            "template": {"version": "v1alpha1", "policies": []},
        }
    ]
```

## Dashboard and Enterprise Operations

SafeAI includes a dashboard surface for security operations:

- incidents and policy events
- approval queue workflow
- compliance report summaries
- tenant-scoped policy sets
- RBAC checks
- alert rule evaluation and alert logs

Run the proxy and open `/dashboard` in your browser.

## Documentation Map

Start here:

- Docs home: [`docs/index.md`](docs/index.md)
- Install: [`docs/getting-started/installation.md`](docs/getting-started/installation.md)
- Quickstart: [`docs/getting-started/quickstart.md`](docs/getting-started/quickstart.md)
- Configuration: [`docs/getting-started/configuration.md`](docs/getting-started/configuration.md)

Guides:

- Policy engine: [`docs/guides/policy-engine.md`](docs/guides/policy-engine.md)
- Tool contracts: [`docs/guides/tool-contracts.md`](docs/guides/tool-contracts.md)
- Agent identity: [`docs/guides/agent-identity.md`](docs/guides/agent-identity.md)
- Structured scanning: [`docs/guides/structured-scanning.md`](docs/guides/structured-scanning.md)
- Capability tokens: [`docs/guides/capability-tokens.md`](docs/guides/capability-tokens.md)
- Audit logging: [`docs/guides/audit-logging.md`](docs/guides/audit-logging.md)

Integrations:

- Integrations overview: [`docs/integrations/index.md`](docs/integrations/index.md)
- LangChain: [`docs/integrations/langchain.md`](docs/integrations/langchain.md)
- CrewAI: [`docs/integrations/crewai.md`](docs/integrations/crewai.md)
- AutoGen: [`docs/integrations/autogen.md`](docs/integrations/autogen.md)
- Claude ADK: [`docs/integrations/claude-adk.md`](docs/integrations/claude-adk.md)
- Google ADK: [`docs/integrations/google-adk.md`](docs/integrations/google-adk.md)
- Coding agents: [`docs/integrations/coding-agents.md`](docs/integrations/coding-agents.md)
- Proxy/sidecar: [`docs/integrations/proxy-sidecar.md`](docs/integrations/proxy-sidecar.md)
- Plugins: [`docs/integrations/plugins.md`](docs/integrations/plugins.md)

Reference:

- CLI reference: [`docs/cli/index.md`](docs/cli/index.md)
- API reference: [`docs/reference/safeai.md`](docs/reference/safeai.md)
- Changelog: [`docs/changelog.md`](docs/changelog.md)

Project and planning:

- Architecture: [`docs/project/architecture.md`](docs/project/architecture.md)
- Roadmap: [`docs/project/roadmap.md`](docs/project/roadmap.md)
- Security: [`docs/project/security.md`](docs/project/security.md)
- Governance: [`docs/project/governance.md`](docs/project/governance.md)
- Compatibility: [`docs/project/compatibility.md`](docs/project/compatibility.md)
- Delivery tracker: [`docs/brainstom/15-delivery-tracker.md`](docs/brainstom/15-delivery-tracker.md)

Notebooks:

- Notebook index: [`docs/notebooks/index.md`](docs/notebooks/index.md)
- Raw notebooks: [`notebook/`](notebook/)

## Contributing, Security, and Governance

Core project policies:

- Contributing guide: [`CONTRIBUTING.md`](CONTRIBUTING.md)
- Security policy: [`SECURITY.md`](SECURITY.md)
- Governance model: [`GOVERNANCE.md`](GOVERNANCE.md)
- Maintainer policy: [`MAINTAINERS.md`](MAINTAINERS.md)
- Code of conduct: [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md)
- Compatibility and semver contract: [`COMPATIBILITY.md`](COMPATIBILITY.md)

## Local Development

```bash
git clone https://github.com/enendufrankc/safeai.git
cd safeai
uv sync --extra dev --extra all
```

Or with pip:

```bash
pip install -e ".[dev,all]"
```

Quality gates used in CI:

```bash
uv run ruff check safeai tests
uv run mypy safeai
uv run python -m pytest tests/ -v
```

## License

SafeAI is licensed under [Apache 2.0](https://opensource.org/licenses/Apache-2.0).
