# AutoGen Integration

Wrap AutoGen tools so every function call in your multi-agent conversation passes through SafeAI's policy engine -- secret detection, PII filtering, tool contracts, and audit logging are enforced transparently.

!!! tip "Auto-generate AutoGen integration"
    Let the intelligence layer generate SafeAI wrappers for your AutoGen agents:
    ```bash
    safeai intelligence integrate --target autogen --path . --apply
    ```

---

## Install

```bash
uv pip install safeai pyautogen
```

---

## Quick Start

```python
from safeai import SafeAI

ai = SafeAI()
adapter = ai.autogen_adapter()
safe_tool = adapter.wrap_tool("execute_code", code_tool, agent_id="coder")
```

---

## Detailed Usage

### Creating the Adapter

```python
from safeai import SafeAI

ai = SafeAI.from_config("safeai.yaml")
adapter = ai.autogen_adapter()   # returns SafeAIAutoGenAdapter
```

You can also import the adapter directly:

```python
from safeai.middleware.autogen import SafeAIAutoGenAdapter
```

### Wrapping Tools

AutoGen registers tools as Python functions. The adapter wraps these functions so that every call is intercepted:

```python
def search_web(query: str) -> str:
    """Search the web for information."""
    return f"Results for: {query}"

# Wrap with SafeAI
safe_search = adapter.wrap_tool(
    name="search_web",
    tool=search_web,
    agent_id="research-agent",
)
```

!!! info "Request and response interception"
    The adapter intercepts both the **request** (function arguments) and the **response** (return value). Inputs are scanned before execution; outputs are guarded before they reach the agent.

### Registering Wrapped Tools with AutoGen Agents

```python
import autogen

assistant = autogen.AssistantAgent(
    name="assistant",
    llm_config={"config_list": config_list},
)

user_proxy = autogen.UserProxyAgent(
    name="user_proxy",
    human_input_mode="NEVER",
)

# Register the SafeAI-wrapped function
user_proxy.register_function(
    function_map={
        "search_web": safe_search,
    }
)
```

---

## Full Example

```python
import autogen
from safeai import SafeAI

# 1. SafeAI setup
ai = SafeAI.from_config("safeai.yaml")
adapter = ai.autogen_adapter()

# 2. Define tools
def execute_code(code: str) -> str:
    """Execute Python code in a sandbox."""
    # ... sandboxed execution ...
    return "execution result"

def read_file(path: str) -> str:
    """Read a file from disk."""
    with open(path) as f:
        return f.read()

# 3. Wrap tools
safe_execute = adapter.wrap_tool("execute_code", execute_code, agent_id="coder")
safe_read = adapter.wrap_tool("read_file", read_file, agent_id="coder")

# 4. Configure AutoGen agents
config_list = [{"model": "gpt-4", "api_key": "..."}]

assistant = autogen.AssistantAgent(
    name="assistant",
    system_message="You are a helpful coding assistant.",
    llm_config={"config_list": config_list},
)

user_proxy = autogen.UserProxyAgent(
    name="user_proxy",
    human_input_mode="NEVER",
    code_execution_config=False,
)

# 5. Register wrapped tools
user_proxy.register_function(
    function_map={
        "execute_code": safe_execute,
        "read_file": safe_read,
    }
)

# Every function call is now guarded by SafeAI
user_proxy.initiate_chat(assistant, message="Read config.yaml and summarize it")
```

!!! warning "Credential leaks are caught"
    If the assistant tries to read a file containing API keys and pass them to `execute_code`, SafeAI detects the secret in the input and blocks the call.

---

## Multi-Agent Conversations

AutoGen excels at multi-agent group chats. SafeAI can enforce different policies per agent:

```python
# Different agent IDs get different permissions
safe_code_tool = adapter.wrap_tool("execute_code", execute_code, agent_id="coder")
safe_review_tool = adapter.wrap_tool("execute_code", execute_code, agent_id="reviewer")
```

```yaml
# safeai.yaml
tool_contracts:
  execute_code:
    allowed_agents: ["coder"]       # reviewer cannot execute code
    blocked_patterns:
      - "os.system"
      - "subprocess"
```

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
  execute_code:
    allowed_agents: ["coder"]
    max_calls_per_minute: 5
  read_file:
    allowed_agents: ["coder", "reviewer"]
    blocked_patterns:
      - "/etc/shadow"
      - ".env"

audit:
  enabled: true
  log_inputs: true
  log_outputs: true
```

---

## API Reference

| Class | Description |
|-------|-------------|
| `SafeAIAutoGenAdapter` | Main adapter returned by `ai.autogen_adapter()` |
| `adapter.wrap_tool()` | Wrap a single function with policy enforcement |

See [API Reference - Middleware](../reference/middleware.md) for full signatures.

---

## Next Steps

- [Policy Engine](../guides/policy-engine.md) -- customize enforcement rules
- [Tool Contracts](../guides/tool-contracts.md) -- per-tool permissions and schemas
- [Agent Identity](../guides/agent-identity.md) -- manage agent IDs and capabilities
