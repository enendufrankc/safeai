<p align="center">
  <img src="public/image/image.png" alt="SafeAI Banner" width="100%" />
</p>

<h3 align="center">SECURE. INTELLIGENT. TRUSTED.</h3>

<p align="center">
  <a href="https://github.com/enendufrankc/safeai/actions/workflows/quality.yml"><img src="https://img.shields.io/github/actions/workflow/status/enendufrankc/safeai/quality.yml?label=build&style=flat-square" alt="Build"></a>
  <a href="https://github.com/enendufrankc/safeai/releases"><img src="https://img.shields.io/badge/release-v0.6.0-blue?style=flat-square" alt="Release"></a>
  <a href="https://pypi.org/project/safeai/"><img src="https://img.shields.io/pypi/v/safeai?style=flat-square&label=pypi" alt="PyPI"></a>
  <a href="https://github.com/enendufrankc/safeai/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-Apache--2.0-green?style=flat-square" alt="License"></a>
  <a href="https://github.com/enendufrankc/safeai/stargazers"><img src="https://img.shields.io/github/stars/enendufrankc/safeai?style=flat-square" alt="Stars"></a>
</p>

<p align="center">
  <b>The runtime security layer for AI agents.</b><br>
  Block secrets. Redact PII. Enforce policies. Control tools. Approve actions.<br>
  Works with <b>any</b> AI provider &mdash; OpenAI, Gemini, Claude, LangChain, CrewAI, and more.
</p>

---

## Two lines. That's it.

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

That's the full setup. No config files, no YAML, no infrastructure. Install and go.

## Install

```bash
pip install safeai
```

Or with extras:

```bash
pip install safeai[vault]       # HashiCorp Vault backend
pip install safeai[aws]         # AWS Secrets Manager backend
pip install safeai[mcp]         # MCP server for coding agents
pip install safeai[all]         # Everything
```

## Why SafeAI?

AI agents are powerful. They call APIs, execute code, read databases, send emails. Without guardrails, a single hallucination or prompt injection can leak credentials, expose customer data, or run destructive commands.

SafeAI sits between your agent and the world:

```
                    ┌──────────────────────────────────┐
  User / Agent  ──> │  INPUT BOUNDARY   (scan_input)   │ ──> AI Provider
                    │  ACTION BOUNDARY  (intercept)     │     (OpenAI, Gemini,
  AI Provider   <── │  OUTPUT BOUNDARY  (guard_output)  │ <──  Claude, etc.)
                    └──────────────────────────────────┘
                              SafeAI Runtime
```

**Every prompt, every tool call, every response** passes through policy-driven enforcement before it goes anywhere.

## What it does

| Capability | What happens |
|:---|:---|
| **Secret detection** | API keys, tokens, and credentials are blocked before they reach any LLM |
| **PII protection** | Emails, phone numbers, SSNs, credit cards are redacted or blocked |
| **Policy engine** | Priority-based rules with tag hierarchies, hot reload, and custom rules |
| **Tool contracts** | Declare what each tool accepts and emits &mdash; undeclared tools are denied |
| **Agent identity** | Bind agents to specific tools and clearance levels |
| **Field filtering** | Strip request/response fields that fall outside a tool's contract |
| **Approval gates** | Human-in-the-loop approval for high-risk actions with TTL and dedup |
| **Encrypted memory** | Schema-enforced agent memory with field-level encryption and auto-expiry |
| **Capability tokens** | Scoped, time-limited tokens for secret access |
| **Audit logging** | Every decision logged with context hash, filterable by agent/action/tag/time |
| **Structured scanning** | Scan nested JSON payloads and files, not just strings |
| **Agent messaging** | Policy-gated agent-to-agent communication |
| **Dangerous command detection** | Block `rm -rf /`, `DROP TABLE`, fork bombs, pipe-to-shell, force pushes |

## Works with everything

SafeAI is framework-agnostic. Use it with any AI provider or agent framework:

