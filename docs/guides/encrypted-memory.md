# Encrypted Memory

SafeAI provides schema-enforced agent memory with field-level encryption. Agents store and retrieve key-value data through `memory_write` and `memory_read`, while sensitive fields are encrypted at rest. Memory schemas define which fields are allowed, their types, encryption requirements, and retention periods.

## Quick Example

```python
from safeai import SafeAI

ai = SafeAI.quickstart()

ai.memory_write("customer_email", "alice@example.com", agent_id="support-bot")
value = ai.memory_read("customer_email", agent_id="support-bot")
print(value)  # "alice@example.com"
```

## Full Example

```yaml title="safeai.yaml"
memory:
  encryption_key_env: SAFEAI_MEMORY_KEY
  default_retention: 24h

  schemas:
    support-bot:
      fields:
        customer_email:
          type: string
          encrypted: true
          retention: 1h
        customer_name:
          type: string
          encrypted: true
          retention: 1h
        ticket_id:
          type: string
          encrypted: false
          retention: 7d
        interaction_summary:
          type: string
          encrypted: false
          retention: 24h
```

```python
from safeai import SafeAI

ai = SafeAI.from_config("safeai.yaml")

# Write memory entries (encrypted fields are encrypted transparently)
ai.memory_write("customer_email", "alice@example.com", agent_id="support-bot")
ai.memory_write("customer_name", "Alice Johnson", agent_id="support-bot")
ai.memory_write("ticket_id", "TKT-42351", agent_id="support-bot")

# Read back — decryption is automatic for the owning agent
email = ai.memory_read("customer_email", agent_id="support-bot")
print(email)  # "alice@example.com"

# Another agent cannot read support-bot's memory
try:
    ai.memory_read("customer_email", agent_id="analytics-bot")
except PermissionError as e:
    print(e)  # "Agent 'analytics-bot' cannot access memory for 'support-bot'"
```

!!! warning "Agent isolation"
    Memory is scoped per agent. An agent can only read and write keys defined in its own schema. Cross-agent access is denied by default.

## Encrypted Memory Handles

For sensitive values that should never be held in plaintext by the agent, use memory handles. The agent receives an opaque handle ID instead of the raw value, and resolves it only when needed:

```python
# Write returns a handle for encrypted fields
handle = ai.memory_write(
    "customer_ssn", "123-45-6789",
    agent_id="support-bot",
    return_handle=True,
)
print(handle)  # MemoryHandle(id="mh-a3f9...", key="customer_ssn")

# Resolve handle when the value is needed
value = ai.resolve_memory_handle(handle.id, agent_id="support-bot")
print(value)  # "123-45-6789"
```

!!! tip "Handles for secrets"
    Memory handles let agents reference sensitive data without holding it in context. Pass the handle ID to tool calls, and resolve it only at the point of use.

## Auto-Expiry

Memory entries expire based on their schema-defined retention. Purge expired entries manually or on a schedule:

```python
# Purge all expired entries across all agents
purged = ai.memory_purge_expired()
print(f"Removed {purged.count} expired entries")

# Purge expired entries for a specific agent
purged = ai.memory_purge_expired(agent_id="support-bot")
```

## Memory Schema Reference

```yaml
memory:
  encryption_key_env: SAFEAI_MEMORY_KEY   # env var holding the encryption key
  default_retention: 24h                  # fallback if field omits retention

  schemas:
    <agent_id>:
      fields:
        <field_name>:
          type: string | int | float | bool | json
          encrypted: true | false
          retention: <duration>           # e.g., 1h, 7d, 30d
```

| Schema Field  | Type     | Description                                           |
|---------------|----------|-------------------------------------------------------|
| `type`        | `str`    | Data type: `string`, `int`, `float`, `bool`, `json`   |
| `encrypted`   | `bool`   | Whether the field is encrypted at rest                 |
| `retention`   | `str`    | How long the value is kept (e.g., `1h`, `7d`, `30d`)  |

## Configuration

```yaml title="safeai.yaml"
memory:
  enabled: true
  backend: sqlite              # sqlite | redis | postgres
  encryption_key_env: SAFEAI_MEMORY_KEY
  default_retention: 24h

  schemas:
    support-bot:
      fields:
        customer_email:
          type: string
          encrypted: true
          retention: 1h
        ticket_id:
          type: string
          encrypted: false
          retention: 7d

    analytics-bot:
      fields:
        report_cache:
          type: json
          encrypted: false
          retention: 12h
```

## See Also

- [API Reference — Encrypted Memory](../reference/memory.md)
- [Capability Tokens guide](capability-tokens.md) for time-limited secret access
- [Agent Identity guide](agent-identity.md) for agent-level access control
