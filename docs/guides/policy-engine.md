# Policy Engine

The SafeAI policy engine evaluates every request against a set of YAML-defined rules. Policies use priority-based, first-match evaluation: the highest-priority matching rule determines the action. This gives you fine-grained, declarative control over what data flows where, without writing application code.

## Quick Example

```yaml title="safeai.yaml"
policies:
  - name: block-ssn-output
    boundary: output
    priority: 100
    condition:
      data_tags: [personal.pii.ssn]
    action: block
    reason: "SSN must never appear in agent output"
```

```python
from safeai import SafeAI

ai = SafeAI.from_config("safeai.yaml")

result = ai.guard_output("SSN: 123-45-6789")
print(result.action)  # "block"
print(result.reason)  # "SSN must never appear in agent output"
```

## Full Example

```yaml title="safeai.yaml"
policies:
  # High priority — always block secrets
  - name: block-secrets
    boundary: input
    priority: 200
    condition:
      data_tags: [secret]
    action: block
    reason: "Secrets must not enter the pipeline"

  # Medium priority — redact PII on output
  - name: redact-pii-output
    boundary: output
    priority: 100
    condition:
      data_tags: [personal.pii]
    action: redact
    reason: "PII must be redacted before reaching users"

  # Low priority — require approval for financial data
  - name: approve-financial
    boundary: output
    priority: 50
    condition:
      data_tags: [personal.financial]
    action: require_approval
    reason: "Financial data requires human review"

  # Default allow
  - name: allow-all
    boundary: "*"
    priority: 1
    condition:
      data_tags: ["*"]
    action: allow
```

```python
from safeai import SafeAI

ai = SafeAI.from_config("safeai.yaml")

# Triggers "block-secrets" (priority 200)
r1 = ai.scan_input("key=sk-ABCDEF1234567890")
assert r1.action == "block"

# Triggers "redact-pii-output" (priority 100)
r2 = ai.guard_output("Email: alice@example.com")
assert r2.action == "redact"

# Triggers "approve-financial" (priority 50)
r3 = ai.guard_output("Account balance: $52,340.00")
assert r3.action == "require_approval"
```

## Policy Format

Each policy is a dictionary with the following fields:

| Field       | Type       | Description                                             |
|-------------|------------|---------------------------------------------------------|
| `name`      | `str`      | Unique identifier for the rule                          |
| `boundary`  | `str`      | `input`, `output`, `tool_request`, `tool_response`, `*` |
| `priority`  | `int`      | Higher number = evaluated first                         |
| `condition` | `dict`     | Matching criteria (see below)                           |
| `action`    | `str`      | `allow`, `block`, `redact`, `require_approval`          |
| `reason`    | `str`      | Human-readable explanation logged with every decision   |

### Condition Fields

```yaml
condition:
  data_tags: [personal.pii.email, secret.api_key]
  agent_id: "support-bot"
  tool_name: "send_email"
```

All specified condition fields must match for the rule to fire.

## Tag Hierarchies

Tags are dot-separated and match hierarchically. A policy targeting a parent tag automatically matches all children:

```
personal           → matches personal.pii, personal.pii.ssn, personal.financial
personal.pii       → matches personal.pii.ssn, personal.pii.email
personal.financial → matches personal.financial.account_number
secret             → matches secret.api_key, secret.aws_key
```

!!! info "Wildcard tags"
    Use `"*"` in `data_tags` to match any tag. This is useful for default allow/deny rules at the bottom of your policy list.

## Actions

| Action              | Behavior                                                      |
|---------------------|---------------------------------------------------------------|
| `allow`             | Let the data through unchanged                                |
| `block`             | Reject the request; return an error to the caller             |
| `redact`            | Mask the matched values and pass the rest through             |
| `require_approval`  | Pause and queue for human review (see [Approval Workflows](approval-workflows.md)) |

## Hot Reload

Reload policies without restarting your application:

```python
# Reload if the file has changed since last load
ai.reload_policies()

# Force reload regardless of file modification time
ai.force_reload_policies()
```

!!! tip "Watch mode"
    In development, call `ai.reload_policies()` at the start of each request to pick up config changes instantly.

## Configuration

```yaml title="safeai.yaml"
policy_engine:
  evaluation: first_match   # first_match | all_match
  default_action: block     # action when no rule matches
  audit: true               # log every evaluation to audit trail

policies:
  - name: my-rule
    boundary: input
    priority: 100
    condition:
      data_tags: [secret]
    action: block
    reason: "Block all secrets on input"
```

## See Also

- [API Reference — Policy Engine](../reference/policy.md)
- [Approval Workflows guide](approval-workflows.md) for `require_approval` action
- [Tool Contracts guide](tool-contracts.md) for tool-specific policies
