# Google ADK Integration

Wrap Google ADK tools so every tool invocation passes through SafeAI's policy engine -- secret detection, PII filtering, tool contracts, and audit logging are enforced transparently.

---

## Install

```bash
pip install safeai google-genai
```

---

## Quick Start

```python
from safeai import SafeAI

ai = SafeAI()
adapter = ai.google_adk_adapter()
safe_tool = adapter.wrap_tool("search", search_tool, agent_id="gemini-agent")
```

---

## Detailed Usage

### Creating the Adapter

```python
from safeai import SafeAI

ai = SafeAI.from_config("safeai.yaml")
adapter = ai.google_adk_adapter()   # returns SafeAIGoogleADKAdapter
```

You can also import the adapter directly:

```python
from safeai.middleware.google_adk import SafeAIGoogleADKAdapter
```

### Wrapping Tools

```python
def get_stock_price(symbol: str) -> str:
    """Get the current stock price."""
    return f"{symbol}: $142.50"

# Wrap with SafeAI
safe_stock = adapter.wrap_tool(
    name="get_stock_price",
    tool=get_stock_price,
    agent_id="finance-agent",
)
```

!!! info "Request and response interception"
    The adapter intercepts both the **request** (tool input) and the **response** (tool output). Inputs are scanned before the tool executes; outputs are guarded before they are returned to the Gemini model.

### Wrapping Multiple Tools

```python
tools = {
    "get_stock_price": get_stock_price,
    "place_order": place_order,
    "get_portfolio": get_portfolio,
}

safe_tools = {
    name: adapter.wrap_tool(name, fn, agent_id="finance-agent")
    for name, fn in tools.items()
}
```

---

## Full Example

```python
import google.genai as genai
from safeai import SafeAI

# 1. SafeAI setup
ai = SafeAI.from_config("safeai.yaml")
adapter = ai.google_adk_adapter()

# 2. Define tools
def search_knowledge_base(query: str) -> str:
    """Search the internal knowledge base."""
    return f"Found 5 articles matching: {query}"

def update_ticket(ticket_id: str, status: str, comment: str) -> str:
    """Update a support ticket."""
    return f"Ticket {ticket_id} updated to {status}"

# 3. Wrap tools
safe_search = adapter.wrap_tool(
    "search_knowledge_base", search_knowledge_base, agent_id="support-agent"
)
safe_update = adapter.wrap_tool(
    "update_ticket", update_ticket, agent_id="support-agent"
)

# 4. Define function declarations for Gemini
search_fn = genai.types.FunctionDeclaration(
    name="search_knowledge_base",
    description="Search the internal knowledge base",
    parameters={
        "type": "OBJECT",
        "properties": {"query": {"type": "STRING"}},
        "required": ["query"],
    },
)

update_fn = genai.types.FunctionDeclaration(
    name="update_ticket",
    description="Update a support ticket",
    parameters={
        "type": "OBJECT",
        "properties": {
            "ticket_id": {"type": "STRING"},
            "status": {"type": "STRING"},
            "comment": {"type": "STRING"},
        },
        "required": ["ticket_id", "status", "comment"],
    },
)

tool_config = genai.types.Tool(function_declarations=[search_fn, update_fn])

# 5. Use with Google GenAI client
client = genai.Client()
response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents="Search for password reset instructions",
    config=genai.types.GenerateContentConfig(tools=[tool_config]),
)

# 6. Handle function calls -- SafeAI enforces policy here
for part in response.candidates[0].content.parts:
    if fn_call := part.function_call:
        if fn_call.name == "search_knowledge_base":
            result = safe_search(query=fn_call.args["query"])
        elif fn_call.name == "update_ticket":
            result = safe_update(**fn_call.args)
```

!!! warning "Policy enforcement in action"
    If Gemini tries to include credentials in a ticket comment or leak PII through a search query, SafeAI blocks the tool call and logs the violation.

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
  update_ticket:
    allowed_agents: ["support-agent"]
    max_calls_per_minute: 20
    approval_required: false
  search_knowledge_base:
    allowed_agents: ["support-agent", "escalation-agent"]

audit:
  enabled: true
  log_inputs: true
  log_outputs: true
```

---

## API Reference

| Class | Description |
|-------|-------------|
| `SafeAIGoogleADKAdapter` | Main adapter returned by `ai.google_adk_adapter()` |
| `adapter.wrap_tool()` | Wrap a single tool with policy enforcement |

See [API Reference - Middleware](../reference/middleware.md) for full signatures.

---

## Next Steps

- [Claude ADK Integration](claude-adk.md) -- similar pattern for Anthropic's ADK
- [Policy Engine](../guides/policy-engine.md) -- customize enforcement rules
- [Audit Logging](../guides/audit-logging.md) -- query the decision log
