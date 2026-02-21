"""Cursor AI hook installer."""

from __future__ import annotations

from pathlib import Path

import click


def install(config_path: str = "safeai.yaml", project_path: str = ".") -> None:
    """Install SafeAI hooks into a Cursor project."""
    project = Path(project_path).resolve()
    rules_dir = project / ".cursor"
    rules_file = rules_dir / "rules"

    hook_cmd = f"safeai hook --config {config_path} --profile cursor"

    block = (
        "\n# SafeAI boundary enforcement\n"
        f"pre_tool_use: {hook_cmd} --event pre_tool_use\n"
        f"post_tool_use: {hook_cmd} --event post_tool_use\n"
    )

    rules_dir.mkdir(parents=True, exist_ok=True)

    existing = ""
    if rules_file.exists():
        existing = rules_file.read_text()

    if "safeai hook" not in existing:
        rules_file.write_text(existing + block)
        click.echo(f"Wrote Cursor hooks to {rules_file}")
    else:
        click.echo(f"SafeAI hooks already present in {rules_file}")
