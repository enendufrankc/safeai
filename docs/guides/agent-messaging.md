# Agent Messaging

SafeAI enforces security policies on agent-to-agent communication. When one agent sends a message to another, `intercept_agent_message` scans the content for secrets and PII, evaluates policies, and can block, redact, or route the message through an approval workflow. This prevents sensitive data from leaking across agent boundaries.

## Quick Example

```python
from safeai import SafeAI

ai = SafeAI.from_config("safeai.yaml")

result = ai.intercept_agent_message(
    message="Customer email is alice@example.com",
    source_agent_id="support-bot",
    destination_agent_id="analytics-bot",
)
print(result.action)     # "redact"
print(result.safe_text)  # "Customer email is [EMAIL REDACTED]"
```

## Full Example

```yaml title="safeai.yaml"
policies:
  - name: block-secrets-between-agents
    boundary: agent_message
    priority: 200
    condition:
      data_tags: [secret]
    action: block
    reason: "Secrets must not pass between agents"

  - name: redact-pii-between-agents
    boundary: agent_message
    priority: 100
    condition:
      data_tags: [personal.pii]
    action: redact
    reason: "PII must be redacted in inter-agent messages"

  - name: approve-financial-between-agents
    boundary: agent_message
    priority: 50
    condition:
      data_tags: [personal.financial]
    action: require_approval
    reason: "Financial data transfer requires approval"
```

```python
from safeai import SafeAI

ai = SafeAI.from_config("safeai.yaml")

# Message with PII — gets redacted
r1 = ai.intercept_agent_message(
    message="User phone: (555) 867-5309, email: alice@example.com",
    source_agent_id="support-bot",
    destination_agent_id="analytics-bot",
)
assert r1.action == "redact"
print(r1.safe_text)
# "User phone: [PHONE REDACTED], email: [EMAIL REDACTED]"

# Message with a secret — blocked entirely
r2 = ai.intercept_agent_message(
    message="Use this key: sk-ABCDEF1234567890",
    source_agent_id="deploy-bot",
    destination_agent_id="monitor-bot",
)
assert r2.action == "block"
print(r2.reason)
# "Secrets must not pass between agents"

# Message with financial data — routed to approval
r3 = ai.intercept_agent_message(
    message="Transfer $50,000 from account 1234 to 5678",
    source_agent_id="finance-bot",
    destination_agent_id="executor-bot",
)
assert r3.action == "require_approval"
print(r3.request_id)  # "apr-c4e2..."
```

!!! warning "Messages are scanned like any other boundary"
    Agent messages go through the same secret detection, PII detection, and policy evaluation as `scan_input` and `guard_output`. The `agent_message` boundary lets you write policies specific to inter-agent traffic.

## How It Works

```
Source Agent ──► intercept_agent_message() ──► Policy Engine ──► Destination Agent
                        │                          │
                    Scan for                   Evaluate rules
                  secrets & PII              (block/redact/approve)
```

1. The source agent calls `intercept_agent_message` with the message and both agent IDs.
2. SafeAI scans the message for secrets and PII, producing data tags.
3. The policy engine evaluates rules with `boundary: agent_message`.
4. Based on the matched policy, the message is allowed, redacted, blocked, or queued for approval.

## Approval Workflows for Messages

When a policy returns `require_approval`, the message is held until a human approves it:

```python
result = ai.intercept_agent_message(
    message="Account balance: $52,340.00",
    source_agent_id="finance-bot",
    destination_agent_id="report-bot",
)

if result.action == "require_approval":
    # Message is queued — notify approver
    print(f"Approval needed: {result.request_id}")

    # Approver reviews and approves
    ai.approve_request(result.request_id, approver="ops-lead")
```

See the [Approval Workflows guide](approval-workflows.md) for full details.

## Configuration

```yaml title="safeai.yaml"
agent_messaging:
  enabled: true
  scan_secrets: true       # scan messages for secrets
  scan_pii: true           # scan messages for PII
  default_action: allow    # action when no policy matches

policies:
  - name: block-secrets-between-agents
    boundary: agent_message
    priority: 200
    condition:
      data_tags: [secret]
    action: block
    reason: "Secrets must not pass between agents"
```

| Setting          | Default | Description                                      |
|------------------|---------|--------------------------------------------------|
| `scan_secrets`   | `true`  | Run secret detection on messages                 |
| `scan_pii`       | `true`  | Run PII detection on messages                    |
| `default_action` | `allow` | Action when no policy matches the message        |

## See Also

- [API Reference — Agent Messaging](../reference/safeai.md)
- [Policy Engine guide](policy-engine.md) for the `agent_message` boundary
- [Agent Identity guide](agent-identity.md) for agent-level access control
- [Approval Workflows guide](approval-workflows.md) for message approval
