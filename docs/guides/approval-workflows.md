# Approval Workflows

When a policy evaluates to `require_approval`, SafeAI pauses the operation and queues it for human review. Approvers can list, approve, or deny pending requests through the Python API or the CLI. This gives you a human-in-the-loop checkpoint for high-risk actions without changing your agent code.

## Quick Example

```python
from safeai import SafeAI

ai = SafeAI.from_config("safeai.yaml")

# An output triggers a require_approval policy
result = ai.guard_output("Wire transfer: $50,000 to account 9876543210")
print(result.action)      # "require_approval"
print(result.request_id)  # "apr-7f3a..."

# Approver reviews and approves
ai.approve_request(result.request_id, approver="ops-lead")
```

## Full Example

```yaml title="safeai.yaml"
policies:
  - name: approve-large-transactions
    boundary: output
    priority: 100
    condition:
      data_tags: [personal.financial]
    action: require_approval
    reason: "Financial data requires human sign-off"
```

```python
from safeai import SafeAI

ai = SafeAI.from_config("safeai.yaml")

# Step 1 — Agent produces output that triggers approval
result = ai.guard_output(
    "Transfer $50,000 from account 1234 to account 5678",
    agent_id="finance-bot",
)
assert result.action == "require_approval"
request_id = result.request_id

# Step 2 — List all pending approvals
pending = ai.list_approval_requests(status="pending")
for req in pending:
    print(f"  [{req.id}] {req.agent_id}: {req.reason}")

# Step 3 — Approve or deny
ai.approve_request(request_id, approver="ops-lead", comment="Verified amount")
# or
# ai.deny_request(request_id, approver="ops-lead", comment="Amount exceeds limit")

# Step 4 — Check updated status
req = ai.get_approval_request(request_id)
print(req.status)        # "approved"
print(req.approved_by)   # "ops-lead"
print(req.resolved_at)   # datetime
```

!!! info "Non-blocking by design"
    The `require_approval` action does not block your application process. The request is queued and your code receives the `request_id` immediately. Poll or use webhooks to check resolution status.

## CLI Commands

Manage approvals from the terminal without writing Python:

```bash
# List pending approvals
safeai approvals list
safeai approvals list --status pending --agent finance-bot

# Approve a request
safeai approvals approve apr-7f3a --approver ops-lead --comment "Looks good"

# Deny a request
safeai approvals deny apr-7f3a --approver ops-lead --comment "Amount too high"

# Show details for a specific request
safeai approvals show apr-7f3a
```

### Example CLI Output

```
$ safeai approvals list --status pending
ID          AGENT         BOUNDARY  REASON                              CREATED
apr-7f3a    finance-bot   output    Financial data requires sign-off    2 min ago
apr-9c1b    support-bot   output    PII export requires approval        15 min ago
```

## TTL and Deduplication

Approval requests have a configurable time-to-live. Expired requests are automatically denied. Duplicate requests within a deduplication window are collapsed into one.

```yaml title="safeai.yaml"
approval:
  ttl: 30m               # requests expire after 30 minutes
  dedup_window: 5m        # identical requests within 5 min are merged
  default_action: deny    # action when TTL expires without resolution
```

| Setting          | Default | Description                                           |
|------------------|---------|-------------------------------------------------------|
| `ttl`            | `1h`    | Time before an unresolved request is auto-denied      |
| `dedup_window`   | `5m`    | Window for collapsing duplicate requests               |
| `default_action` | `deny`  | Action taken when a request expires                   |

!!! warning "Expired requests are denied"
    If no human acts within the TTL, the request resolves as denied. Set `default_action: allow` only if your threat model permits it.

## Configuration

```yaml title="safeai.yaml"
approval:
  enabled: true
  ttl: 30m
  dedup_window: 5m
  default_action: deny
  notifiers:
    - type: webhook
      url: https://hooks.slack.com/services/T00/B00/xxxxx
    - type: email
      to: ops-team@company.com

policies:
  - name: approve-financial
    boundary: output
    priority: 100
    condition:
      data_tags: [personal.financial]
    action: require_approval
    reason: "Financial data requires human sign-off"
```

## See Also

- [API Reference — Approval Workflows](../reference/approval.md)
- [Policy Engine guide](policy-engine.md) for `require_approval` action
- [Audit Logging guide](audit-logging.md) for tracking approval decisions