<table>
  <tr>
    <td align="center"><b>AI Providers</b></td>
    <td align="center"><b>Agent Frameworks</b></td>
    <td align="center"><b>Coding Agents</b></td>
    <td align="center"><b>Deployment</b></td>
  </tr>
  <tr>
    <td>
      OpenAI<br>
      Google Gemini<br>
      Anthropic Claude<br>
      Ollama<br>
      Any HTTP API
    </td>
    <td>
      LangChain<br>
      CrewAI<br>
      AutoGen<br>
      Google ADK<br>
      Claude ADK
    </td>
    <td>
      Claude Code<br>
      Cursor<br>
      Copilot<br>
      Any MCP client
    </td>
    <td>
      Python SDK<br>
      REST API (sidecar)<br>
      Gateway proxy<br>
      MCP server<br>
      CLI hooks
    </td>
  </tr>
</table>

### SDK adapters (3 lines)

```python
from safeai.middleware.langchain import wrap_langchain_tool

safe_tool = wrap_langchain_tool(safeai, my_tool, agent_id="agent-1")
```

### Coding agent hooks (1 command)

```bash
safeai setup claude-code   # writes .claude/settings.json hooks automatically
safeai setup cursor         # writes .cursor/rules hooks
```

### REST API sidecar

```bash
safeai serve --mode sidecar --port 8000
```

```bash
curl -X POST http://localhost:8000/v1/scan/input \
  -d '{"text": "Use key sk-ABCDEF1234567890"}'
# => {"decision": {"action": "block", "reason": "Secrets must never cross any boundary."}}
```

## Configure what gets enforced

`quickstart()` accepts keyword arguments to control protections:

```python
# Block PII entirely instead of redacting
strict = SafeAI.quickstart(block_pii=True, redact_pii=False)

# Secrets only, ignore PII
minimal = SafeAI.quickstart(redact_pii=False)

# Add custom rules
custom = SafeAI.quickstart(custom_rules=[
    {
        "name": "block-financial-input",
        "boundary": ["input"],
        "priority": 15,
        "condition": {"data_tags": ["personal.financial"]},
        "action": "block",
        "reason": "Financial data cannot be sent to the model.",
    },
])
```

For full control, use `safeai init` to scaffold a config directory with YAML policies, tool contracts, agent identities, memory schemas, and more.

## Real-world example: Gemini with SafeAI

```python
from safeai import SafeAI
from google import genai

ai = SafeAI.quickstart()
client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

def safe_generate(prompt: str) -> str:
    # 1. Check the prompt before sending
    scan = ai.scan_input(prompt)
    if scan.decision.action == "block":
        return f"BLOCKED: {scan.decision.reason}"

    # 2. Call Gemini
    response = client.models.generate_content(
        model="gemini-2.0-flash", contents=prompt
    )

    # 3. Guard the response before returning
    guard = ai.guard_output(response.text)
    return guard.safe_output  # PII redacted, secrets stripped

answer = safe_generate("Explain what an API key is in one sentence.")
```

## Interactive notebooks

Explore every capability hands-on in the [`notebook/`](notebook/) directory:

| Notebook | What it covers |
|:---|:---|
| [`api_call_test`](notebook/api_call_test.ipynb) | Zero-config quickstart + real Gemini API integration |
| [`structured_scanning`](notebook/structured_scanning.ipynb) | Nested JSON payload and file scanning |
| [`policy_engine`](notebook/policy_engine.ipynb) | Rules, priorities, tag hierarchies, hot reload |
| [`memory_controller`](notebook/memory_controller.ipynb) | Encrypted agent memory with schemas and auto-expiry |
| [`tool_interception`](notebook/tool_interception.ipynb) | Tool contracts, agent identity, field-level filtering |
| [`approval_workflow`](notebook/approval_workflow.ipynb) | Human-in-the-loop approval gates |
| [`audit_logging`](notebook/audit_logging.ipynb) | Full decision trail with query filters |
| [`agent_messaging`](notebook/agent_messaging.ipynb) | Agent-to-agent message interception |
| [`capability_tokens`](notebook/capability_tokens.ipynb) | Scoped, time-limited secret access tokens |
| [`hook_adapter`](notebook/hook_adapter.ipynb) | Universal hook adapter and agent profiles |
| [`proxy_server`](notebook/proxy_server.ipynb) | REST API sidecar with TestClient |

