# Multi-Provider Routing

SafeAI's multi-provider routing lets you register multiple LLM providers and automatically route requests based on priority, cost, latency, or availability. When a provider goes down, the circuit breaker trips and traffic fails over to the next healthy provider — no manual intervention, no dropped requests.

!!! tip "Works with the proxy"
    Multi-provider routing integrates directly with the [Proxy / Sidecar](../integrations/proxy-sidecar.md). Any routing strategy you configure applies to all requests flowing through the proxy.

## Quick Start

```python
from safeai.core.router import ProviderRegistry, ProviderConfig

registry = ProviderRegistry(strategy="priority")
registry.register(ProviderConfig(
    name="openai",
    base_url="https://api.openai.com",
    api_key_env="OPENAI_API_KEY",
    models=["gpt-4o", "gpt-4o-mini"],
    priority=1,
))
registry.register(ProviderConfig(
    name="anthropic",
    base_url="https://api.anthropic.com",
    api_key_env="ANTHROPIC_API_KEY",
    models=["claude-sonnet-4-20250514"],
    priority=2,
))

decision = registry.route()
print(decision.provider)  # "openai"
print(decision.reason)    # "highest priority healthy provider"
```

## Provider Configuration

Each provider is defined with a `ProviderConfig`:

```python
from safeai.core.router import ProviderConfig

provider = ProviderConfig(
    name="openai",                          # unique identifier
    base_url="https://api.openai.com",      # API endpoint
    api_key_env="OPENAI_API_KEY",           # env var holding the API key
    models=["gpt-4o", "gpt-4o-mini"],       # models available on this provider
    priority=1,                             # lower number = higher priority
)
```

| Field         | Type        | Description                                              |
|---------------|-------------|----------------------------------------------------------|
| `name`        | `str`       | Unique identifier for the provider                       |
| `base_url`    | `str`       | Base URL of the provider's API                           |
| `api_key_env` | `str`       | Environment variable name containing the API key         |
| `models`      | `list[str]` | Models available from this provider                      |
| `priority`    | `int`       | Routing priority — lower number means higher preference  |

!!! info "Local providers"
    For self-hosted providers like Ollama, omit `api_key_env`:
    ```python
    ProviderConfig(name="ollama", base_url="http://localhost:11434", models=["llama3.2"], priority=3)
    ```

## Routing Strategies

Create a `ProviderRegistry` with one of four strategies:

```python
from safeai.core.router import ProviderRegistry, ProviderConfig

for strategy in ["priority", "cost_optimized", "latency_optimized", "round_robin"]:
    reg = ProviderRegistry(strategy=strategy)
    reg.register(ProviderConfig(name="a", base_url="http://a", models=["m"], priority=1))
    reg.register(ProviderConfig(name="b", base_url="http://b", models=["m"], priority=2))
    d = reg.route()
    print(f"{strategy}: {d.provider} ({d.reason})")
```

| Strategy            | Behavior                                                                 |
|---------------------|--------------------------------------------------------------------------|
| `priority`          | Always picks the healthy provider with the lowest `priority` number      |
| `cost_optimized`    | Routes to the cheapest available provider for the requested model        |
| `latency_optimized` | Routes to the provider with the lowest observed response latency         |
| `round_robin`       | Distributes requests evenly across all healthy providers                 |

!!! warning "Strategy applies only to healthy providers"
    Regardless of strategy, providers with an open circuit breaker are excluded from selection. A `round_robin` registry with one unhealthy provider will skip it automatically.

## Circuit Breaker

The circuit breaker tracks consecutive failures per provider. After a configurable threshold, the provider's circuit opens and all traffic fails over to the next candidate.

```python
from safeai.core.router import ProviderRegistry, ProviderConfig

registry = ProviderRegistry(strategy="priority", circuit_breaker_threshold=3)
registry.register(ProviderConfig(name="primary", base_url="http://primary", models=["m"], priority=1))
registry.register(ProviderConfig(name="backup", base_url="http://backup", models=["m"], priority=2))

# Simulate 3 consecutive failures
for _ in range(3):
    registry.report_failure("primary")

# Circuit is now open — traffic routes to backup
decision = registry.route()
assert decision.provider == "backup"
```

