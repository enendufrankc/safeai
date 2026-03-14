# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 SafeAI Contributors
"""Cost tracking and budget enforcement for LLM calls."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any, Literal

import yaml


@dataclass(frozen=True)
class ModelPricing:
    provider: str
    model: str
    input_price_per_1m: float
    output_price_per_1m: float


@dataclass(frozen=True)
class CostRecord:
    timestamp: str
    provider: str
    model: str
    agent_id: str
    session_id: str
    input_tokens: int
    output_tokens: int
    estimated_cost: float


@dataclass(frozen=True)
class BudgetRule:
    scope: Literal["global", "per_user", "per_session", "per_agent"]
    limit: float
    action: Literal["warn", "soft_block", "hard_block"]
    alert_at_percent: int = 80


@dataclass(frozen=True)
class BudgetStatus:
    scope: str
    scope_id: str
    spent: float
    limit: float
    utilization_pct: float
    action: str
    exceeded: bool


@dataclass(frozen=True)
class CostSummary:
    total_cost: float
    total_input_tokens: int
    total_output_tokens: int
    by_model: dict[str, float]
    by_provider: dict[str, float]
    by_agent: dict[str, float]
    record_count: int


class CostTracker:
    """Track LLM call costs and enforce budget rules."""

    def __init__(
        self,
        pricing: list[ModelPricing] | None = None,
        budgets: list[BudgetRule] | None = None,
    ) -> None:
        self._lock = RLock()
        self._pricing: dict[tuple[str, str], ModelPricing] = {}
        for entry in pricing or []:
            self._pricing[(entry.provider, entry.model)] = entry
        self._budgets: list[BudgetRule] = list(budgets or [])
        self._records: list[CostRecord] = []
        self._spend_global: float = 0.0
        self._spend_by_agent: dict[str, float] = defaultdict(float)
        self._spend_by_session: dict[str, float] = defaultdict(float)

    # ------------------------------------------------------------------
    # Pricing loader
    # ------------------------------------------------------------------

    def load_pricing_yaml(self, path: Path) -> None:
        """Load pricing from a YAML file and populate the pricing lookup."""
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        models = data.get("models", [])
        with self._lock:
            for item in models:
                entry = ModelPricing(
                    provider=item["provider"],
                    model=item["model"],
                    input_price_per_1m=float(item["input_price_per_1m"]),
                    output_price_per_1m=float(item["output_price_per_1m"]),
                )
                self._pricing[(entry.provider, entry.model)] = entry

    # ------------------------------------------------------------------
    # Record a call
    # ------------------------------------------------------------------

    def record(
        self,
        *,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        agent_id: str = "unknown",
        session_id: str = "default",
    ) -> CostRecord:
        """Calculate cost, store a record, and update cumulative counters."""
        with self._lock:
            pricing = self._pricing.get((provider, model))
            if pricing is not None:
                cost = (
                    input_tokens * pricing.input_price_per_1m
                    + output_tokens * pricing.output_price_per_1m
                ) / 1_000_000
            else:
                cost = 0.0

            record = CostRecord(
                timestamp=datetime.now(timezone.utc).isoformat(),
                provider=provider,
                model=model,
                agent_id=agent_id,
                session_id=session_id,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                estimated_cost=cost,
            )
            self._records.append(record)
            self._spend_global += cost
            self._spend_by_agent[agent_id] += cost
            self._spend_by_session[session_id] += cost
            return record

    # ------------------------------------------------------------------
    # Budget checks
    # ------------------------------------------------------------------

    def check_budget(self, *, scope_id: str = "global") -> list[BudgetStatus]:
        """Check all budget rules against cumulative spend."""
        statuses: list[BudgetStatus] = []
        with self._lock:
            for rule in self._budgets:
                if rule.scope == "global":
                    spent = self._spend_global
                    sid = "global"
                elif rule.scope == "per_agent":
                    spent = self._spend_by_agent.get(scope_id, 0.0)
                    sid = scope_id
                elif rule.scope == "per_session":
                    spent = self._spend_by_session.get(scope_id, 0.0)
                    sid = scope_id
                else:
                    spent = self._spend_global
                    sid = scope_id

                utilization = (spent / rule.limit * 100) if rule.limit > 0 else 0.0
                statuses.append(
                    BudgetStatus(
                        scope=rule.scope,
                        scope_id=sid,
                        spent=spent,
                        limit=rule.limit,
                        utilization_pct=utilization,
                        action=rule.action,
                        exceeded=spent >= rule.limit,
                    )
                )
        return statuses

    # ------------------------------------------------------------------
    # Summarise
    # ------------------------------------------------------------------

    def summary(
        self,
        *,
        agent_id: str | None = None,
        model: str | None = None,
        last_n: int | None = None,
    ) -> CostSummary:
        """Aggregate cost records with optional filters."""
        with self._lock:
            records = list(self._records)

        if agent_id is not None:
            records = [r for r in records if r.agent_id == agent_id]
        if model is not None:
            records = [r for r in records if r.model == model]
        if last_n is not None:
            records = records[-last_n:]

        total_cost = 0.0
        total_input = 0
        total_output = 0
        by_model: dict[str, float] = defaultdict(float)
        by_provider: dict[str, float] = defaultdict(float)
        by_agent: dict[str, float] = defaultdict(float)

        for rec in records:
            total_cost += rec.estimated_cost
            total_input += rec.input_tokens
            total_output += rec.output_tokens
            by_model[rec.model] += rec.estimated_cost
            by_provider[rec.provider] += rec.estimated_cost
            by_agent[rec.agent_id] += rec.estimated_cost

        return CostSummary(
            total_cost=total_cost,
            total_input_tokens=total_input,
            total_output_tokens=total_output,
            by_model=dict(by_model),
            by_provider=dict(by_provider),
            by_agent=dict(by_agent),
            record_count=len(records),
        )

    # ------------------------------------------------------------------
    # Budget enforcement (Phase 10.2)
    # ------------------------------------------------------------------

    def enforce_budget(
        self,
        *,
        agent_id: str = "unknown",
        session_id: str = "default",
    ) -> BudgetStatus | None:
        """Return the most restrictive exceeded budget, or *None* if all OK.

        The action boundary calls this before allowing an LLM call.  When
        multiple budgets are exceeded the one with the highest utilisation
        percentage is returned so the caller can act on the strictest breach.
        """
        worst: BudgetStatus | None = None
        with self._lock:
            for rule in self._budgets:
                if rule.scope == "global":
                    spent = self._spend_global
                    sid = "global"
                elif rule.scope == "per_agent":
                    spent = self._spend_by_agent.get(agent_id, 0.0)
                    sid = agent_id
                elif rule.scope == "per_session":
                    spent = self._spend_by_session.get(session_id, 0.0)
                    sid = session_id
                else:
                    spent = self._spend_global
                    sid = agent_id

                utilization = (spent / rule.limit * 100) if rule.limit > 0 else 0.0
                if spent < rule.limit:
                    continue

                status = BudgetStatus(
                    scope=rule.scope,
                    scope_id=sid,
                    spent=spent,
                    limit=rule.limit,
                    utilization_pct=utilization,
                    action=rule.action,
                    exceeded=True,
                )
                if worst is None or status.utilization_pct > worst.utilization_pct:
                    worst = status
        return worst

    # ------------------------------------------------------------------
    # Audit-trail integration (Phase 10.3)
    # ------------------------------------------------------------------

    @staticmethod
    def to_audit_fields(record: CostRecord) -> dict[str, Any]:
        """Return a dict of cost fields suitable for merging into audit event data."""
        return {
            "tokens_in": record.input_tokens,
            "tokens_out": record.output_tokens,
            "estimated_cost": record.estimated_cost,
            "model": record.model,
            "provider": record.provider,
        }

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Clear all records and counters."""
        with self._lock:
            self._records.clear()
            self._spend_global = 0.0
            self._spend_by_agent.clear()
            self._spend_by_session.clear()