## Architecture

```
safeai/
├── api.py                  # SafeAI SDK entry point (quickstart, from_config)
├── core/
│   ├── policy.py           # Priority-based policy engine with hot reload
│   ├── interceptor.py      # Action boundary: contracts + identity + filtering
│   ├── audit.py            # Append-only audit log with rich queries
│   ├── memory.py           # Schema-enforced encrypted memory controller
│   ├── approval.py         # Human-in-the-loop approval workflow
│   ├── contracts.py        # Tool contract parser and registry
│   ├── identity.py         # Agent identity and clearance enforcement
│   └── structured.py       # Nested payload and file scanning
├── middleware/              # Framework adapters (LangChain, CrewAI, AutoGen, ADK)
├── proxy/                  # HTTP sidecar/gateway server with Prometheus metrics
├── secrets/                # Capability-token gated secret resolution (Env, Vault, AWS)
├── agents/                 # Agent profiles and hook installers
├── mcp/                    # MCP server for coding agent integration
├── dashboard/              # Enterprise dashboard with RBAC, alerts, compliance
├── plugins/                # Plugin system for custom detectors and adapters
├── templates/              # Policy template catalog (healthcare, finance, support)
└── cli/                    # CLI: init, scan, validate, logs, serve, hook, setup
```

## Policy system

SafeAI uses a **priority-based first-match** policy engine. Rules are evaluated in priority order (lowest number wins). The first matching rule determines the action.

```yaml
# safeai/policies/default.yaml
policies:
  - name: block-secrets
    boundary: [input, output, action]
    priority: 10
    condition:
      data_tags: [secret]
    action: block
    reason: Secrets must never cross any boundary.

  - name: redact-pii-output
    boundary: [output]
    priority: 20
    condition:
      data_tags: [personal.pii]
    action: redact
    reason: PII must be redacted before leaving the system.

  - name: require-approval-destructive
    boundary: [action]
    priority: 25
    condition:
      data_tags: [destructive]
    action: require_approval
    reason: Destructive operations require human approval.

  - name: default-allow
    boundary: [input, output, action]
    priority: 1000
    condition: {}
    action: allow
```

Tags are hierarchical: a rule matching `personal` also catches `personal.pii`, `personal.financial`, etc.

## CLI

```bash
safeai init                          # Scaffold config directory
safeai scan "text to check"          # Scan text from terminal
safeai validate                      # Validate all config files
safeai logs --action block --last 1h # Query audit log
safeai serve --mode sidecar          # Start REST API server
safeai hook                          # Universal coding agent hook
safeai setup claude-code             # Install hooks for Claude Code
safeai setup cursor                  # Install hooks for Cursor
safeai templates list                # Browse policy templates
safeai templates show healthcare     # View a template
```

## Documentation

| Resource | Description |
|:---|:---|
| [Quickstart](docs/17-quickstart.md) | Get running in 2 minutes |
| [Contributor Guide](CONTRIBUTING.md) | How to contribute |
| [Onboarding Playbook](docs/18-contributor-onboarding-playbook.md) | Deep dive for new contributors |
| [Architecture Review](docs/16-architecture-review-2026-02-20.md) | Design decisions and rationale |
| [Security Policy](SECURITY.md) | Vulnerability disclosure process |
| [Governance](GOVERNANCE.md) | Project governance model |
| [Compatibility](COMPATIBILITY.md) | Versioning and compatibility guarantees |

## Contributing

We welcome contributions. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

```bash
git clone https://github.com/enendufrankc/safeai.git
cd safeai
pip install -e ".[all]"
python -m pytest tests/ -v   # 173 tests, <3 seconds
```

## License

SafeAI is released under the [Apache 2.0 License](LICENSE).

---

<p align="center">
  <b>SafeAI</b> &mdash; Because AI agents should have guardrails, not afterthoughts.
</p>
