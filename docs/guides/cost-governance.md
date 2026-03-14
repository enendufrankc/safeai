# Cost Governance

SafeAI tracks token usage across every LLM call your agents make, calculates costs in real time, and enforces budget limits before spend gets out of control. The `CostTracker` records consumption per model and provider, while `BudgetRule` lets you set hard or soft spending caps with configurable alerts.

!!! tip "Why cost governance matters"
    AI agents can generate thousands of LLM calls autonomously. Without guardrails, a single runaway loop can burn through your entire API budget in minutes. Cost governance gives you visibility and control over every dollar spent.

## Quick Start

```python
from safeai.core.cost import CostTracker, ModelPricing

tracker = CostTracker(pricing=[
    ModelPricing(provider="openai", model="gpt-4o",
                 input_price_per_1m=2.50, output_price_per_1m=10.00),
])

r = tracker.record(provider="openai", model="gpt-4o",
                   input_tokens=1000, output_tokens=500)
print(f"Cost: ${r.estimated_cost:.6f}")  # Cost: $0.007500
```

## Model Pricing

Define per-model pricing with `ModelPricing`. Prices are specified as cost per 1 million tokens for both input and output.

```python
from safeai.core.cost import ModelPricing

pricing = [
    ModelPricing(provider="openai", model="gpt-4o",
                 input_price_per_1m=2.50, output_price_per_1m=10.00),
    ModelPricing(provider="anthropic", model="claude-sonnet-4-20250514",
                 input_price_per_1m=3.00, output_price_per_1m=15.00),
]
```

| Field                | Type    | Description                                |
|----------------------|---------|--------------------------------------------|
| `provider`           | `str`   | Provider name (`openai`, `anthropic`, etc.) |
| `model`              | `str`   | Model identifier (e.g. `gpt-4o`)          |
| `input_price_per_1m` | `float` | Cost per 1M input (prompt) tokens          |
| `output_price_per_1m`| `float` | Cost per 1M output (completion) tokens     |

