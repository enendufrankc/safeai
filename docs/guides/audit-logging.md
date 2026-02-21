# Audit Logging

Every security decision SafeAI makes is logged with full context: the boundary, action taken, matched policy, agent ID, data tags, and a content hash for traceability. You can query the audit trail programmatically or through the CLI to investigate incidents, verify compliance, and understand agent behavior.

## Quick Example

```python
from safeai import SafeAI

ai = SafeAI.from_config("safeai.yaml")

# Query recent blocked inputs
entries = ai.query_audit(boundary="input", action="block")
for e in entries:
    print(f"[{e.timestamp}] {e.agent_id}: {e.reason}")
```

## Full Example

```python
from safeai import SafeAI

ai = SafeAI.from_config("safeai.yaml")

# Trigger some auditable events
ai.scan_input("API_KEY=sk-ABCDEF1234567890", agent_id="data-bot")
ai.guard_output("SSN: 123-45-6789", agent_id="support-bot")

# Query with multiple filters
entries = ai.query_audit(
    boundary="input",
    action="block",
    agent_id="data-bot",
    last="1h",
)

for entry in entries:
    print(f"Timestamp:  {entry.timestamp}")
    print(f"Boundary:   {entry.boundary}")
    print(f"Action:     {entry.action}")
    print(f"Agent:      {entry.agent_id}")
    print(f"Policy:     {entry.policy_name}")
    print(f"Tags:       {entry.data_tags}")
    print(f"Reason:     {entry.reason}")
    print(f"Hash:       {entry.content_hash}")
    print(f"Session:    {entry.session_id}")
    print("---")
```

!!! info "Content hashes, not content"
    The audit log stores a SHA-256 hash of the scanned content, not the content itself. This allows you to verify that a specific input triggered a decision without storing sensitive data in your logs.

## Audit Entry Fields

| Field          | Type       | Description                                          |
|----------------|------------|------------------------------------------------------|
| `timestamp`    | `datetime` | When the decision was made                           |
| `boundary`     | `str`      | `input`, `output`, `tool_request`, `tool_response`   |
| `action`       | `str`      | `allow`, `block`, `redact`, `require_approval`       |
| `policy_name`  | `str`      | Name of the matched policy rule                      |
| `agent_id`     | `str`      | Agent that triggered the evaluation                  |
| `data_tags`    | `list`     | Data classification tags detected                    |
| `reason`       | `str`      | Human-readable explanation from the policy           |
| `content_hash` | `str`      | SHA-256 hash of the scanned content                  |
| `session_id`   | `str`      | Session identifier for grouping related events       |
| `phase`        | `str`      | Processing phase (e.g., `scan`, `guard`, `intercept`)|

## Query Filters

All filters are optional. Combine them to narrow results:

```python
entries = ai.query_audit(
    boundary="output",               # filter by boundary
    action="redact",                 # filter by action taken
    agent_id="support-bot",          # filter by agent
    data_tags=["personal.pii"],      # filter by detected tags
    policy_name="redact-pii-output", # filter by policy rule
    session_id="sess-abc123",        # filter by session
    phase="guard",                   # filter by processing phase
    last="1h",                       # time window: "5m", "1h", "24h", "7d"
    limit=50,                        # max entries returned
)
```

## CLI Commands

Query the audit trail from the terminal:

```bash
# Recent blocked inputs
safeai logs --boundary input --action block --last 1h

# All events for a specific agent
safeai logs --agent support-bot --last 24h

# Filter by data tag
safeai logs --tag personal.pii --last 7d

# Export as JSON
safeai logs --boundary output --action redact --format json > audit.json

# Count events by action
safeai logs --last 24h --count-by action
```

### Example CLI Output

```
$ safeai logs --boundary input --action block --last 1h
TIMESTAMP            AGENT        POLICY          TAGS                 REASON
2026-02-21 14:32:01  data-bot     block-secrets   secret.api_key       Secrets must not enter the pipeline
2026-02-21 14:28:15  support-bot  block-secrets   secret.database_url  Secrets must not enter the pipeline
```

## Configuration

```yaml title="safeai.yaml"
audit:
  enabled: true
  backend: sqlite          # sqlite | postgres | file
  retention: 90d           # how long to keep audit entries
  hash_algorithm: sha256   # sha256 | sha512
  include_content: false   # never store raw content (default)

  file:                    # settings when backend is "file"
    path: ./logs/audit.jsonl
    rotate: daily
```

| Setting           | Default   | Description                                    |
|-------------------|-----------|------------------------------------------------|
| `backend`         | `sqlite`  | Storage backend for audit entries               |
| `retention`       | `90d`     | Auto-delete entries older than this             |
| `hash_algorithm`  | `sha256`  | Hash function for content fingerprinting        |
| `include_content` | `false`   | Store raw content (not recommended)             |

!!! warning "Do not enable `include_content` in production"
    Storing raw content in audit logs defeats the purpose of scanning for secrets and PII. Use content hashes to correlate events without retaining sensitive data.

## See Also

- [API Reference — Audit Logging](../reference/audit.md)
- [Policy Engine guide](policy-engine.md) for defining rules that produce audit entries
- [Approval Workflows guide](approval-workflows.md) for tracking approval decisions
