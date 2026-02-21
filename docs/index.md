---
hide:
  - navigation
  - toc
---

<div class="hero" markdown>

![SafeAI Banner](assets/banner.png)

# SafeAI

### SECURE. INTELLIGENT. TRUSTED.

<p class="tagline">The runtime security layer for AI agents.<br>
Block secrets. Redact PII. Enforce policies. Control tools. Approve actions.<br>
Works with <strong>any</strong> AI provider — OpenAI, Gemini, Claude, LangChain, CrewAI, and more.</p>

</div>

<div class="badges" markdown>

[![Build](https://img.shields.io/github/actions/workflow/status/enendufrankc/safeai/quality.yml?label=build&style=flat-square)](https://github.com/enendufrankc/safeai/actions/workflows/quality.yml)
[![Release](https://img.shields.io/badge/release-v0.6.0-blue?style=flat-square)](https://github.com/enendufrankc/safeai/releases)
[![PyPI](https://img.shields.io/pypi/v/safeai?style=flat-square&label=pypi)](https://pypi.org/project/safeai/)
[![License](https://img.shields.io/badge/license-Apache--2.0-green?style=flat-square)](https://github.com/enendufrankc/safeai/blob/main/LICENSE)
[![Stars](https://img.shields.io/github/stars/enendufrankc/safeai?style=flat-square)](https://github.com/enendufrankc/safeai/stargazers)

</div>

## Two lines. That's it.

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

</div>

---

## Everything you need to secure AI agents

<div class="feature-grid" markdown>

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

## Architecture

```
                    ┌──────────────────────────────────┐
  User / Agent  ──> │  INPUT BOUNDARY   (scan_input)   │ ──> AI Provider
                    │  ACTION BOUNDARY  (intercept)     │     (OpenAI, Gemini,
  AI Provider   <── │  OUTPUT BOUNDARY  (guard_output)  │ <──  Claude, etc.)
                    └──────────────────────────────────┘
                              SafeAI Runtime
```

SafeAI enforces security at the **boundaries** where data enters, exits, and crosses trust lines. Every prompt, every tool call, and every response passes through policy-driven enforcement before it goes anywhere.

---

## Works with everything

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

## Install

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
