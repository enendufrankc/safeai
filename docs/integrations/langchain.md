# LangChain Integration

Wrap any LangChain tool so every invocation passes through SafeAI's policy engine -- secret detection, PII filtering, tool contracts, and audit logging all happen transparently.

!!! tip "Auto-generate LangChain integration"
    Let the intelligence layer generate SafeAI-wrapped tools for your LangChain project:
    ```bash
    safeai intelligence integrate --target langchain --path . --apply
    ```

---

## Install

```bash
uv pip install safeai langchain
```

---

## Quick Start (3 Lines)

```python
from safeai import SafeAI

ai = SafeAI()
adapter = ai.langchain_adapter()
safe_tool = adapter.wrap_tool("search", search_tool, agent_id="agent-1")
```

That is it. `safe_tool` is a drop-in replacement -- call it exactly like the original, and SafeAI enforces your policy on every invocation.

---

## Detailed Usage

### Creating the Adapter

```python
from safeai import SafeAI

ai = SafeAI.from_config("safeai.yaml")     # or SafeAI() for defaults
adapter = ai.langchain_adapter()             # returns SafeAILangChainAdapter
```

The adapter holds a reference to your SafeAI instance and its active policy. You can create multiple adapters with different configurations if needed.

### Wrapping Tools

```python
from langchain.tools import Tool

# Your existing LangChain tool
search_tool = Tool(
    name="web_search",
    func=lambda q: f"Results for: {q}",
    description="Search the web",
)

# Wrap it with SafeAI
safe_search = adapter.wrap_tool(
    name="web_search",
    tool=search_tool,
    agent_id="research-agent",
)
```

!!! info "What happens on each call"
    1. **Input scan** -- the tool's input is checked for secrets, PII, and policy violations.
    2. **Contract validation** -- if a tool contract is registered, the input schema is validated.
    3. **Execution** -- if the input passes, the original tool runs.
    4. **Output guard** -- the tool's output is scanned before being returned to the agent.
    5. **Audit log** -- the full request/response cycle is logged.

### Handling Blocked Calls

When SafeAI blocks a tool call, it raises `SafeAIBlockedError`:

```python
from safeai.middleware.langchain import SafeAIBlockedError

try:
    result = safe_search.run("Use API key sk-ABCDEF1234567890")
except SafeAIBlockedError as e:
    print(f"Blocked: {e.reason}")
    print(f"Violations: {e.violations}")
```

---

## Direct Import

If you prefer not to go through the `SafeAI` facade, import the adapter and helper directly:

```python
from safeai.middleware.langchain import (
    SafeAILangChainAdapter,
    SafeAICallback,
    SafeAIBlockedError,
    wrap_langchain_tool,
)
```

### Using `wrap_langchain_tool`

```python
from safeai.middleware.langchain import wrap_langchain_tool

safe_tool = wrap_langchain_tool(
    tool=search_tool,
    name="web_search",
    agent_id="research-agent",
    config_path="safeai.yaml",
)
```

### Using `SafeAICallback`

Attach SafeAI as a LangChain callback to intercept all tool calls in a chain or agent:

```python
from safeai.middleware.langchain import SafeAICallback

callback = SafeAICallback(safeai=ai)

# Pass to any LangChain chain or agent
agent.run("Do something", callbacks=[callback])
```

---

## Full Example

```python
from langchain.agents import initialize_agent, AgentType
from langchain.tools import Tool
from langchain_openai import ChatOpenAI
from safeai import SafeAI

# 1. Set up SafeAI
ai = SafeAI.from_config("safeai.yaml")
adapter = ai.langchain_adapter()

# 2. Define tools
tools = [
    Tool(name="calculator", func=lambda x: eval(x), description="Math"),
    Tool(name="search", func=lambda q: f"Results: {q}", description="Search"),
]

# 3. Wrap all tools
safe_tools = [
    adapter.wrap_tool(t.name, t, agent_id="math-agent")
    for t in tools
]

# 4. Build agent with safe tools
llm = ChatOpenAI(model="gpt-4")
agent = initialize_agent(
    safe_tools,
    llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
)

# Every tool call is now guarded by SafeAI
agent.run("What is 2 + 2?")
```

---

## Configuration

The adapter respects your `safeai.yaml` policy. Key settings for LangChain:

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
  web_search:
    allowed_agents: ["research-agent"]
    max_calls_per_minute: 10

audit:
  enabled: true
  log_inputs: true
  log_outputs: true
```

---

## API Reference

| Class / Function | Description |
|------------------|-------------|
| `SafeAILangChainAdapter` | Main adapter returned by `ai.langchain_adapter()` |
| `SafeAICallback` | LangChain callback handler for chain-level interception |
| `SafeAIBlockedError` | Raised when a tool call is blocked by policy |
| `wrap_langchain_tool()` | Convenience function for one-off wrapping |

See [API Reference - Middleware](../reference/middleware.md) for full signatures.

---

## Next Steps

- [Policy Engine](../guides/policy-engine.md) -- customize what gets blocked
- [Tool Contracts](../guides/tool-contracts.md) -- define per-tool schemas and permissions
- [Audit Logging](../guides/audit-logging.md) -- query the decision log
