# Configuration

SafeAI supports two configuration paths: keyword arguments for quick programmatic setup, and YAML files for full config-driven deployments. This page covers both approaches and explains the policy engine that powers runtime decisions.

## Scaffold with `safeai init`

Running `safeai init` in your project root creates the following structure:

```
.
├── safeai.yaml              # Main configuration file
├── policies/
│   └── default.yaml         # Default policy rules
├── contracts/
│   └── example.yaml         # Agent contract definitions
├── schemas/
│   └── memory.yaml          # Memory and state schemas
└── agents/
    └── default.yaml         # Agent role definitions
```

Each file is pre-populated with commented examples you can edit immediately.

## quickstart() Keyword Arguments

`SafeAI.quickstart()` accepts keyword arguments that override the defaults without requiring any YAML files:

```python
from safeai import SafeAI

ai = SafeAI.quickstart(
    block_secrets=True,      # Block inputs containing API keys, tokens, passwords
    redact_pii=True,         # Redact PII in outputs (names, emails, phones, etc.)
    block_pii=False,         # Block instead of redact when PII is found
    custom_rules=[           # Additional regex-based rules
        {"pattern": r"INTERNAL-\d{6}", "action": "block", "reason": "Internal ID leak"},
    ],
    audit_path="audit.log",  # Write audit events to a file (default: in-memory only)
)
```

| Parameter       | Type          | Default  | Description                                      |
|-----------------|---------------|----------|--------------------------------------------------|
| `block_secrets` | `bool`        | `True`   | Block inputs that contain detected secrets       |
| `redact_pii`    | `bool`        | `True`   | Redact PII tokens in guarded outputs             |
| `block_pii`     | `bool`        | `False`  | Block outputs entirely when PII is detected      |
| `custom_rules`  | `list[dict]`  | `[]`     | Additional pattern-based scanning rules          |
| `audit_path`    | `str \| None` | `None`   | File path for persistent audit logging           |

!!! tip
    `quickstart()` is ideal for prototyping and single-script use cases. For production deployments with multiple agents or complex policies, use `from_config()` instead.

## from_config() -- Full YAML Configuration

Load configuration from your `safeai.yaml` file:

```python
from safeai import SafeAI

ai = SafeAI.from_config("safeai.yaml")
```

### safeai.yaml Structure

```yaml
version: "0.6"

scanner:
  block_secrets: true
  custom_rules:
    - pattern: "INTERNAL-\\d{6}"
      action: block
      reason: "Internal ID leak"

guardrails:
  redact_pii: true
  block_pii: false

audit:
  enabled: true
  path: "audit.log"

policies:
  path: "policies/"

contracts:
  path: "contracts/"

agents:
  path: "agents/"
```

`from_config()` reads all referenced directories and assembles the full policy engine, contract validator, and agent registry at startup.

## Policy Format

Policies are YAML files evaluated in **priority order, first-match wins**. Each rule specifies a tag pattern, an action, and an optional priority (lower number = higher priority).

```yaml
# policies/default.yaml
rules:
  - tag: "secrets/*"
    action: block
    priority: 1
    reason: "Secrets must never reach the model"

  - tag: "pii/email"
    action: redact
    priority: 10
    reason: "Redact email addresses in output"

  - tag: "pii/*"
    action: redact
    priority: 20
    reason: "Redact all other PII categories"

  - tag: "content/profanity"
    action: block
    priority: 50
    reason: "Block profane content"

  - tag: "*"
    action: allow
    priority: 100
    reason: "Default allow"
```

### Evaluation Order

1. All matching rules are collected based on the detected tags.
2. Rules are sorted by `priority` (ascending -- lowest number first).
3. The **first matching rule** determines the action.
4. If no rule matches, the default action is `allow`.

!!! warning
    Always include a catch-all rule (`tag: "*"`) with the highest priority number as a safety net. Without it, unrecognized tags fall through to the implicit allow, which may not be what you intend.

## Tag Hierarchy

Tags use a slash-separated hierarchy. A parent tag pattern matches all of its children:

| Pattern         | Matches                                              |
|-----------------|------------------------------------------------------|
| `secrets/*`     | `secrets/api_key`, `secrets/token`, `secrets/password` |
| `pii/*`         | `pii/email`, `pii/phone`, `pii/name`, `pii/address`  |
| `pii/email`     | `pii/email` only                                     |
| `*`             | Everything                                           |

This lets you write broad rules for entire categories and override them with specific rules at a lower priority number:

```yaml
rules:
  # Allow email specifically (higher priority)
  - tag: "pii/email"
    action: allow
    priority: 5

  # Block all other PII (lower priority)
  - tag: "pii/*"
    action: block
    priority: 10
```

!!! note
    Priority is about evaluation order, not importance. A rule with `priority: 1` is evaluated **before** a rule with `priority: 10`. Use low numbers for your most specific overrides and high numbers for broad defaults.

## Intelligence Layer Configuration

The intelligence layer provides AI advisory agents for auto-configuring SafeAI, recommending policy improvements, explaining incidents, generating compliance policies, and producing integration code. It is disabled by default and requires a configured AI backend.

```yaml
# safeai.yaml
intelligence:
  enabled: true
  backend:
    provider: ollama              # or "openai-compatible"
    model: llama3.2
    base_url: http://localhost:11434
    api_key_env: null             # env var name (NOT the key itself)
  max_events_per_query: 500
  metadata_only: true             # false = user opts into raw content (air-gapped)
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `intelligence.enabled` | `bool` | `false` | Enable/disable the intelligence layer |
| `intelligence.backend.provider` | `str` | `ollama` | Backend provider (`ollama` or `openai-compatible`) |
| `intelligence.backend.model` | `str` | `llama3.2` | Model name to use |
| `intelligence.backend.base_url` | `str` | `http://localhost:11434` | Backend API URL |
| `intelligence.backend.api_key_env` | `str\|null` | `null` | Environment variable name containing the API key |
| `intelligence.max_events_per_query` | `int` | `500` | Maximum audit events per intelligence query |
| `intelligence.metadata_only` | `bool` | `true` | When true, AI agents only see metadata, never raw content |

!!! warning
    No AI model is bundled with SafeAI. You must have a running model backend (Ollama, OpenAI, etc.) for intelligence commands to work. The rest of SafeAI works fully without any LLM.

See the [Intelligence Layer guide](../guides/intelligence.md) for full usage details.

## Next Steps

- [Quickstart](quickstart.md) -- see configuration in action with live examples.
- Explore the `policies/`, `contracts/`, and `agents/` directories generated by `safeai init` for annotated templates.
- [Intelligence Layer](../guides/intelligence.md) -- AI advisory agents for configuration and understanding.
