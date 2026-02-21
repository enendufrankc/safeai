"""Generic agent installer — prints manual integration instructions."""

from __future__ import annotations

import click


def install(config_path: str = "safeai.yaml", **_kwargs: object) -> None:
    """Print instructions for integrating SafeAI with a generic agent."""
    click.echo("Generic SafeAI hook integration")
    click.echo("=" * 40)
    click.echo()
    click.echo("To integrate SafeAI with your agent, pipe JSON to the hook command:")
    click.echo()
    click.echo("  Pre-tool check:")
    click.echo(f'    echo \'{{"tool_name":"...","tool_input":{{...}},"event":"pre_tool_use"}}\' '
               f"| safeai hook --config {config_path}")
    click.echo()
    click.echo("  Post-tool check:")
    click.echo(f'    echo \'{{"tool_name":"...","tool_output":"...","event":"post_tool_use"}}\' '
               f"| safeai hook --config {config_path}")
    click.echo()
    click.echo("Exit codes: 0 = allow, 1 = block (reason on stdout), 2 = error")
    click.echo()
    click.echo("Or use the MCP server for bidirectional integration:")
    click.echo(f"    safeai mcp --config {config_path}")
