"""CLI command for running the SafeAI MCP server."""

from __future__ import annotations

import asyncio
import sys

import click


@click.command("mcp")
@click.option("--config", default="safeai.yaml", help="Path to safeai.yaml config file.")
def mcp_command(config: str) -> None:
    """Start the SafeAI MCP server (stdio transport)."""
    try:
        from safeai.mcp.server import run_stdio_server
    except ImportError:
        click.echo(
            "Error: The 'mcp' package is required for the MCP server.\n"
            "Install it with: pip install 'safeai[mcp]'",
            err=True,
        )
        sys.exit(1)

    try:
        asyncio.run(run_stdio_server(config))
    except KeyboardInterrupt:
        pass
