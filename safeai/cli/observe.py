"""safeai observe command group."""

from __future__ import annotations

import click

from safeai.api import SafeAI


@click.group(name="observe")
def observe_group() -> None:
    """Agent observability and session tracing."""


@observe_group.command(name="agents")
@click.option("--config", "config_path", default="safeai.yaml", show_default=True, help="Config path.")
@click.option("--last", default="24h", show_default=True, help="Time window (e.g. 1h, 24h, 7d).")
def observe_agents_command(config_path: str, last: str) -> None:
    """List agents with event counts."""
    sdk = SafeAI.from_config(config_path)
    events = sdk.query_audit(last=last, limit=50000, newest_first=True)
    agents: dict[str, dict[str, int | str | None]] = {}
    for event in events:
        agent_id = str(event.get("agent_id", "unknown"))
        if agent_id not in agents:
            agents[agent_id] = {"event_count": 0, "last_seen": None}
        agents[agent_id]["event_count"] = int(agents[agent_id]["event_count"] or 0) + 1
        if agents[agent_id]["last_seen"] is None:
            agents[agent_id]["last_seen"] = event.get("timestamp")
    if not agents:
        click.echo(f"No agent activity found in last {last}.")
        return
    click.echo(f"{'agent_id':<30} {'events':>8}  last_seen")
    click.echo("-" * 80)
    for agent_id, info in sorted(agents.items(), key=lambda x: x[1].get("event_count", 0), reverse=True):
        click.echo(f"{agent_id:<30} {info['event_count']:>8}  {info.get('last_seen', '-')}")


@observe_group.command(name="sessions")
@click.option("--config", "config_path", default="safeai.yaml", show_default=True, help="Config path.")
@click.option("--session", "session_id", required=True, help="Session ID to trace.")
@click.option("--limit", default=100, show_default=True, help="Max events to show.")
def observe_sessions_command(config_path: str, session_id: str, limit: int) -> None:
    """Show event trace for a session."""
    sdk = SafeAI.from_config(config_path)
    events = sdk.query_audit(session_id=session_id, limit=limit, newest_first=False)
    if not events:
        click.echo(f"No events found for session '{session_id}'.")
        return
    click.echo(f"Session: {session_id} ({len(events)} events)")
    click.echo("-" * 80)
    for event in events:
        ts = event.get("timestamp", "-")
        boundary = event.get("boundary", "-")
        action = event.get("action", "-")
        agent = event.get("agent_id", "-")
        reason = event.get("reason", "-")
        click.echo(f"  {ts}  {boundary:<10} {action:<8} agent={agent}  {reason}")
