# SafeAI Integration Patterns

Reference for integrating SafeAI into specific frameworks and agent types.

## Table of Contents
1. [SDK Quickstart](#sdk-quickstart)
2. [LangChain](#langchain)
3. [CrewAI](#crewai)
4. [AutoGen](#autogen)
5. [Claude ADK](#claude-adk)
6. [Google ADK](#google-adk)
7. [Proxy / Sidecar Mode](#proxy--sidecar-mode)
8. [Claude Code (hooks)](#claude-code-hooks)
9. [Cursor (hooks)](#cursor-hooks)
10. [MCP Server](#mcp-server)

---

## SDK Quickstart

```python
from safeai import SafeAI

# Zero-config: blocks secrets, redacts PII
ai = SafeAI.quickstart()

# From config file
ai = SafeAI.from_config("safeai.yaml")

# Boundaries
result = ai.scan_input("User input text")
result = ai.guard_output("Model output text")
result = ai.intercept_tool_request("bash", {"command": "ls -la"})
```

**ScanResult fields:** `allowed`, `action`, `filtered_text`, `tags`, `policy_name`, `reason`

---

## LangChain

```python
from safeai.middleware.langchain import SafeAIToolWrapper
from safeai import SafeAI

ai = SafeAI.from_config("safeai.yaml")

# Wrap a tool
@SafeAIToolWrapper(ai)
def my_tool(input: str) -> str:
    return do_something(input)

# Or use the decorator directly on a LangChain Tool
from langchain.tools import Tool
safe_tool = SafeAIToolWrapper(ai).wrap(Tool(name="search", func=search_fn, description="..."))
```

---

## CrewAI

```python
from safeai.middleware.crewai import SafeAICrewAIWrapper
from safeai import SafeAI

ai = SafeAI.from_config("safeai.yaml")
wrapper = SafeAICrewAIWrapper(ai)

# Wrap tool before passing to CrewAI agent
safe_tool = wrapper.wrap(my_crewai_tool)
```

---

## AutoGen

```python
from safeai.middleware.autogen import SafeAIAutoGenInterceptor
from safeai import SafeAI

ai = SafeAI.from_config("safeai.yaml")
interceptor = SafeAIAutoGenInterceptor(ai)

# Attach to GroupChat or ConversableAgent message flow
# interceptor.on_message(msg) → filtered message
```

---

## Claude ADK

```python
from safeai.middleware.claude_adk import SafeAIClaudeADKHook
from safeai import SafeAI

ai = SafeAI.from_config("safeai.yaml")
hook = SafeAIClaudeADKHook(ai)

# Register as a tool hook in your Claude ADK agent
agent.register_tool_hook(hook.pre_tool, hook.post_tool)
```

---

## Google ADK

```python
from safeai.middleware.google_adk import SafeAIGoogleADKWrapper
from safeai import SafeAI

ai = SafeAI.from_config("safeai.yaml")
wrapper = SafeAIGoogleADKWrapper(ai)

safe_tool = wrapper.wrap(my_google_adk_tool)
```

---

## Proxy / Sidecar Mode

Start SafeAI as an HTTP proxy alongside your app:

```bash
safeai serve --mode sidecar --port 8910 --config safeai.yaml
```

**Endpoints:**

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `POST /v1/scan/input` | POST | Scan input text |
| `POST /v1/guard/output` | POST | Guard output text |
| `POST /v1/intercept/tool` | POST | Intercept tool call |
| `GET /v1/audit` | GET | Query audit log |
| `GET /v1/policies/templates` | GET | List policy templates |
| `GET /v1/health` | GET | Health check |

**Example:**
```bash
curl -X POST http://localhost:8910/v1/scan/input \
  -H "Content-Type: application/json" \
  -d '{"text": "My SSN is 123-45-6789", "agent_id": "my-agent"}'
```

**Gateway mode** (proxy upstream LLM API):
```bash
safeai serve --mode gateway --port 8910 --upstream https://api.openai.com
```

---

## Claude Code (hooks)

After `safeai setup claude-code`, `.claude/settings.json` gets these hooks:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": ".*",
        "hooks": [
          {
            "type": "command",
            "command": "safeai hook --config safeai.yaml --profile claude-code --event pre_tool_use"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": ".*",
        "hooks": [
          {
            "type": "command",
            "command": "safeai hook --config safeai.yaml --profile claude-code --event post_tool_use"
          }
        ]
      }
    ]
  }
}
```

Hook stdin JSON:
```json
{
  "event": "pre_tool_use",
  "agent_id": "claude-code",
  "tool_name": "Bash",
  "tool_input": {"command": "git push --force origin main"},
  "session_id": "optional-session-id"
}
```

Exit codes: `0` = allow, `1` = block (Claude Code respects this to cancel the tool call)

---

## Cursor (hooks)

After `safeai setup cursor`, `.cursor/rules` gets SafeAI enforcement rules:

```
# SafeAI Security Rules
Before executing any tool call, pipe the request through:
  safeai hook --config safeai.yaml --profile cursor
```

---

## MCP Server

Tools available when SafeAI runs as an MCP server:

| Tool | Input | Output |
|------|-------|--------|
| `scan_input` | `text`, `agent_id?`, `session_id?` | `allowed`, `action`, `filtered_text`, `tags` |
| `guard_output` | `text`, `agent_id?` | `allowed`, `action`, `filtered_text` |
| `scan_structured` | `payload` (JSON object), `agent_id?` | `allowed`, `action`, `filtered_payload` |
| `query_audit` | `limit?`, `boundary?`, `action?`, `agent_id?` | Array of audit events |
| `list_policies` | _(none)_ | Available policy template names |
| `check_tool` | `tool_name`, `tool_input` (JSON), `agent_id?` | `allowed`, `reason` |

**Launch:**
```bash
safeai mcp --config safeai.yaml
```

**Claude Desktop config** (`~/Library/Application Support/Claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "safeai": {
      "command": "safeai",
      "args": ["mcp", "--config", "/absolute/path/to/safeai.yaml"]
    }
  }
}
```
