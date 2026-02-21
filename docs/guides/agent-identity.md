# Agent Identity

SafeAI binds each agent to a declared set of tools and clearance levels. Before an agent calls a tool or accesses tagged data, `validate_agent_identity` checks that the agent is authorized. Agents that attempt to use unbound tools or access data above their clearance are denied.

!!! tip "Auto-discover agents"
    The intelligence layer can analyze your project and generate agent identity documents automatically:
    ```bash
    safeai intelligence auto-config --path . --apply
    ```
    Use this guide to customize generated identities or define them manually.

## Quick Example

```python
from safeai import SafeAI

ai = SafeAI.from_config("safeai.yaml")

result = ai.validate_agent_identity(
    "support-bot",
    tool_name="send_email",
    data_tags=["personal.pii.email"],
)
print(result.allowed)  # True
```

## Full Example

```yaml title="safeai.yaml"
agent_identities:
  support-bot:
    allowed_tools:
      - send_email
      - lookup_order
    clearance_tags:
      - personal.pii.email
      - personal.pii.name
      - public

  analytics-bot:
    allowed_tools:
      - query_database
      - generate_report
    clearance_tags:
      - personal.financial
      - aggregate
```

```python
from safeai import SafeAI

ai = SafeAI.from_config("safeai.yaml")

# support-bot can send email with PII
r1 = ai.validate_agent_identity(
    "support-bot",
    tool_name="send_email",
    data_tags=["personal.pii.email"],
)
assert r1.allowed is True

# support-bot cannot query the database
r2 = ai.validate_agent_identity(
    "support-bot",
    tool_name="query_database",
)
assert r2.allowed is False
print(r2.reason)  # "Tool 'query_database' not in allowed_tools for agent 'support-bot'"

# support-bot cannot access financial data
r3 = ai.validate_agent_identity(
    "support-bot",
    data_tags=["personal.financial"],
)
assert r3.allowed is False
print(r3.reason)  # "Tag 'personal.financial' not in clearance_tags for agent 'support-bot'"

# analytics-bot can query with financial clearance
r4 = ai.validate_agent_identity(
    "analytics-bot",
    tool_name="query_database",
    data_tags=["personal.financial"],
)
assert r4.allowed is True
```

!!! danger "Unknown agents are denied by default"
    If an `agent_id` is not defined in `agent_identities`, all validation calls return `allowed: False`. Register every agent before deployment.

## Identity Format

```yaml
agent_identities:
  <agent_id>:
    allowed_tools:
      - <tool_name>       # tools this agent may call
    clearance_tags:
      - <data_tag>        # data classifications this agent may access
```

| Field            | Type        | Description                                      |
|------------------|-------------|--------------------------------------------------|
| `allowed_tools`  | `list[str]` | Tool names the agent is permitted to invoke       |
| `clearance_tags` | `list[str]` | Data tags the agent is cleared to handle          |

### Clearance Tag Hierarchies

Clearance tags follow the same hierarchy as policy tags. Granting `personal.pii` implicitly clears the agent for `personal.pii.email`, `personal.pii.ssn`, and all other children:

```yaml
clearance_tags:
  - personal.pii    # covers personal.pii.email, personal.pii.ssn, etc.
  - public
```

## Validation Method

```python
result = ai.validate_agent_identity(
    agent_id,                    # required
    tool_name="send_email",      # optional — check tool access
    data_tags=["personal.pii"],  # optional — check data clearance
)

# result.allowed: bool
# result.reason: str (empty when allowed)
# result.agent_id: str
# result.checked_tool: str | None
# result.checked_tags: list[str]
```

Both `tool_name` and `data_tags` are optional. If you provide both, the agent must be authorized for the tool **and** all listed tags.

!!! tip "Layer with tool contracts"
    Agent identity controls *who* can call a tool. Tool contracts control *what data* the tool can receive and return. Use both for complete coverage. See the [Tool Contracts guide](tool-contracts.md).

## Configuration

```yaml title="safeai.yaml"
agent_identities:
  support-bot:
    allowed_tools:
      - send_email
      - lookup_order
    clearance_tags:
      - personal.pii.email
      - personal.pii.name
      - public

  analytics-bot:
    allowed_tools:
      - query_database
      - generate_report
    clearance_tags:
      - personal.financial
      - aggregate

  admin-bot:
    allowed_tools:
      - "*"               # wildcard — all tools allowed
    clearance_tags:
      - "*"               # wildcard — all data allowed
```

!!! info "Wildcard access"
    Use `"*"` for admin or privileged agents that need unrestricted access. Use sparingly and pair with audit logging.

## See Also

- [API Reference — Agent Identity](../reference/identity.md)
- [Tool Contracts guide](tool-contracts.md) for tool-level data controls
- [Capability Tokens guide](capability-tokens.md) for time-limited access grants
