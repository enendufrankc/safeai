"""safeai CLI entrypoint."""

from __future__ import annotations

import click

from safeai.cli.init import init_command
from safeai.cli.logs import logs_command
from safeai.cli.scan import scan_command
from safeai.cli.serve import serve_command
from safeai.cli.validate import validate_command


@click.group()
def cli() -> None:
    """SafeAI command line interface."""


cli.add_command(init_command)
cli.add_command(validate_command)
cli.add_command(scan_command)
cli.add_command(logs_command)
cli.add_command(serve_command)
