"""safeai logs command."""

from __future__ import annotations

import json
from pathlib import Path

import click

from safeai.core.audit import AuditLogger


@click.command(name="logs")
@click.option("--file", "log_file", default="logs/audit.log", show_default=True, help="Audit log file path.")
@click.option("--tail", "tail_lines", default=20, show_default=True, type=int, help="Number of recent lines.")
@click.option("--boundary", default=None, help="Filter by boundary.")
@click.option("--action", default=None, help="Filter by action.")
@click.option("--policy", "policy_name", default=None, help="Filter by policy name.")
@click.option("--agent", "agent_id", default=None, help="Filter by agent id.")
@click.option("--tool", "tool_name", default=None, help="Filter by tool name.")
@click.option("--since", default=None, help="Filter events since ISO-8601 timestamp.")
@click.option("--last", default=None, help="Filter events in the last duration (e.g. 15m, 2h).")
@click.option("--json-output/--text-output", "json_output", default=True, show_default=True)
def logs_command(
    log_file: str,
    tail_lines: int,
    boundary: str | None,
    action: str | None,
    policy_name: str | None,
    agent_id: str | None,
    tool_name: str | None,
    since: str | None,
    last: str | None,
    json_output: bool,
) -> None:
    """Query recent audit log events with optional filters."""
    path = Path(log_file).expanduser().resolve()
    logger = AuditLogger(str(path))
    try:
        events = logger.query(
            boundary=boundary,
            action=action,
            policy_name=policy_name,
            agent_id=agent_id,
            tool_name=tool_name,
            since=since,
            last=last,
            limit=tail_lines,
        )
    except Exception as exc:  # pragma: no cover - click surface.
        raise click.ClickException(str(exc)) from exc
    if not events:
        raise click.ClickException(f"No matching audit events found in {path}")

    if json_output:
        for item in events:
            click.echo(json.dumps(item, separators=(",", ":"), ensure_ascii=True))
        return

    for event in events:
        click.echo(
            " ".join(
                [
                    f"{event.get('timestamp', '-')}",
                    f"boundary={event.get('boundary', '-')}",
                    f"action={event.get('action', '-')}",
                    f"policy={event.get('policy_name') or '-'}",
                    f"agent={event.get('agent_id', '-')}",
                    f"tags={','.join(event.get('data_tags', [])) or '-'}",
                    f"reason={event.get('reason', '-')}",
                ]
            )
        )
