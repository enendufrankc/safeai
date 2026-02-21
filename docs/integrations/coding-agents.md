# Coding Agent Integration

SafeAI provides first-class support for AI-powered coding assistants. One CLI command installs hooks that intercept every tool call your coding agent makes -- file writes, shell commands, API calls -- and enforce your security policy.

---

## Supported Agents

| Agent | Setup Command | Mechanism |
|-------|---------------|-----------|
| Claude Code | `safeai setup claude-code` | `.claude/settings.json` hooks |
| Cursor | `safeai setup cursor` | `.cursor/rules` hooks |
| Any MCP client | `safeai mcp` | MCP server protocol |
| Any agent | `safeai hook` | Universal stdin/stdout JSON protocol |

---

## Claude Code

### Setup

```bash
safeai setup claude-code
```

This command auto-generates `.claude/settings.json` in your project root with SafeAI hook configuration. Claude Code will call SafeAI before executing any tool.

!!! tip "No code changes required"
    The setup command writes the configuration file -- you do not need to modify your Claude Code workflow at all.

### What Gets Hooked

- **File operations** -- write, edit, delete
- **Shell commands** -- bash, terminal execution
- **Web requests** -- fetch, API calls
- **MCP tool calls** -- any MCP-connected tool

### Manual Configuration

If you prefer to configure manually, add SafeAI as a hook in `.claude/settings.json`:

```json
{
  "hooks": {
    "tool_use": {
      "command": "safeai hook",
      "timeout_ms": 5000
    }
  }
}
```

---

## Cursor

### Setup

```bash
safeai setup cursor
```

This command auto-generates `.cursor/rules` in your project root with SafeAI hook configuration.

### Manual Configuration

Add SafeAI to your `.cursor/rules` file:

```
@safeai-hook
Before executing any tool, pipe the action through `safeai hook` for policy enforcement.
```

---

## MCP Server

SafeAI can run as an [MCP (Model Context Protocol)](https://modelcontextprotocol.io/) server, making it compatible with any MCP client.

### Start the MCP Server

```bash
safeai mcp
```

### Connect from Any MCP Client

Configure your MCP client to connect to SafeAI:

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

!!! info "MCP tools exposed"
    The SafeAI MCP server exposes tools like `scan_input`, `guard_output`, and `intercept_tool` that any MCP-compatible client can call.

---

## Universal Hook Protocol

The `safeai hook` command implements a simple JSON-over-stdin/stdout protocol that works with any agent or automation.

### How It Works

```
Agent  --[JSON action]--> stdin --> safeai hook --> policy engine
                                                       |
Agent <--[JSON decision]-- stdout <--------------------+
```

### Input Format

The agent sends a JSON object on **stdin** describing the action:

```json
{
  "tool": "bash",
  "input": {
    "command": "curl https://api.example.com -H 'Authorization: Bearer sk-secret123'"
  },
  "agent_id": "claude-code",
  "context": {
    "file": "main.py",
    "line": 42
  }
}
```

### Output Format

SafeAI writes a JSON decision to **stdout**:

=== "Allowed"

    ```json
    {
      "decision": "allow",
      "tool": "bash",
      "agent_id": "claude-code",
      "timestamp": "2025-01-15T10:30:00Z"
    }
    ```

=== "Blocked"

    ```json
    {
      "decision": "block",
      "tool": "bash",
      "agent_id": "claude-code",
      "reason": "Secret detected in command: API key pattern matched",
      "violations": [
        {
          "type": "secret_detected",
          "detector": "api_key",
          "location": "input.command",
          "severity": "critical"
        }
      ],
      "timestamp": "2025-01-15T10:30:00Z"
    }
    ```

=== "Modified"

    ```json
    {
      "decision": "modify",
      "tool": "bash",
      "agent_id": "claude-code",
      "modified_input": {
        "command": "curl https://api.example.com -H 'Authorization: Bearer [REDACTED]'"
      },
      "reason": "Secret redacted from command",
      "timestamp": "2025-01-15T10:30:00Z"
    }
    ```

### Using the Hook from a Script

```bash
# Pipe a tool action through SafeAI
echo '{"tool": "bash", "input": {"command": "ls -la"}}' | safeai hook
```

```python
import subprocess
import json

action = {
    "tool": "write_file",
    "input": {"path": "secrets.txt", "content": "password=hunter2"},
    "agent_id": "my-agent",
}

result = subprocess.run(
    ["safeai", "hook"],
    input=json.dumps(action),
    capture_output=True,
    text=True,
)

decision = json.loads(result.stdout)
if decision["decision"] == "allow":
    # proceed with the action
    ...
elif decision["decision"] == "block":
    print(f"Blocked: {decision['reason']}")
```

---

## Configuration

All coding agent hooks respect your `safeai.yaml` policy:

```yaml
# safeai.yaml
policy:
  default_action: block
  secret_detection:
    enabled: true
  pii_protection:
    enabled: true
    action: redact
  dangerous_commands:
    enabled: true
    blocked:
      - "rm -rf /"
      - "DROP TABLE"
      - "chmod 777"

hook:
  timeout_ms: 5000
  log_allowed: true
  log_blocked: true

audit:
  enabled: true
```

---

## Comparison

| Feature | `setup claude-code` | `setup cursor` | `safeai mcp` | `safeai hook` |
|---------|:-------------------:|:--------------:|:------------:|:-------------:|
| Auto-configuration | Yes | Yes | Manual | Manual |
| Protocol | JSON hook | Rules file | MCP | stdin/stdout JSON |
| Works offline | Yes | Yes | Yes | Yes |
| Custom policy | Yes | Yes | Yes | Yes |
| Audit logging | Yes | Yes | Yes | Yes |

---

## Next Steps

- [Proxy / Sidecar](proxy-sidecar.md) -- HTTP-based alternative for non-hook environments
- [Dangerous Commands](../guides/dangerous-commands.md) -- configure command blocklists
- [Secret Detection](../guides/secret-detection.md) -- tune secret detection patterns
