# Tool Contracts

Tool contracts declare what data each tool is allowed to accept and emit. Before a tool call executes, SafeAI validates the request against the contract and strips unauthorized fields from the response. This prevents tools from receiving data they should not see and stops sensitive fields from leaking back to the agent.

## Quick Example

```python
from safeai import SafeAI

ai = SafeAI.from_config("safeai.yaml")

# Validate that "send_email" is allowed to receive PII-tagged data
result = ai.validate_tool_request("send_email", data_tags=["personal.pii.email"])
print(result.allowed)  # True
```

## Full Example

```yaml title="safeai.yaml"
tool_contracts:
  send_email:
    allowed_request_tags:
      - personal.pii.email
      - personal.pii.name
    allowed_response_fields:
      - status
      - message_id

  query_database:
    allowed_request_tags:
      - personal.financial
    allowed_response_fields:
      - rows
      - row_count
```

```python
from safeai import SafeAI

ai = SafeAI.from_config("safeai.yaml")

# --- Request validation ---
# Allowed: email tool receiving email data
r1 = ai.validate_tool_request("send_email", data_tags=["personal.pii.email"])
assert r1.allowed is True

# Denied: email tool receiving financial data
r2 = ai.validate_tool_request("send_email", data_tags=["personal.financial"])
assert r2.allowed is False
print(r2.reason)  # "Tag 'personal.financial' not in allowed_request_tags for send_email"

# --- Full request interception ---
intercepted = ai.intercept_tool_request(
    tool_name="send_email",
    payload={"to": "alice@example.com", "subject": "Invoice", "body": "..."},
    data_tags=["personal.pii.email"],
)
assert intercepted.action == "allow"

# --- Response interception ---
raw_response = {
    "status": "sent",
    "message_id": "msg-12345",
    "internal_trace_id": "x-trace-9999",  # not in allowed_response_fields
}

filtered = ai.intercept_tool_response("send_email", raw_response)
print(filtered.safe_response)
# {"status": "sent", "message_id": "msg-12345"}
# internal_trace_id has been stripped
```

!!! warning "Unlisted fields are stripped"
    Any response field not explicitly listed in `allowed_response_fields` is removed before the agent sees it. This is a deny-by-default posture for tool responses.

## Contract Format

```yaml
tool_contracts:
  <tool_name>:
    allowed_request_tags:
      - <data_tag>       # tags this tool is permitted to receive
    allowed_response_fields:
      - <field_name>     # top-level fields the agent may see
```

| Field                    | Type        | Description                                         |
|--------------------------|-------------|-----------------------------------------------------|
| `allowed_request_tags`   | `list[str]` | Data tags the tool may receive in requests           |
| `allowed_response_fields`| `list[str]` | Response fields visible to the agent after filtering |

## Interception Methods

### `validate_tool_request`

Lightweight check that returns `allowed: True/False` without modifying data:

```python
result = ai.validate_tool_request(tool_name, data_tags=["personal.pii"])
if not result.allowed:
    print(result.reason)
```

### `intercept_tool_request`

Full interception that validates tags and scans the payload for secrets/PII:

```python
result = ai.intercept_tool_request(
    tool_name="send_email",
    payload={"to": "alice@example.com", "body": "..."},
    data_tags=["personal.pii.email"],
)
# result.action: "allow" | "block"
# result.payload: sanitized payload (if allowed)
```

### `intercept_tool_response`

Filters the tool response to only include allowed fields:

```python
result = ai.intercept_tool_response("send_email", raw_response)
# result.safe_response: dict with only allowed fields
# result.stripped_fields: list of field names that were removed
```

!!! tip "Combine with agent identity"
    Tool contracts define what data a tool may handle. Agent identity defines which agents may call which tools. Use both together for defense in depth. See the [Agent Identity guide](agent-identity.md).

## Configuration

```yaml title="safeai.yaml"
tool_contracts:
  send_email:
    allowed_request_tags:
      - personal.pii.email
      - personal.pii.name
    allowed_response_fields:
      - status
      - message_id

  query_database:
    allowed_request_tags:
      - personal.financial
    allowed_response_fields:
      - rows
      - row_count

  web_search:
    allowed_request_tags:
      - public
    allowed_response_fields:
      - results
      - total_count
```

## See Also

- [API Reference — Tool Contracts](../reference/contracts.md)
- [Agent Identity guide](agent-identity.md) for agent-level tool binding
- [Policy Engine guide](policy-engine.md) for data-tag-based rules
