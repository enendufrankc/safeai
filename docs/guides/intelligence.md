# Intelligence Layer

SafeAI's intelligence layer provides 5 AI advisory agents that help you **configure** and **understand** SafeAI. The agents generate configuration files, explain incidents, recommend policy improvements, produce compliance policy sets, and generate framework integration code.

!!! warning "AI outside the enforcement loop"
    The intelligence layer is purely advisory. AI generates configs and explanations -- SafeAI enforces deterministically. AI never makes runtime enforcement decisions.

---

## Core Constraints

| Constraint | What it means |
|---|---|
| **Metadata-only default** | AI agents never see raw protected data (secrets, PII values). They work on audit aggregates, code structure, and tool definitions. |
| **BYOM (Bring Your Own Model)** | You configure your own AI backend (Ollama, OpenAI, Anthropic, etc.). SafeAI doesn't bundle or mandate any provider. |
| **AI outside enforcement** | AI generates configs, SafeAI enforces deterministically. AI advises on audit events after the fact. |
| **Human approval** | All AI-generated configs are written to a staging directory for human review before taking effect. |

---

## Configuration

Enable the intelligence layer in `safeai.yaml`:

```yaml
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

### Backend Options

=== "Ollama (local, no API key)"

    ```yaml
    intelligence:
      enabled: true
      backend:
        provider: ollama
        model: llama3.2
        base_url: http://localhost:11434
    ```

=== "OpenAI"

    ```yaml
    intelligence:
      enabled: true
      backend:
        provider: openai-compatible
        model: gpt-4o
        base_url: https://api.openai.com/v1
        api_key_env: OPENAI_API_KEY
    ```

=== "Anthropic"

    ```yaml
    intelligence:
      enabled: true
      backend:
        provider: openai-compatible
        model: claude-sonnet-4-20250514
        base_url: https://api.anthropic.com/v1
        api_key_env: ANTHROPIC_API_KEY
    ```

=== "Programmatic"

    ```python
    from safeai import SafeAI
    from safeai.intelligence import OpenAICompatibleBackend

    sai = SafeAI.quickstart()
    sai.register_ai_backend("my-llm", OpenAICompatibleBackend(
        model="gpt-4o",
        api_key="sk-...",
        base_url="https://api.openai.com/v1",
    ))
    ```

!!! tip
    The `api_key_env` field is the **name of an environment variable**, not the key itself. SafeAI reads the key from your environment at runtime.

---

## The 5 Agents

### Auto-Config

Analyzes your project's codebase structure (file names, imports, class/function names, dependencies) and generates a complete SafeAI configuration.

```bash
safeai intelligence auto-config --path . --output-dir .safeai-generated
```

What it reads: file paths, function signatures (via `ast`), imports, `pyproject.toml` deps.
What it produces: `safeai.yaml`, policies, contracts, identities.

### Recommender

Reads audit event aggregates (counts by action, boundary, policy, agent, tool, tag) and suggests policy improvements.

```bash
safeai intelligence recommend --since 7d --output-dir .safeai-generated
```

What it reads: audit aggregates (counts only, no individual events).
What it produces: suggested policy YAML, gap report.

### Incident Response

Classifies and explains a security event, with optional remediation suggestions.

```bash
safeai intelligence explain <event_id>
```

What it reads: single sanitized event + up to 5 surrounding events (metadata only).
What it produces: classification, explanation, optional policy patch.

### Compliance

Maps regulatory frameworks (HIPAA, PCI-DSS, SOC2, GDPR) to SafeAI policy rules.

```bash
safeai intelligence compliance --framework hipaa --output-dir .safeai-generated
```

What it reads: built-in compliance framework requirements, current config structure.
What it produces: compliance policy set, gap analysis report.

### Integration

Generates framework-specific integration code for connecting SafeAI to your target framework.

```bash
safeai intelligence integrate --target langchain --path . --output-dir .safeai-generated
```

What it reads: target framework name, project structure (file names, deps).
What it produces: integration code (hooks, adapters, config).

---

## What the Agents Never See

None of the agents see:

- Secret values
- PII content
- Raw input/output text
- Matched regex values
- Capability token IDs

The `MetadataSanitizer` strips all banned metadata keys before any data enters an AI prompt. Banned keys include: `secret_key`, `capability_token_id`, `matched_value`, `raw_content`, `raw_input`, `raw_output`.

---

## SDK API

All intelligence methods are on the `SafeAI` class and use lazy imports (the intelligence package is never loaded unless called):

```python
from safeai import SafeAI

sai = SafeAI.from_config("safeai.yaml")

# Backend management
sai.register_ai_backend("ollama", backend, default=True)
sai.list_ai_backends()

# Advisory methods (all return AdvisorResult)
result = sai.intelligence_auto_config(project_path=".", framework_hint="langchain")
result = sai.intelligence_recommend(since="7d")
result = sai.intelligence_explain(event_id="evt_abc123")
result = sai.intelligence_compliance(framework="hipaa")
result = sai.intelligence_integrate(target="langchain", project_path=".")
```

### AdvisorResult

Every intelligence method returns an `AdvisorResult`:

```python
@dataclass(frozen=True)
class AdvisorResult:
    advisor_name: str           # "auto-config", "recommender", etc.
    status: str                 # "success", "error", "no_backend"
    summary: str                # Human-readable summary
    artifacts: dict[str, str]   # {"safeai.yaml": "...", "policies/rec.yaml": "..."}
    raw_response: str           # Full LLM response
    model_used: str             # Model that generated the response
    metadata: dict[str, Any]    # Agent-specific structured data
```

---

## Proxy Endpoints

The intelligence layer adds these proxy endpoints:

| Endpoint | Method | Description |
|---|---|---|
| `/v1/intelligence/status` | GET | Returns enabled/disabled status, backend, and model |
| `/v1/intelligence/explain` | POST | Classify and explain an incident |
| `/v1/intelligence/recommend` | POST | Suggest policy improvements |
| `/v1/intelligence/compliance` | POST | Generate compliance policies |

All endpoints return HTTP 503 with a clear message when not configured.

---

## Dashboard Integration

The dashboard adds an "Explain this incident" button on incident detail views:

- RBAC permission: `intelligence:explain` (available to `viewer` and above)
- Admin users get `intelligence:*` for all intelligence operations
- Endpoint: `POST /v1/dashboard/intelligence/explain`

---

## Staging and Human Review

All generated artifacts are written to a staging directory (default: `.safeai-generated/`) for human review:

```bash
# Generate configs
safeai intelligence auto-config --output-dir .safeai-generated

# Review the generated files
cat .safeai-generated/safeai.yaml
cat .safeai-generated/policies/generated.yaml

# Apply when satisfied
safeai intelligence auto-config --output-dir .safeai-generated --apply
```

The `--apply` flag copies files from the staging directory to the project root. Without it, nothing takes effect.

---

## Error Handling

| Level | Behavior |
|---|---|
| **Config** | `intelligence.enabled: false` (default). CLI commands fail with: "Intelligence layer is disabled." |
| **Runtime** | `intelligence_*()` methods raise `AIBackendNotConfiguredError` with instructions. |
| **Proxy** | Returns HTTP 503 `{"error": "Intelligence layer not configured"}`. Dashboard hides intelligence buttons. |

---

## Next Steps

- [Configuration](../getting-started/configuration.md) -- full `safeai.yaml` reference
- [Audit Logging](audit-logging.md) -- understand the audit events that feed the recommender
- [Policy Engine](policy-engine.md) -- how the generated policies are enforced
