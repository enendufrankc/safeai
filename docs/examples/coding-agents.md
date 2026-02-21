# Securing Coding Agents with SafeAI

AI coding agents can write files, run shell commands, make API calls, and install packages — all autonomously. A single hallucinated command or prompt injection could delete your repo, leak secrets from `.env`, or push malicious code.

SafeAI enforces security policies on every action your coding agent takes. Setup takes **2 commands**.

---

## Supported agents

| Agent | Setup |
|:---|:---|
| Claude Code | `safeai setup claude-code` |
| Cursor | `safeai setup cursor` |
| GitHub Copilot | `safeai hook` (universal hook) |
| Codex CLI | `safeai hook` (universal hook) |
| Replit Agent | Sidecar proxy |
| Antigravity | `safeai hook` (universal hook) |
| Windsurf | `safeai hook` (universal hook) |
| Any MCP client | `safeai mcp` (MCP server) |
| Any agent | `safeai hook` (universal hook) |

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

### Step 2 — Auto-generate policies for your project

```bash
safeai intelligence auto-config --path . --apply
```

SafeAI analyzes your project structure and generates security policies automatically. Done.

---

## Connect your coding agent

=== "Claude Code"

    ```bash
    safeai setup claude-code
    ```

    This writes `.claude/settings.json` with SafeAI hooks. Every tool call Claude Code makes — file writes, shell commands, web requests — is enforced automatically.

=== "Cursor"

    ```bash
    safeai setup cursor
    ```

    This writes `.cursor/rules` with SafeAI hooks. Cursor's agent checks SafeAI before every action.

=== "GitHub Copilot / Codex / Antigravity / Windsurf"

    These agents support custom pre-execution hooks. Point them at `safeai hook`:

    ```bash
    # Test it
    echo '{"tool": "bash", "input": {"command": "rm -rf /"}}' | safeai hook
    ```

    ```json
    {
      "decision": "block",
      "reason": "Destructive commands are not allowed."
    }
    ```

    Configure your agent to pipe tool calls through `safeai hook` before execution. The exact config location varies by agent — check your agent's docs for custom hook/command settings.

=== "Replit Agent"

    Replit runs in a container, so use the sidecar proxy:

    ```bash
    # In your Replit shell
    pip install safeai
    safeai init --non-interactive
    safeai intelligence auto-config --path . --apply
    safeai serve --mode sidecar --port 8484 &
    ```

    Then call the SafeAI API before executing actions:

    ```python
    import requests

    result = requests.post("http://localhost:8484/v1/scan/input", json={
        "text": "rm -rf /home/runner/*",
        "agent_id": "replit-agent",
    }).json()

    if result["decision"] == "block":
        print(f"Blocked: {result['violations']}")
    ```

=== "Any MCP Client"

    SafeAI runs as an MCP server compatible with any MCP client:

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

    The MCP server exposes `scan_input`, `guard_output`, and `intercept_tool` as callable tools.

---

## What gets enforced

Once connected, SafeAI checks every action against your policies:

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

The recommender analyzes your audit trail and suggests policy improvements — like adding rules for tools that aren't covered yet.

---

## Full example: Claude Code

```bash
# One-time setup (30 seconds)
uv pip install safeai
safeai init                                     # interactive — choose your AI backend
safeai intelligence auto-config --path . --apply  # generate policies
safeai setup claude-code                         # install hooks

# That's it. Use Claude Code normally.
# SafeAI enforces policies on every tool call.
```

## Full example: Cursor

```bash
uv pip install safeai
safeai init
safeai intelligence auto-config --path . --apply
safeai setup cursor
```

## Full example: Any agent via universal hook

```bash
uv pip install safeai
safeai init
safeai intelligence auto-config --path . --apply

# Configure your agent to run tool calls through:
#   echo '<json action>' | safeai hook
```

---

## Next steps

- [Intelligence Layer](../guides/intelligence.md) — AI advisory agents
- [Dangerous Commands](../guides/dangerous-commands.md) — command blocklists
- [Secret Detection](../guides/secret-detection.md) — tune secret detection
- [Approval Workflows](../guides/approval-workflows.md) — human-in-the-loop gates
- [Proxy / Sidecar](../integrations/proxy-sidecar.md) — HTTP API for non-hook environments