```
normal  ──►  failure 1  ──►  failure 2  ──►  failure 3  ──►  circuit OPEN
                                                                  │
                                                          failover to backup
```

| Parameter                    | Default | Description                                    |
|------------------------------|---------|------------------------------------------------|
| `circuit_breaker_threshold`  | `5`     | Consecutive failures before the circuit opens  |

## Health Monitoring

Check the status of all registered providers at any time:

```python
health = registry.health()
for status in health:
    print(f"{status.provider}: circuit_open={status.circuit_open}")
```

```python
# After failing over from primary
health = registry.health()
print(f"Primary circuit open: {health[0].circuit_open}")   # True
print(f"Backup circuit open: {health[1].circuit_open}")    # False
```

!!! tip "Periodic health checks"
    Call `registry.health()` on a schedule and feed the results into your observability stack. Combine with [Audit Logging](audit-logging.md) to track routing decisions over time.

## Model-Specific Routing

When you need a specific model, pass it to `route()`. The registry selects only providers that serve that model:

```python
from safeai.core.router import ProviderRegistry, ProviderConfig

registry = ProviderRegistry(strategy="priority")
registry.register(ProviderConfig(
    name="openai",
    base_url="https://api.openai.com",
    api_key_env="OPENAI_API_KEY",
    models=["gpt-4o", "gpt-4o-mini"],
    priority=1,
))
registry.register(ProviderConfig(
    name="anthropic",
    base_url="https://api.anthropic.com",
    api_key_env="ANTHROPIC_API_KEY",
    models=["claude-sonnet-4-20250514"],
    priority=2,
))

# Routes to anthropic — the only provider with this model
decision = registry.route(model="claude-sonnet-4-20250514")
print(f"Model route: {decision.provider}")  # "anthropic"
```

!!! danger "No provider for model"
    If no healthy provider serves the requested model, `route()` raises an error. Always ensure at least one provider is registered for each model you plan to use.

## YAML Configuration

Configure routing declaratively in `safeai.yaml`:

```yaml title="safeai.yaml"
routing:
  enabled: true
  strategy: priority
  circuit_breaker_threshold: 3

  providers:
    - name: openai
      base_url: https://api.openai.com
      api_key_env: OPENAI_API_KEY
      models: [gpt-4o, gpt-4o-mini]
      priority: 1

    - name: anthropic
      base_url: https://api.anthropic.com
      api_key_env: ANTHROPIC_API_KEY
      models: [claude-sonnet-4-20250514]
      priority: 2

    - name: ollama
      base_url: http://localhost:11434
      models: [llama3.2]
      priority: 3
```

Load and verify the config programmatically:

```python
from safeai.config.models import SafeAIConfig

cfg = SafeAIConfig()
print(f"Routing: enabled={cfg.routing.enabled}, strategy={cfg.routing.strategy}")
```

| Setting                      | Default    | Description                                      |
|------------------------------|------------|--------------------------------------------------|
| `routing.enabled`            | `false`    | Enable multi-provider routing                    |
| `routing.strategy`           | `priority` | One of `priority`, `cost_optimized`, `latency_optimized`, `round_robin` |
| `routing.circuit_breaker_threshold` | `5` | Failures before circuit opens                    |

## Proxy Integration

When routing is enabled, the [Proxy / Sidecar](../integrations/proxy-sidecar.md) automatically applies your routing strategy to every intercepted LLM request:

```yaml title="safeai.yaml"
proxy:
  enabled: true
  listen: "0.0.0.0:8080"

routing:
  enabled: true
  strategy: latency_optimized
  providers:
    - name: openai
      base_url: https://api.openai.com
      api_key_env: OPENAI_API_KEY
      models: [gpt-4o]
      priority: 1
    - name: anthropic
      base_url: https://api.anthropic.com
      api_key_env: ANTHROPIC_API_KEY
      models: [claude-sonnet-4-20250514]
      priority: 2
```

Point your application at the proxy and SafeAI handles provider selection, failover, and health monitoring transparently:

```bash
export OPENAI_BASE_URL=http://localhost:8080
```

## See Also

- [Proxy / Sidecar integration](../integrations/proxy-sidecar.md) for HTTP proxy setup
- [Policy Engine guide](policy-engine.md) for boundary enforcement on routed requests
- [Audit Logging guide](audit-logging.md) for tracking routing decisions
