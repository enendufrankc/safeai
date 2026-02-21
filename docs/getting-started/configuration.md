# Configuration

SafeAI can configure itself automatically using the intelligence layer, or you can set everything up manually for full control. This page covers both paths, starting with the easiest.

## The Easiest Way: `safeai init` + Intelligence Auto-Config

The fastest way to a production-ready configuration is to scaffold your project and let the intelligence layer figure out the right policies for you. No YAML editing required.

### Step 1: Initialize and configure

```bash
safeai init
```

The interactive CLI scaffolds your project and walks you through setting up the intelligence layer — no YAML editing needed:

```
SafeAI initialized
  created: safeai.yaml
  created: policies/default.yaml
  created: contracts/example.yaml
  ...

Intelligence Layer Setup
SafeAI can use an AI backend to auto-generate policies,
explain incidents, and recommend improvements.

Enable the intelligence layer? [Y/n]: Y

Choose your AI backend:
  1. Ollama (local, free — no API key needed)
  2. OpenAI
  3. Anthropic
  4. Google Gemini
  5. Mistral
  6. Groq
  7. Azure OpenAI
  8. Cohere
  9. Together AI
  10. Fireworks AI
  11. DeepSeek
  12. Other (any OpenAI-compatible endpoint)

Select provider [1]: 1

Intelligence layer configured!
  provider: ollama
  model:    llama3.2
```

The CLI writes the intelligence configuration to `safeai.yaml` automatically.

### Step 2: Auto-generate policies

```bash
safeai intelligence auto-config --path . --apply
```

The intelligence layer analyzes your project structure and generates tailored policies, contracts, and agent identities. Review the output, tweak if needed, and you're done.

!!! tip
    This is the recommended path for most users. You can always refine later using `safeai intelligence recommend` or by editing the generated YAML files.

!!! warning
    No AI model is bundled with SafeAI. You must have a running model backend (Ollama, OpenAI, etc.) for intelligence commands to work. The rest of SafeAI works fully without any LLM.

See the [Intelligence Layer guide](../guides/intelligence.md) for full usage details including `recommend`, `explain`, and `compliance` commands.

### Intelligence configuration reference

If you ever need to edit the intelligence config manually, here are the fields `safeai init` writes to `safeai.yaml`:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `intelligence.enabled` | `bool` | `false` | Enable/disable the intelligence layer |
| `intelligence.backend.provider` | `str` | `ollama` | Backend provider (`ollama` or `openai-compatible`) |
| `intelligence.backend.model` | `str` | `llama3.2` | Model name to use |
| `intelligence.backend.base_url` | `str` | `http://localhost:11434` | Backend API URL |
| `intelligence.backend.api_key_env` | `str\|null` | `null` | Environment variable name containing the API key |
| `intelligence.max_events_per_query` | `int` | `500` | Maximum audit events per intelligence query |
| `intelligence.metadata_only` | `bool` | `true` | When true, AI agents only see metadata, never raw content |

## `quickstart()` -- Programmatic Setup

If you prefer to configure SafeAI in code rather than through the CLI, `SafeAI.quickstart()` accepts keyword arguments that override the defaults without requiring any YAML files:

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
    `quickstart()` is ideal for prototyping and single-script use cases. For production deployments with multiple agents or complex policies, use `from_config()` or the intelligence auto-config path instead.

## `from_config()` -- Full YAML Configuration (Advanced)

For users who want fine-grained manual control over every setting, load configuration from your `safeai.yaml` file directly:

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

## Next Steps

- [Quickstart](quickstart.md) -- see configuration in action with live examples.
- Explore the `policies/`, `contracts/`, and `agents/` directories generated by `safeai init` for annotated templates.
- [Intelligence Layer](../guides/intelligence.md) -- AI advisory agents for configuration, recommendations, and incident analysis.
