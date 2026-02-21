"""CLI commands for setting up SafeAI hooks in coding agents."""

from __future__ import annotations

import click


@click.group("setup")
def setup_group() -> None:
    """Set up SafeAI hooks for a coding agent."""


@setup_group.command("claude-code")
@click.option("--config", default="safeai.yaml", help="Path to safeai.yaml config file.")
@click.option("--path", default=".", help="Project directory to install hooks into.")
def setup_claude_code(config: str, path: str) -> None:
    """Install SafeAI hooks for Claude Code."""
    from safeai.agents.installers.claude_code import install

    install(config_path=config, project_path=path)


@setup_group.command("cursor")
@click.option("--config", default="safeai.yaml", help="Path to safeai.yaml config file.")
@click.option("--path", default=".", help="Project directory to install hooks into.")
def setup_cursor(config: str, path: str) -> None:
    """Install SafeAI hooks for Cursor."""
    from safeai.agents.installers.cursor import install

    install(config_path=config, project_path=path)


@setup_group.command("generic")
@click.option("--config", default="safeai.yaml", help="Path to safeai.yaml config file.")
def setup_generic(config: str) -> None:
    """Print instructions for manual SafeAI hook integration."""
    from safeai.agents.installers.generic import install

    install(config_path=config)
