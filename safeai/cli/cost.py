# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 SafeAI Contributors
"""safeai cost — view spend, check budgets, export reports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal, cast

import click

from safeai.config.loader import load_config


@click.group(name="cost")
def cost_group() -> None:
    """View LLM spend and budget status."""


@cost_group.command(name="summary")
@click.option("--config", "config_path", default="safeai.yaml", show_default=True, help="Config path.")
@click.option("--agent", "agent_id", default=None, help="Filter by agent ID.")
@click.option("--model", default=None, help="Filter by model name.")
@click.option("--last", "last_n", default=None, type=int, help="Last N records.")
def cost_summary(config_path: str, agent_id: str | None, model: str | None, last_n: int | None) -> None:
    """Show cost summary breakdown."""
    config_file = Path(config_path).expanduser().resolve()
    if not config_file.exists():
        click.echo(f"Config not found: {config_file}\nFix: Run 'safeai init' to create default config.", err=True)
        raise SystemExit(1)

    cfg = load_config(config_file)
    if not cfg.cost.enabled:
        click.echo("Cost tracking is not enabled.\nFix: Set 'cost.enabled: true' in safeai.yaml.")
        return

    from safeai.core.cost import CostTracker

    tracker = CostTracker()

    if cfg.cost.pricing_file:
        pricing_path = config_file.parent / cfg.cost.pricing_file
        if pricing_path.exists():
            tracker.load_pricing_yaml(pricing_path)

    summary = tracker.summary(agent_id=agent_id, model=model, last_n=last_n)

    click.echo(f"Total cost:    ${summary.total_cost:.4f} {cfg.cost.currency}")
    click.echo(f"Input tokens:  {summary.total_input_tokens:,}")
    click.echo(f"Output tokens: {summary.total_output_tokens:,}")
    click.echo(f"Records:       {summary.record_count}")

    if summary.by_model:
        click.echo("\nBy model:")
        for m, cost in sorted(summary.by_model.items(), key=lambda x: -x[1]):
            click.echo(f"  {m}: ${cost:.4f}")

    if summary.by_provider:
        click.echo("\nBy provider:")
        for p, cost in sorted(summary.by_provider.items(), key=lambda x: -x[1]):
            click.echo(f"  {p}: ${cost:.4f}")

    if summary.by_agent:
        click.echo("\nBy agent:")
        for a, cost in sorted(summary.by_agent.items(), key=lambda x: -x[1]):
            click.echo(f"  {a}: ${cost:.4f}")


@cost_group.command(name="budget")
@click.option("--config", "config_path", default="safeai.yaml", show_default=True, help="Config path.")
@click.option("--check", is_flag=True, help="Check budget status.")
def cost_budget(config_path: str, check: bool) -> None:
    """Show budget utilization."""
    config_file = Path(config_path).expanduser().resolve()
    if not config_file.exists():
        click.echo(f"Config not found: {config_file}\nFix: Run 'safeai init' to create default config.", err=True)
        raise SystemExit(1)

    cfg = load_config(config_file)
    if not cfg.cost.enabled:
        click.echo("Cost tracking is not enabled.\nFix: Set 'cost.enabled: true' in safeai.yaml.")
        return

    if not cfg.cost.budgets:
        click.echo("No budget rules configured.\nFix: Add 'cost.budgets' section to safeai.yaml.")
        return

    from safeai.core.cost import BudgetRule, CostTracker

    budgets = [
        BudgetRule(
            scope=cast("Literal['global', 'per_user', 'per_session', 'per_agent']", b.scope),
            limit=b.limit,
            action=cast("Literal['warn', 'soft_block', 'hard_block']", b.action),
            alert_at_percent=b.alert_at_percent,
        )
        for b in cfg.cost.budgets
    ]
    tracker = CostTracker(budgets=budgets)
    statuses = tracker.check_budget()

    if not statuses:
        click.echo("All budgets within limits. ✓")
        return

    for s in statuses:
        icon = "🔴" if s.exceeded else ("🟡" if s.utilization_pct >= s.limit * 0.8 else "🟢")
        click.echo(f"{icon} {s.scope}/{s.scope_id}: ${s.spent:.4f} / ${s.limit:.2f} ({s.utilization_pct:.1f}%) [{s.action}]")


@cost_group.command(name="report")
@click.option("--config", "config_path", default="safeai.yaml", show_default=True, help="Config path.")
@click.option("--format", "fmt", type=click.Choice(["json", "text"]), default="text", help="Output format.")
def cost_report(config_path: str, fmt: str) -> None:
    """Export a cost report."""
    config_file = Path(config_path).expanduser().resolve()
    if not config_file.exists():
        click.echo(f"Config not found: {config_file}\nFix: Run 'safeai init' to create default config.", err=True)
        raise SystemExit(1)

    cfg = load_config(config_file)
    if not cfg.cost.enabled:
        click.echo("Cost tracking is not enabled.\nFix: Set 'cost.enabled: true' in safeai.yaml.")
        return

    from safeai.core.cost import CostTracker

    tracker = CostTracker()

    summary = tracker.summary()
    if fmt == "json":
        data = {
            "total_cost": summary.total_cost,
            "total_input_tokens": summary.total_input_tokens,
            "total_output_tokens": summary.total_output_tokens,
            "record_count": summary.record_count,
            "by_model": summary.by_model,
            "by_provider": summary.by_provider,
            "by_agent": summary.by_agent,
            "currency": cfg.cost.currency,
        }
        click.echo(json.dumps(data, indent=2))
    else:
        click.echo(f"Cost Report ({cfg.cost.currency})")
        click.echo("=" * 40)
        click.echo(f"Total: ${summary.total_cost:.4f}")
        click.echo(f"Records: {summary.record_count}")
