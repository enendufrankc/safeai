# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 SafeAI Contributors
"""Multi-provider LLM routing with failover and strategy selection."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from threading import RLock
from typing import Literal

RoutingStrategy = Literal["cost_optimized", "latency_optimized", "round_robin", "priority"]


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    base_url: str
    api_key_env: str | None = None
    models: list[str] = field(default_factory=list)
    priority: int = 0
    max_retries: int = 3
    timeout_seconds: float = 30.0
    enabled: bool = True


@dataclass(frozen=True)
class RoutingDecision:
    provider: str
    model: str
    base_url: str
    api_key_env: str | None
    reason: str


@dataclass
class ProviderHealth:
    name: str
    consecutive_failures: int = 0
    last_failure_time: float | None = None
    circuit_open: bool = False
    avg_latency_ms: float = 0.0
    total_requests: int = 0


class ProviderRegistry:
    """Routes requests across LLM providers with failover and strategy selection."""

    def __init__(
        self,
        providers: list[ProviderConfig] | None = None,
        strategy: RoutingStrategy = "priority",
        circuit_breaker_threshold: int = 5,
        circuit_breaker_cooldown: float = 60.0,
    ) -> None:
        self._providers: dict[str, ProviderConfig] = {}
        self._health: dict[str, ProviderHealth] = {}
        self._strategy: RoutingStrategy = strategy
        self._circuit_breaker_threshold = circuit_breaker_threshold
        self._circuit_breaker_cooldown = circuit_breaker_cooldown
        self._lock = RLock()
        self._rr_counter = 0

        for provider in providers or []:
            self.register(provider)

    def register(self, provider: ProviderConfig) -> None:
        with self._lock:
            self._providers[provider.name] = provider
            if provider.name not in self._health:
                self._health[provider.name] = ProviderHealth(name=provider.name)

    def route(
        self,
        *,
        model: str | None = None,
        preferred_provider: str | None = None,
    ) -> RoutingDecision:
        with self._lock:
            candidates = [p for p in self._providers.values() if self._is_available(p)]

            if model is not None:
                candidates = [p for p in candidates if model in p.models]

            if not candidates:
                raise RuntimeError(
                    f"No available provider for model={model!r}. "
                    f"Registered: {list(self._providers.keys())}. "
                    "Check that providers are enabled and circuits are not open."
                )

            if preferred_provider is not None:
                preferred = [p for p in candidates if p.name == preferred_provider]
                if preferred:
                    return self._make_decision(preferred[0], model, "preferred_provider")

            chosen: ProviderConfig
            reason: str

            if self._strategy == "priority" or self._strategy == "cost_optimized":
                candidates.sort(key=lambda p: p.priority)
                chosen = candidates[0]
                reason = self._strategy

            elif self._strategy == "latency_optimized":
                candidates.sort(key=lambda p: self._health[p.name].avg_latency_ms)
                chosen = candidates[0]
                reason = "latency_optimized"

            elif self._strategy == "round_robin":
                idx = self._rr_counter % len(candidates)
                chosen = candidates[idx]
                self._rr_counter += 1
                reason = "round_robin"

            else:  # pragma: no cover
                raise RuntimeError(f"Unknown strategy: {self._strategy}")

            return self._make_decision(chosen, model, reason)

    def report_success(self, provider: str, latency_ms: float) -> None:
        with self._lock:
            h = self._health.get(provider)
            if h is None:
                return
            h.consecutive_failures = 0
            h.circuit_open = False
            h.total_requests += 1
            alpha = 0.3
            if h.total_requests == 1:
                h.avg_latency_ms = latency_ms
            else:
                h.avg_latency_ms = alpha * latency_ms + (1 - alpha) * h.avg_latency_ms

    def report_failure(self, provider: str) -> None:
        with self._lock:
            h = self._health.get(provider)
            if h is None:
                return
            h.consecutive_failures += 1
            h.last_failure_time = time.monotonic()
            if h.consecutive_failures >= self._circuit_breaker_threshold:
                h.circuit_open = True

    def health(self) -> list[ProviderHealth]:
        with self._lock:
            return [
                ProviderHealth(
                    name=h.name,
                    consecutive_failures=h.consecutive_failures,
                    last_failure_time=h.last_failure_time,
                    circuit_open=h.circuit_open,
                    avg_latency_ms=h.avg_latency_ms,
                    total_requests=h.total_requests,
                )
                for h in self._health.values()
            ]

    def _is_available(self, provider: ProviderConfig) -> bool:
        if not provider.enabled:
            return False
        h = self._health.get(provider.name)
        if h is None:
            return True
        if not h.circuit_open:
            return True
        if h.last_failure_time is not None:
            elapsed = time.monotonic() - h.last_failure_time
            if elapsed >= self._circuit_breaker_cooldown:
                h.circuit_open = False
                h.consecutive_failures = 0
                return True
        return False

    @staticmethod
    def _make_decision(
        provider: ProviderConfig,
        model: str | None,
        reason: str,
    ) -> RoutingDecision:
        chosen_model = model if model is not None else (provider.models[0] if provider.models else "")
        return RoutingDecision(
            provider=provider.name,
            model=chosen_model,
            base_url=provider.base_url,
            api_key_env=provider.api_key_env,
            reason=reason,
        )
