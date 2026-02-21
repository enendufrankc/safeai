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
@click.option("--data-tag", "data_tag", default=None, help="Filter by data tag (supports parent tags).")
@click.option("--phase", default=None, help="Filter by action phase in metadata (request/response).")
@click.option("--session", "session_id", default=None, help="Filter by session id.")
@click.option("--event-id", "event_id", default=None, help="Filter by exact event id.")
@click.option("--source-agent", "source_agent_id", default=None, help="Filter by source agent id.")
@click.option(
    "--destination-agent",
    "destination_agent_id",
    default=None,
    help="Filter by destination agent id.",
)
@click.option("--metadata-key", "metadata_key", default=None, help="Filter by metadata key.")
@click.option("--metadata-value", "metadata_value", default=None, help="Filter by metadata value.")
@click.option("--since", default=None, help="Filter events since ISO-8601 timestamp.")
@click.option("--until", default=None, help="Filter events until ISO-8601 timestamp.")
@click.option("--last", default=None, help="Filter events in the last duration (e.g. 15m, 2h).")
@click.option("--detail", "detail_event_id", default=None, help="Show full details for a specific event id.")
@click.option("--newest-first/--oldest-first", "newest_first", default=True, show_default=True)
@click.option("--json-output/--text-output", "json_output", default=True, show_default=True)
@click.option("--pretty/--compact", "pretty_json", default=False, show_default=True)
def logs_command(
    log_file: str,
    tail_lines: int,
    boundary: str | None,
    action: str | None,
    policy_name: str | None,
    agent_id: str | None,
    tool_name: str | None,
    data_tag: str | None,
    phase: str | None,
    session_id: str | None,
    event_id: str | None,
    source_agent_id: str | None,
    destination_agent_id: str | None,
    metadata_key: str | None,
    metadata_value: str | None,
    since: str | None,
    until: str | None,
    last: str | None,
    detail_event_id: str | None,
    newest_first: bool,
    json_output: bool,
    pretty_json: bool,
) -> None:
    """Query recent audit log events with optional filters."""
    path = Path(log_file).expanduser().resolve()
    logger = AuditLogger(str(path))
    target_event_id = detail_event_id or event_id
    try:
        events = logger.query(
            boundary=boundary,
            action=action,
            policy_name=policy_name,
            agent_id=agent_id,
            tool_name=tool_name,
            data_tag=data_tag,
            phase=phase,
            session_id=session_id,
            event_id=target_event_id,
            source_agent_id=source_agent_id,
            destination_agent_id=destination_agent_id,
            metadata_key=metadata_key,
            metadata_value=metadata_value,
            since=since,
            until=until,
            last=last,
            limit=1 if target_event_id else tail_lines,
            newest_first=newest_first,
        )
    except Exception as exc:  # pragma: no cover - click surface.
        raise click.ClickException(str(exc)) from exc
    if not events:
        raise click.ClickException(f"No matching audit events found in {path}")

    if target_event_id:
        _render_detail(
            events[0],
            json_output=json_output,
            pretty_json=pretty_json,
        )
        return

    if json_output:
        for item in events:
            if pretty_json:
                click.echo(json.dumps(item, indent=2, ensure_ascii=True, sort_keys=True))
            else:
                click.echo(json.dumps(item, separators=(",", ":"), ensure_ascii=True))
        return

    for event in events:
        metadata = event.get("metadata") or {}
        if not isinstance(metadata, dict):
            metadata = {}
        click.echo(
            " ".join(
                [
                    f"id={event.get('event_id', '-')}",
                    f"{event.get('timestamp', '-')}",
                    f"boundary={event.get('boundary', '-')}",
                    f"action={event.get('action', '-')}",
                    f"policy={event.get('policy_name') or '-'}",
                    f"agent={event.get('agent_id', '-')}",
                    f"source={event.get('source_agent_id') or '-'}",
                    f"destination={event.get('destination_agent_id') or '-'}",
                    f"session={event.get('session_id') or '-'}",
                    f"phase={metadata.get('phase', '-')}",
                    f"tool={event.get('tool_name') or '-'}",
                    f"tags={','.join(event.get('data_tags', [])) or '-'}",
                    f"reason={event.get('reason', '-')}",
                ]
            )
        )


def _render_detail(event: dict[str, object], *, json_output: bool, pretty_json: bool) -> None:
    if json_output:
        if pretty_json:
            click.echo(json.dumps(event, indent=2, ensure_ascii=True, sort_keys=True))
        else:
            click.echo(json.dumps(event, separators=(",", ":"), ensure_ascii=True))
        return

    metadata = event.get("metadata") or {}
    if not isinstance(metadata, dict):
        metadata = {}
    click.echo(f"id: {event.get('event_id', '-')}")
    click.echo(f"time: {event.get('timestamp', '-')}")
    click.echo(f"boundary: {event.get('boundary', '-')}")
    click.echo(f"action: {event.get('action', '-')}")
    click.echo(f"policy: {event.get('policy_name') or '-'}")
    click.echo(f"agent: {event.get('agent_id', '-')}")
    click.echo(f"source_agent: {event.get('source_agent_id') or '-'}")
    click.echo(f"destination_agent: {event.get('destination_agent_id') or '-'}")
    click.echo(f"session: {event.get('session_id') or '-'}")
    click.echo(f"tool: {event.get('tool_name') or '-'}")
    raw_tags = event.get("data_tags")
    tags = [str(tag) for tag in raw_tags] if isinstance(raw_tags, list) else []
    click.echo(f"tags: {','.join(tags) or '-'}")
    click.echo(f"reason: {event.get('reason', '-')}")
    click.echo(f"context_hash: {event.get('context_hash', '-')}")
    click.echo(f"metadata: {json.dumps(metadata, sort_keys=True, ensure_ascii=True)}")
