"""safeai templates command group."""

from __future__ import annotations

import json

import click
import yaml  # type: ignore[import-untyped]

from safeai.api import SafeAI


@click.group(name="templates")
def templates_group() -> None:
    """Inspect built-in and plugin-provided policy templates."""


@templates_group.command(name="list")
@click.option("--config", "config_path", default="safeai.yaml", show_default=True, help="Config path.")
def templates_list_command(config_path: str) -> None:
    """List available policy templates."""
    sdk = SafeAI.from_config(config_path)
    rows = sdk.list_policy_templates()
    if not rows:
        click.echo("No policy templates found.")
        return
    click.echo(f"{'name':<24} {'source':<12} path")
    click.echo("-" * 72)
    for item in rows:
        click.echo(
            f"{str(item.get('name', '')):<24} {str(item.get('source', '')):<12} {str(item.get('path', '-'))}"
        )


@templates_group.command(name="show")
@click.option("--config", "config_path", default="safeai.yaml", show_default=True, help="Config path.")
@click.option("--name", "template_name", required=True, help="Template name.")
@click.option("--format", "output_format", type=click.Choice(["yaml", "json"]), default="yaml", show_default=True)
def templates_show_command(config_path: str, template_name: str, output_format: str) -> None:
    """Render one policy template."""
    sdk = SafeAI.from_config(config_path)
    try:
        payload = sdk.load_policy_template(template_name)
    except KeyError as exc:
        raise click.ClickException(str(exc)) from exc
    if output_format == "json":
        click.echo(json.dumps(payload, indent=2, sort_keys=False, ensure_ascii=True))
        return
    click.echo(yaml.safe_dump(payload, sort_keys=False))
