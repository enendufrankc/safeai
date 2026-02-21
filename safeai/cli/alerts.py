"""safeai alerts command group."""

from __future__ import annotations

import json

import click

from safeai.api import SafeAI
from safeai.config.loader import load_config
from safeai.dashboard.service import AlertRuleManager, _parse_alert_rule


@click.group(name="alerts")
def alerts_group() -> None:
    """Manage alert rules and evaluate alerts."""


@alerts_group.command(name="list")
@click.option("--config", "config_path", default="safeai.yaml", show_default=True, help="Config path.")
def alerts_list_command(config_path: str) -> None:
    """List configured alert rules."""
    cfg = load_config(config_path)
    from pathlib import Path

    config_dir = Path(config_path).expanduser().resolve().parent
    rules_file_str = cfg.dashboard.alert_rules_file
    rules_file = None
    if rules_file_str:
        raw = Path(rules_file_str).expanduser()
        rules_file = raw if raw.is_absolute() else (config_dir / raw).resolve()
    manager = AlertRuleManager(rules_file=rules_file, alert_log_file=None)
    rules = manager.list_rules()
    if not rules:
        click.echo("No alert rules configured.")
        return
    click.echo(f"{'rule_id':<20} {'name':<30} {'threshold':>9} {'window':<8} channels")
    click.echo("-" * 90)
    for rule in rules:
        channels = ", ".join(rule.channels)
        click.echo(f"{rule.rule_id:<20} {rule.name:<30} {rule.threshold:>9} {rule.window:<8} {channels}")


@alerts_group.command(name="add")
@click.option("--config", "config_path", default="safeai.yaml", show_default=True, help="Config path.")
@click.option("--rule-id", required=True, help="Unique rule identifier.")
@click.option("--name", required=True, help="Human-readable rule name.")
@click.option("--threshold", type=int, default=5, show_default=True, help="Event count threshold.")
@click.option("--window", default="15m", show_default=True, help="Time window (e.g. 15m, 1h).")
@click.option("--channel", "channels", multiple=True, default=["file"], help="Notification channels.")
def alerts_add_command(
    config_path: str,
    rule_id: str,
    name: str,
    threshold: int,
    window: str,
    channels: tuple[str, ...],
) -> None:
    """Add or update an alert rule."""
    cfg = load_config(config_path)
    from pathlib import Path

    config_dir = Path(config_path).expanduser().resolve().parent
    rules_file_str = cfg.dashboard.alert_rules_file
    rules_file = None
    if rules_file_str:
        raw = Path(rules_file_str).expanduser()
        rules_file = raw if raw.is_absolute() else (config_dir / raw).resolve()
    manager = AlertRuleManager(rules_file=rules_file, alert_log_file=None)
    parsed = _parse_alert_rule({
        "rule_id": rule_id,
        "name": name,
        "threshold": threshold,
        "window": window,
        "channels": list(channels),
    })
    if parsed is None:
        raise click.ClickException("Invalid alert rule parameters.")
    manager.upsert(parsed)
    click.echo(f"Alert rule '{rule_id}' saved.")


@alerts_group.command(name="test")
@click.option("--config", "config_path", default="safeai.yaml", show_default=True, help="Config path.")
@click.option("--last", default="15m", show_default=True, help="Time window to evaluate.")
def alerts_test_command(config_path: str, last: str) -> None:
    """Dry-run alert evaluation against recent audit events."""
    sdk = SafeAI.from_config(config_path)
    events = sdk.query_audit(last=last, limit=20000)
    cfg = load_config(config_path)
    from pathlib import Path

    config_dir = Path(config_path).expanduser().resolve().parent
    rules_file_str = cfg.dashboard.alert_rules_file
    alert_log_str = cfg.dashboard.alert_log_file
    rules_file = None
    alert_log_file = None
    if rules_file_str:
        raw = Path(rules_file_str).expanduser()
        rules_file = raw if raw.is_absolute() else (config_dir / raw).resolve()
    if alert_log_str:
        raw = Path(alert_log_str).expanduser()
        alert_log_file = raw if raw.is_absolute() else (config_dir / raw).resolve()
    manager = AlertRuleManager(rules_file=rules_file, alert_log_file=alert_log_file)
    triggered = manager.evaluate(events=events)
    if not triggered:
        click.echo(f"No alerts triggered (evaluated {len(events)} events in last {last}).")
        return
    click.echo(f"Triggered {len(triggered)} alert(s):")
    for alert in triggered:
        click.echo(json.dumps(alert, indent=2))
