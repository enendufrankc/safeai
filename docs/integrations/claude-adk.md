# Claude ADK Integration

Wrap Claude ADK tools so every tool invocation passes through SafeAI's policy engine -- secret detection, PII filtering, tool contracts, and audit logging are enforced transparently.

---

## Install

```bash
pip install safeai anthropic
```

---

## Quick Start

```python
from safeai import SafeAI

ai = SafeAI()
adapter = ai.claude_adk_adapter()
safe_tool = adapter.wrap_tool("search", search_tool, agent_id="claude-agent")
```

---

## Detailed Usage

### Creating the Adapter

```python
from safeai import SafeAI

ai = SafeAI.from_config("safeai.yaml")
adapter = ai.claude_adk_adapter()   # returns SafeAIClaudeADKAdapter
```

You can also import the adapter directly:

```python
from safeai.middleware.claude_adk import SafeAIClaudeADKAdapter
```

### Wrapping Tools

```python
def get_weather(location: str) -> str:
    """Get current weather for a location."""
    return f"Weather in {location}: 72F, sunny"

# Wrap with SafeAI
safe_weather = adapter.wrap_tool(
    name="get_weather",
    tool=get_weather,
    agent_id="assistant",
)
```

!!! info "Request and response interception"
    The adapter intercepts both the **request** (tool input) and the **response** (tool output). Inputs are scanned before the tool executes; outputs are guarded before they are returned to the Claude model.

### Wrapping Multiple Tools

```python
tools = {
    "get_weather": get_weather,
    "search_docs": search_docs,
    "run_query": run_query,
}

safe_tools = {
    name: adapter.wrap_tool(name, fn, agent_id="assistant")
    for name, fn in tools.items()
}
```

---

## Full Example

```python
import anthropic
from safeai import SafeAI

# 1. SafeAI setup
ai = SafeAI.from_config("safeai.yaml")
adapter = ai.claude_adk_adapter()

# 2. Define tools
def search_database(query: str) -> str:
    """Search the internal database."""
    return f"Found 3 results for: {query}"

def send_email(to: str, subject: str, body: str) -> str:
    """Send an email."""
    return f"Email sent to {to}"

# 3. Wrap tools
safe_search = adapter.wrap_tool("search_database", search_database, agent_id="assistant")
safe_email = adapter.wrap_tool("send_email", send_email, agent_id="assistant")

# 4. Define tool schemas for Claude
tool_schemas = [
    {
        "name": "search_database",
        "description": "Search the internal database",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    {
        "name": "send_email",
        "description": "Send an email",
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {"type": "string"},
                "subject": {"type": "string"},
                "body": {"type": "string"},
            },
            "required": ["to", "subject", "body"],
        },
    },
]

# 5. Use with Anthropic client
client = anthropic.Anthropic()
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    tools=tool_schemas,
    messages=[{"role": "user", "content": "Search for Q4 revenue data"}],
)

# 6. Handle tool use -- SafeAI enforces policy here
for block in response.content:
    if block.type == "tool_use":
        if block.name == "search_database":
            result = safe_search(query=block.input["query"])
        elif block.name == "send_email":
            result = safe_email(**block.input)
```

!!! warning "Sensitive data is caught"
    If Claude tries to include credentials in an email body or leak PII through a search query, SafeAI blocks the tool call and logs the violation.

---

## Configuration

```yaml
# safeai.yaml
policy:
  default_action: block
  secret_detection:
    enabled: true
  pii_protection:
    enabled: true
    action: redact

tool_contracts:
  send_email:
    allowed_agents: ["assistant"]
    max_calls_per_minute: 5
    approval_required: true
  search_database:
    allowed_agents: ["assistant"]

audit:
  enabled: true
  log_inputs: true
  log_outputs: true
```

---

## API Reference

| Class | Description |
|-------|-------------|
| `SafeAIClaudeADKAdapter` | Main adapter returned by `ai.claude_adk_adapter()` |
| `adapter.wrap_tool()` | Wrap a single tool with policy enforcement |

See [API Reference - Middleware](../reference/middleware.md) for full signatures.

---

## Next Steps

- [Google ADK Integration](google-adk.md) -- similar pattern for Google's ADK
- [Policy Engine](../guides/policy-engine.md) -- customize enforcement rules
- [Approval Workflows](../guides/approval-workflows.md) -- require human approval for sensitive tools
