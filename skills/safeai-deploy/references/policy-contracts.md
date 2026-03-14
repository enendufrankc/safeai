# SafeAI Policy & Contract Reference

## Table of Contents
1. [Policy File Schema](#policy-file-schema)
2. [Policy Actions](#policy-actions)
3. [Data Tags (built-in detectors)](#data-tags-built-in-detectors)
4. [Example Policy Files](#example-policy-files)
5. [Contract File Schema](#contract-file-schema)
6. [Example Contract Files](#example-contract-files)
7. [Agent Identity Schema](#agent-identity-schema)
8. [Memory Schema](#memory-schema)

---

## Policy File Schema

```yaml
version: v1alpha1
policies:
  - name: string               # Unique policy name
    boundary:                  # Which boundaries to apply to
      - input                  # scan_input calls
      - action                 # intercept_tool_request calls
      - output                 # guard_output calls
    priority: integer          # Lower = evaluated first (default: 100)
    condition:
      data_tags: [string]      # Tags detected by classifier (any match triggers)
      tool_name: string        # Exact tool name (action boundary only)
      agent_id: string         # Exact agent ID
    action: allow|block|redact|require_approval
    reason: string             # Human-readable explanation (shown in audit log)
    fallback_template: string  # Output replacement text (for redact/block)
```

---

## Policy Actions

| Action | Behavior |
|--------|---------|
| `allow` | Passes the data through unchanged |
| `block` | Rejects the request; returns error to agent |
| `redact` | Replaces detected values with `[REDACTED]` or `fallback_template` |
| `require_approval` | Queues for human approval; blocks until approved or TTL expires |

**Evaluation:** First-match, priority-ordered. Default-deny if no policy matches.

---

## Data Tags (built-in detectors)

| Tag | Detected Pattern |
|-----|-----------------|
| `secret.api_key` | API keys (OpenAI, Anthropic, AWS, etc.) |
| `secret.password` | Password fields |
| `secret.private_key` | PEM private keys |
| `secret.aws_access_key` | AWS access key IDs |
| `secret.aws_secret_key` | AWS secret access keys |
| `pii.email` | Email addresses |
| `pii.phone` | Phone numbers |
| `pii.ssn` | US Social Security Numbers |
| `pii.credit_card` | Credit card numbers |
| `pii.ip_address` | IPv4 addresses |
| `pii.name` | Person names (heuristic) |
| `pii.address` | Physical addresses |
| `finance.routing_number` | Bank routing numbers |
| `finance.account_number` | Bank account numbers |
| `health.dob` | Dates of birth |

Custom tags can be added via plugins (see `plugins/example.py`).

---

## Example Policy Files

### Block all secrets on input

```yaml
version: v1alpha1
policies:
  - name: block-secrets-input
    boundary: [input]
    priority: 10
    condition:
      data_tags: [secret.api_key, secret.private_key, secret.aws_secret_key]
    action: block
    reason: "Secrets must not enter the AI boundary"
```

### Redact PII from model output

```yaml
version: v1alpha1
policies:
  - name: redact-pii-output
    boundary: [output]
    priority: 20
    condition:
      data_tags: [pii.email, pii.phone, pii.ssn, pii.credit_card]
    action: redact
    reason: "PII must be redacted from model responses"
```

### Require approval for destructive bash commands

```yaml
version: v1alpha1
policies:
  - name: approve-destructive-bash
    boundary: [action]
    priority: 5
    condition:
      tool_name: Bash
      data_tags: [command.destructive]
    action: require_approval
    reason: "Destructive shell commands require human approval"
```

### Healthcare compliance policy set

```yaml
version: v1alpha1
policies:
  - name: hipaa-phi-block
    boundary: [input, output]
    priority: 1
    condition:
      data_tags: [pii.ssn, health.dob, pii.name, pii.address]
    action: block
    reason: "PHI must not cross AI boundary (HIPAA)"

  - name: hipaa-allow-non-phi
    boundary: [input, output]
    priority: 1000
    condition: {}
    action: allow
    reason: "Allow non-PHI data"
```

---

## Contract File Schema

```yaml
version: v1alpha1
contract:
  tool_name: string           # Exact tool name this contract applies to
  description: string         # Human-readable description
  accepts:
    tags: [string]            # Data tags this tool accepts
    fields: [string]          # Specific field names accepted
  emits:
    tags: [string]            # Data tags this tool may produce
    fields: [string]          # Specific field names emitted
  stores:
    fields: [string]          # Fields persisted by this tool
    retention: string         # Retention duration (e.g., 30d, 90d, forever)
  side_effects:
    reversible: boolean       # Whether the action can be undone
    requires_approval: boolean # Whether this tool requires explicit approval
```

---

## Example Contract Files

### Email sender contract

```yaml
version: v1alpha1
contract:
  tool_name: send_email
  description: Sends an email to one or more recipients
  accepts:
    tags: [pii.email]
    fields: [to, cc, bcc, subject, body]
  emits:
    tags: []
    fields: [message_id, sent_at]
  stores:
    fields: [to, subject, body]
    retention: 90d
  side_effects:
    reversible: false
    requires_approval: true
```

### File write contract

```yaml
version: v1alpha1
contract:
  tool_name: Write
  description: Writes content to a file
  accepts:
    tags: []
    fields: [file_path, content]
  emits:
    tags: []
    fields: [bytes_written]
  stores:
    fields: [file_path]
    retention: forever
  side_effects:
    reversible: true
    requires_approval: false
```

### Database query contract

```yaml
version: v1alpha1
contract:
  tool_name: sql_query
  description: Executes a SQL query
  accepts:
    tags: []
    fields: [query, parameters]
  emits:
    tags: [pii.email, pii.name, pii.phone]
    fields: [rows, columns]
  stores:
    fields: []
    retention: 0d
  side_effects:
    reversible: false
    requires_approval: false
```

---

## Agent Identity Schema

```yaml
version: v1alpha1
agents:
  - id: string                 # Unique agent identifier
    name: string               # Display name
    clearance_tags: [string]   # Data tags this agent is allowed to see
    tools:
      - name: string           # Tool name
        category: string       # Tool category for policy routing
```

### Example

```yaml
version: v1alpha1
agents:
  - id: claude-code
    name: Claude Code
    clearance_tags: [secret.api_key]
    tools:
      - name: Bash
        category: shell
      - name: Write
        category: file_write
      - name: Read
        category: file_read
```

---

## Memory Schema

```yaml
version: v1alpha1
fields:
  - name: string               # Field name in memory store
    type: string               # Data type (string, integer, float, boolean)
    tags: [string]             # Data classification tags
    retention: string          # Retention duration
    encrypted: boolean         # Whether to encrypt at rest
```

### Example

```yaml
version: v1alpha1
fields:
  - name: user_email
    type: string
    tags: [pii.email]
    retention: 30d
    encrypted: true

  - name: session_id
    type: string
    tags: []
    retention: 24h
    encrypted: false
```
