"""safeai approvals command group."""

from __future__ import annotations

import json

import click

from safeai.api import SafeAI


@click.group(name="approvals")
def approvals_group() -> None:
    """Inspect and decide approval requests."""


@approvals_group.command(name="list")
@click.option("--config", "config_path", default="safeai.yaml", show_default=True, help="Config path.")
@click.option(
    "--status",
    default="pending",
    show_default=True,
    type=click.Choice(["pending", "approved", "denied", "expired", "all"], case_sensitive=False),
)
@click.option("--agent", "agent_id", default=None, help="Filter by agent id.")
@click.option("--tool", "tool_name", default=None, help="Filter by tool name.")
@click.option("--limit", default=50, show_default=True, type=int)
@click.option("--json-output/--text-output", "json_output", default=True, show_default=True)
def approvals_list_command(
    config_path: str,
    status: str,
    agent_id: str | None,
    tool_name: str | None,
    limit: int,
    json_output: bool,
) -> None:
    """List approval requests."""
    sdk = SafeAI.from_config(config_path)
    rows = sdk.list_approval_requests(
        status=None if status == "all" else status,
        agent_id=agent_id,
        tool_name=tool_name,
        limit=limit,
    )
    if json_output:
        for row in rows:
            click.echo(
                json.dumps(
                    {
                        "request_id": row.request_id,
                        "status": row.status,
                        "reason": row.reason,
                        "policy_name": row.policy_name,
                        "agent_id": row.agent_id,
                        "tool_name": row.tool_name,
                        "session_id": row.session_id,
                        "requested_at": row.requested_at.isoformat(),
                        "expires_at": row.expires_at.isoformat(),
                        "decided_at": row.decided_at.isoformat() if row.decided_at else None,
                        "approver_id": row.approver_id,
                        "decision_note": row.decision_note,
                        "metadata": row.metadata or {},
                    },
                    separators=(",", ":"),
                    ensure_ascii=True,
                )
            )
        return

    for row in rows:
        click.echo(
            " ".join(
                [
                    f"id={row.request_id}",
                    f"status={row.status}",
                    f"agent={row.agent_id}",
                    f"tool={row.tool_name}",
                    f"session={row.session_id or '-'}",
                    f"requested={row.requested_at.isoformat()}",
                    f"expires={row.expires_at.isoformat()}",
                    f"reason={row.reason}",
                ]
            )
        )


@approvals_group.command(name="approve")
@click.argument("request_id")
@click.option("--config", "config_path", default="safeai.yaml", show_default=True, help="Config path.")
@click.option("--approver", "approver_id", required=True, help="Approver identity.")
@click.option("--note", default=None, help="Optional approval note.")
def approvals_approve_command(request_id: str, config_path: str, approver_id: str, note: str | None) -> None:
    """Approve a pending request."""
    sdk = SafeAI.from_config(config_path)
    if not sdk.approve_request(request_id, approver_id=approver_id, note=note):
        raise click.ClickException(f"Unable to approve request '{request_id}'.")
    click.echo(f"Approved: {request_id}")


@approvals_group.command(name="deny")
@click.argument("request_id")
@click.option("--config", "config_path", default="safeai.yaml", show_default=True, help="Config path.")
@click.option("--approver", "approver_id", required=True, help="Approver identity.")
@click.option("--note", default=None, help="Optional denial note.")
def approvals_deny_command(request_id: str, config_path: str, approver_id: str, note: str | None) -> None:
    """Deny a pending request."""
    sdk = SafeAI.from_config(config_path)
    if not sdk.deny_request(request_id, approver_id=approver_id, note=note):
        raise click.ClickException(f"Unable to deny request '{request_id}'.")
    click.echo(f"Denied: {request_id}")
