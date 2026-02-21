# Capability Tokens

Capability tokens give agents scoped, time-limited access to tools and actions without exposing raw credentials. You issue a token with a specific agent, tool, action set, and TTL. The agent presents the token when making requests, and SafeAI validates it at the boundary. When the token expires or is revoked, access stops immediately.

## Quick Example

```python
from safeai import SafeAI

ai = SafeAI.quickstart()

token = ai.issue_capability_token(
    agent_id="support-bot",
    tool_name="send_email",
    actions=["read", "send"],
    ttl="10m",
)
print(token.id)  # "ctk-8b2f..."

result = ai.validate_capability_token(token.id, agent_id="support-bot", tool_name="send_email")
print(result.valid)  # True
```

## Full Example

```python
from safeai import SafeAI

ai = SafeAI.quickstart()

# Step 1 — Issue a token for a specific agent, tool, and action set
token = ai.issue_capability_token(
    agent_id="support-bot",
    tool_name="send_email",
    actions=["read", "send"],
    ttl="10m",
)
print(f"Token: {token.id}")
print(f"Expires: {token.expires_at}")

# Step 2 — Agent presents the token when calling the tool
result = ai.validate_capability_token(
    token.id,
    agent_id="support-bot",
    tool_name="send_email",
)
assert result.valid is True
assert "send" in result.actions

# Step 3 — Wrong agent or wrong tool is rejected
bad_result = ai.validate_capability_token(
    token.id,
    agent_id="analytics-bot",  # not the token holder
    tool_name="send_email",
)
assert bad_result.valid is False
print(bad_result.reason)  # "Token not issued to agent 'analytics-bot'"

# Step 4 — Revoke the token early
ai.revoke_capability_token(token.id)

revoked_result = ai.validate_capability_token(
    token.id,
    agent_id="support-bot",
    tool_name="send_email",
)
assert revoked_result.valid is False
print(revoked_result.reason)  # "Token has been revoked"
```

!!! danger "Agents never see raw credentials"
    Capability tokens are an abstraction layer. The agent receives a token ID, not the underlying API key or database password. The credential is resolved server-side when the tool executes.

## Token Lifecycle

```
issue  ──►  active  ──►  expired (automatic)
                │
                └──────►  revoked (manual)
```

| State     | Description                                     |
|-----------|-------------------------------------------------|
| `active`  | Token is valid and can be used                  |
| `expired` | TTL has elapsed; token is no longer accepted     |
| `revoked` | Manually revoked before expiry                  |

## API Methods

### `issue_capability_token`

Create a new token:

```python
token = ai.issue_capability_token(
    agent_id="support-bot",       # required — which agent holds this token
    tool_name="send_email",       # required — which tool the token grants access to
    actions=["read", "send"],     # required — permitted actions
    ttl="10m",                    # required — time-to-live (e.g., "5m", "1h", "24h")
    metadata={"ticket": "TKT-1"} # optional — arbitrary context
)
```

### `validate_capability_token`

Check whether a token is valid for a given agent and tool:

```python
result = ai.validate_capability_token(
    token_id,                     # required
    agent_id="support-bot",       # required
    tool_name="send_email",       # required
)
# result.valid: bool
# result.actions: list[str] (if valid)
# result.reason: str (if invalid)
```

### `revoke_capability_token`

Immediately invalidate a token:

```python
ai.revoke_capability_token(token_id)
```

!!! tip "Revoke on task completion"
    Issue tokens at the start of a task and revoke them when the task completes. This limits the blast radius if a token is intercepted.

## Configuration

```yaml title="safeai.yaml"
capability_tokens:
  enabled: true
  max_ttl: 1h              # maximum allowed TTL for any token
  default_ttl: 10m          # TTL used when not specified
  storage: memory           # memory | redis | postgres
  audit: true               # log token issue, validate, and revoke events
```

| Setting       | Default  | Description                                      |
|---------------|----------|--------------------------------------------------|
| `max_ttl`     | `1h`     | Upper bound on token lifetime                    |
| `default_ttl` | `10m`    | TTL applied when `ttl` is omitted on issue       |
| `storage`     | `memory` | Backend for token state                          |
| `audit`       | `true`   | Log token events to the audit trail              |

## See Also

- [API Reference — Capability Tokens](../reference/secrets.md)
- [Agent Identity guide](agent-identity.md) for static tool/data bindings
- [Audit Logging guide](audit-logging.md) for tracking token events