!!! info "Keep pricing up to date"
    LLM providers update pricing frequently. Review your `ModelPricing` definitions regularly or load them from a YAML config file to make updates easier. See [YAML Configuration](#yaml-configuration) below.

## Recording Usage

Call `tracker.record()` after each LLM interaction to log token consumption and calculate cost.

```python
from safeai.core.cost import CostTracker, ModelPricing

tracker = CostTracker(pricing=[
    ModelPricing(provider="openai", model="gpt-4o",
                 input_price_per_1m=2.50, output_price_per_1m=10.00),
    ModelPricing(provider="anthropic", model="claude-sonnet-4-20250514",
                 input_price_per_1m=3.00, output_price_per_1m=15.00),
])

# Record an OpenAI call
r1 = tracker.record(provider="openai", model="gpt-4o",
                    input_tokens=1000, output_tokens=500, agent_id="my-agent")
print(f"Cost: ${r1.estimated_cost:.6f}")

# Record an Anthropic call
r2 = tracker.record(provider="anthropic", model="claude-sonnet-4-20250514",
                    input_tokens=2000, output_tokens=800, agent_id="my-agent")

# Get an aggregate summary
summary = tracker.summary()
print(f"Total: ${summary.total_cost:.4f}, by model: {summary.by_model}")
```

### Record Fields

| Parameter       | Type   | Required | Description                                  |
|-----------------|--------|----------|----------------------------------------------|
| `provider`      | `str`  | Yes      | LLM provider name                            |
| `model`         | `str`  | Yes      | Model identifier                             |
| `input_tokens`  | `int`  | Yes      | Number of prompt tokens consumed             |
| `output_tokens` | `int`  | Yes      | Number of completion tokens consumed         |
| `agent_id`      | `str`  | No       | Agent that initiated the call                |

## Budget Enforcement

Use `BudgetRule` to set spending limits. Budgets can issue warnings at a configurable threshold and either soft-warn or hard-block when the limit is reached.

```python
from safeai.core.cost import CostTracker, ModelPricing, BudgetRule

tracker = CostTracker(
    pricing=[
        ModelPricing(provider="openai", model="gpt-4o",
                     input_price_per_1m=2.50, output_price_per_1m=10.00),
    ],
    budgets=[
        BudgetRule(scope="global", limit=0.01,
                   action="hard_block", alert_at_percent=80),
    ],
)

tracker.record(provider="openai", model="gpt-4o",
               input_tokens=5000, output_tokens=2000)
status = tracker.enforce_budget()
```

!!! warning "Hard blocks stop all calls"
    When a `hard_block` budget is exceeded, `enforce_budget()` signals that no further LLM calls should proceed. Make sure your agent handles this status gracefully to avoid silent failures.

### Budget Rule Options

| Field              | Type    | Description                                            |
|--------------------|---------|--------------------------------------------------------|
| `scope`            | `str`   | `global`, a specific `agent_id`, or model name         |
| `limit`            | `float` | Maximum spend in USD                                   |
| `action`           | `str`   | `hard_block` or `soft_warn`                            |
| `alert_at_percent` | `int`   | Percentage of limit at which to trigger an alert (e.g. `80`) |

### Actions

| Action        | Behavior                                                             |
|---------------|----------------------------------------------------------------------|
| `hard_block`  | Reject further LLM calls once the budget limit is reached           |
| `soft_warn`   | Log a warning but allow calls to continue                           |

## Provider Wrappers

SafeAI includes provider wrappers that extract token usage from raw API responses. Use these to automatically feed usage data into the `CostTracker`.

### OpenAI

```python
from safeai.providers.openai_wrapper import OpenAIWrapper

oai = OpenAIWrapper()
usage = oai.extract_usage({
    "model": "gpt-4o",
    "usage": {"prompt_tokens": 100, "completion_tokens": 50},
})
# usage.input_tokens == 100, usage.output_tokens == 50
```

### Anthropic

```python
from safeai.providers.anthropic_wrapper import AnthropicWrapper

anth = AnthropicWrapper()
usage = anth.extract_usage({
    "model": "claude-sonnet-4-20250514",
    "usage": {"input_tokens": 200, "output_tokens": 100},
})
```

### Google

```python
from safeai.providers.google_wrapper import GoogleWrapper

goog = GoogleWrapper()
usage = goog.extract_usage({
    "model": "gemini-pro",
    "usageMetadata": {"promptTokenCount": 150, "candidatesTokenCount": 75},
})
```

| Provider   | Wrapper Class      | Input Field          | Output Field             |
|------------|--------------------|----------------------|--------------------------|
| OpenAI     | `OpenAIWrapper`    | `prompt_tokens`      | `completion_tokens`      |
| Anthropic  | `AnthropicWrapper` | `input_tokens`       | `output_tokens`          |
| Google     | `GoogleWrapper`    | `promptTokenCount`   | `candidatesTokenCount`   |

## YAML Configuration

Load model pricing from a YAML config file instead of defining it in code. This makes it easy to update prices without redeploying.

```python
from pathlib import Path
from safeai.core.cost import CostTracker

tracker = CostTracker()
tracker.load_pricing_yaml(Path("safeai/config/defaults/cost/pricing.yaml"))
```

Example pricing YAML:

```yaml title="pricing.yaml"
pricing:
  - provider: openai
    model: gpt-4o
    input_price_per_1m: 2.50
    output_price_per_1m: 10.00
  - provider: openai
    model: gpt-4o-mini
    input_price_per_1m: 0.15
    output_price_per_1m: 0.60
  - provider: anthropic
    model: claude-sonnet-4-20250514
    input_price_per_1m: 3.00
    output_price_per_1m: 15.00
```

!!! tip "Centralize pricing"
    Store your pricing YAML alongside your `safeai.yaml` configuration so all cost-related settings live in one place. Reference it from your main config to keep things DRY.

## CLI Commands

SafeAI provides CLI commands for inspecting cost data and managing budgets.

### `cost summary`

Display an aggregate cost summary across all tracked usage.

```bash
python -m safeai.cli.main cost summary
python -m safeai.cli.main cost summary --help
```

### `cost budget`

View or manage budget rules and their current status.

```bash
python -m safeai.cli.main cost budget
python -m safeai.cli.main cost budget --help
```

### `cost report`

Generate a detailed cost report, optionally filtered by date range, provider, or agent.

```bash
python -m safeai.cli.main cost report
python -m safeai.cli.main cost report --help
```

| Command         | Description                                      |
|-----------------|--------------------------------------------------|
| `cost summary`  | Aggregate cost totals by model and provider      |
| `cost budget`   | Display budget rules, utilization, and alerts    |
| `cost report`   | Detailed breakdown with optional filters         |

## Audit Integration

Every cost record is written to the SafeAI audit trail. Cost fields are attached to audit log entries so you can correlate spend with specific agent actions, policy decisions, and user sessions.

Audit entries include:

| Audit Field        | Description                                    |
|--------------------|------------------------------------------------|
| `estimated_cost`   | Dollar cost of the individual LLM call         |
| `input_tokens`     | Prompt tokens consumed                         |
| `output_tokens`    | Completion tokens consumed                     |
| `provider`         | LLM provider name                              |
| `model`            | Model identifier                               |
| `agent_id`         | Agent that initiated the call                  |
| `budget_status`    | Budget state at time of call (`ok`, `warning`, `exceeded`) |

!!! info "Query cost data in audit logs"
    Use the audit trail to answer questions like "How much did agent X spend last week?" or "Which model is the most expensive per session?" The structured fields make it easy to filter and aggregate.

## See Also

- [Policy Engine guide](policy-engine.md) for controlling agent behavior with rules
- [Secret Detection guide](secret-detection.md) for scanning inbound text
- [Audit Logging guide](audit-logging.md) for reviewing logged events
