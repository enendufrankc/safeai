"""safeai CLI entrypoint."""

from __future__ import annotations

import click

from safeai.cli.approvals import approvals_group
from safeai.cli.hook import hook_command
from safeai.cli.init import init_command
from safeai.cli.logs import logs_command
from safeai.cli.mcp import mcp_command
from safeai.cli.scan import scan_command
from safeai.cli.serve import serve_command
from safeai.cli.setup import setup_group
from safeai.cli.templates import templates_group
from safeai.cli.intelligence import intelligence_group
from safeai.cli.validate import validate_command


@click.group()
def cli() -> None:
    """SafeAI command line interface."""


cli.add_command(init_command)
cli.add_command(validate_command)
cli.add_command(scan_command)
cli.add_command(logs_command)
cli.add_command(serve_command)
cli.add_command(approvals_group)
cli.add_command(templates_group)
cli.add_command(hook_command)
cli.add_command(setup_group)
cli.add_command(mcp_command)
cli.add_command(intelligence_group)
