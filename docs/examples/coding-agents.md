# Securing Coding Agents with SafeAI

AI coding agents can write files, run shell commands, make API calls, and install packages — all autonomously. A single hallucinated command or prompt injection could delete your repo, leak secrets from `.env`, or push malicious code.

SafeAI enforces security policies on every action your coding agent takes. Setup takes **3 commands**.

---

## Supported agents

| Agent | Recommended setup | Alternative |
|:---|:---|:---|
| Claude Code | MCP server | `safeai setup claude-code` (hooks) |
| Cursor | MCP server | `safeai setup cursor` (hooks) |
| Windsurf | MCP server | — |
| GitHub Copilot | MCP server | — |
| Codex CLI | MCP server | `safeai hook` (universal hook) |
| Replit Agent | MCP server | Sidecar proxy |
| Antigravity | MCP server | `safeai hook` (universal hook) |
| VS Code + Continue | MCP server | — |
| Any MCP-compatible agent | MCP server | — |

!!! tip "MCP is the universal approach"
    Most coding agents now support [MCP (Model Context Protocol)](https://modelcontextprotocol.io/). Adding SafeAI as an MCP server works across all of them with the same config — no agent-specific setup needed.

---

## Quick setup

### Step 1 — Initialize SafeAI

```bash
uv pip install safeai
cd your-project
safeai init
```

The interactive setup walks you through choosing an AI backend:

```
Intelligence Layer Setup

Enable the intelligence layer? [Y/n]: Y

Choose your AI backend:
  1. Ollama (local, free — no API key needed)
  2. OpenAI
  3. Anthropic
  4. Google Gemini
  5. Mistral
  6. Groq
  ...

Select provider [1]: 1

Intelligence layer configured!
```

### Step 2 — Auto-generate policies

```bash
safeai intelligence auto-config --path . --apply
```

SafeAI analyzes your project structure and generates security policies automatically.

### Step 3 — Add SafeAI MCP server to your agent

Add this to your agent's MCP config:

```json
{
  "mcpServers": {
    "safeai": {
      "command": "safeai",
      "args": ["mcp"]
    }
  }
}
```

That's it. Your coding agent now calls SafeAI's `scan_input`, `guard_output`, and `intercept_tool` tools before every action.

---

## Where to put the MCP config

Each agent reads MCP server config from a different file:

=== "Claude Code"

    ```json title=".claude/settings.json"
    {
      "mcpServers": {
        "safeai": {
          "command": "safeai",
          "args": ["mcp"]
        }
      }
    }
    ```

    Or use the shortcut: `safeai setup claude-code`

=== "Cursor"

    ```json title=".cursor/mcp.json"
    {
      "mcpServers": {
        "safeai": {
          "command": "safeai",
          "args": ["mcp"]
        }
      }
    }
    ```

=== "Windsurf"

    ```json title="~/.codeium/windsurf/mcp_config.json"
    {
      "mcpServers": {
        "safeai": {
          "command": "safeai",
          "args": ["mcp"]
        }
      }
    }
    ```

=== "VS Code (Continue / Copilot)"

    ```json title=".vscode/mcp.json"
    {
      "mcpServers": {
        "safeai": {
          "command": "safeai",
          "args": ["mcp"]
        }
      }
    }
    ```

=== "Codex CLI"

    ```json title="~/.codex/mcp.json"
    {
      "mcpServers": {
        "safeai": {
          "command": "safeai",
          "args": ["mcp"]
        }
      }
    }
    ```

=== "Replit Agent"

    In your Replit project, add to `.replit`:

    ```toml title=".replit"
    [mcp]
    [mcp.servers.safeai]
    command = "safeai"
    args = ["mcp"]
    ```

=== "Any MCP client"

    Look for your agent's MCP configuration file and add:

    ```json
    {
      "mcpServers": {
        "safeai": {
          "command": "safeai",
          "args": ["mcp"]
        }
      }
    }
    ```

---

## MCP tools exposed

Once connected, your coding agent can call these SafeAI tools:

| Tool | What it does |
|:---|:---|
| `scan_input` | Scan text for secrets, PII, and policy violations before the model sees it |
| `guard_output` | Check model responses for leaked secrets or PII before showing to the user |
| `intercept_tool` | Validate a tool call (bash, file write, API call) against policies before execution |
| `query_audit` | Search the audit trail for past decisions |
| `check_approval` | Check if a pending action has been approved |

---

## What gets enforced

| Action | Example | SafeAI response |
|:---|:---|:---|
| Destructive command | `rm -rf ~/projects` | **Blocked** |
| Read private keys | `cat ~/.ssh/id_ed25519` | **Blocked** |
| Leak secret in code | `api_key = "sk-abc123"` | **Blocked** |
| PII in output | `User email: john@example.com` | **Redacted** |
| Install suspicious package | `pip install totally-not-malware` | **Blocked** |
| Push to remote | `git push origin main` | **Held for approval** |
| Write to `.env` | `echo "DB_PASS=..." > .env` | **Blocked** |

---

## Explain blocked actions

When SafeAI blocks something and you want to understand why:

```bash
# See recent blocks
safeai logs --action block --last 1h

# Ask the AI to explain
safeai intelligence explain evt_abc123
```

```
Classification: DESTRUCTIVE_COMMAND
Severity: HIGH

The agent attempted to run "rm -rf ~/projects" via the bash tool.
This matches the destructive command policy. The command would have
recursively deleted your projects directory.
```

---

## Improve policies over time

After your coding agent has been running for a while:

```bash
safeai intelligence recommend --since 7d --apply
```

The recommender analyzes your audit trail and suggests policy improvements.

---

## Full example

```bash
# One-time setup (30 seconds)
uv pip install safeai
safeai init                                       # interactive setup
safeai intelligence auto-config --path . --apply  # generate policies

# Add MCP config to your agent (same for all agents)
# Then use your coding agent normally — SafeAI enforces on every action.
```

---

## Alternative: hooks (no MCP)

If your agent doesn't support MCP, SafeAI also supports direct hooks:

```bash
# Auto-install hooks for supported agents
safeai setup claude-code
safeai setup cursor

# Or use the universal hook with any agent
echo '{"tool": "bash", "input": {"command": "rm -rf /"}}' | safeai hook
# → {"decision": "block", "reason": "Destructive commands are not allowed."}
```

---

## Alternative: sidecar proxy (any language)

For agents that can make HTTP calls but don't support MCP or hooks:

```bash
safeai serve --mode sidecar --port 8484
```

Then call the REST API:

```bash
curl -X POST http://localhost:8484/v1/intercept/tool \
  -H "content-type: application/json" \
  -d '{"tool": "bash", "input": {"command": "rm -rf /"}, "agent_id": "my-agent"}'
```

---

## Next steps

- [Intelligence Layer](../guides/intelligence.md) — AI advisory agents
- [Coding Agent Integration](../integrations/coding-agents.md) — hook protocol details
- [Dangerous Commands](../guides/dangerous-commands.md) — command blocklists
- [Secret Detection](../guides/secret-detection.md) — tune secret detection
- [Proxy / Sidecar](../integrations/proxy-sidecar.md) — HTTP API reference
