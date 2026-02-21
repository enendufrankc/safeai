"""safeai validate command."""

from __future__ import annotations

from pathlib import Path

import click

from safeai.config.loader import (
    load_config,
    load_contract_documents,
    load_identity_documents,
    load_memory_documents,
    load_policy_documents,
)


@click.command(name="validate")
@click.option("--config", "config_path", default="safeai.yaml", show_default=True, help="Config path.")
def validate_command(config_path: str) -> None:
    """Validate config and policy files parse successfully."""
    try:
        cfg = load_config(config_path)
        policies = load_policy_documents(config_path, cfg.paths.policy_files, version=cfg.version)
        memories = load_memory_documents(config_path, cfg.paths.memory_schema_files, version=cfg.version)
        contracts = load_contract_documents(config_path, cfg.paths.contract_files, version=cfg.version)
        identities = load_identity_documents(config_path, cfg.paths.identity_files, version=cfg.version)
    except Exception as exc:  # pragma: no cover - surfaced via click CLI.
        raise click.ClickException(str(exc)) from exc

    if not policies:
        raise click.ClickException("No policies found. Check paths.policy_files.")
    if not memories:
        raise click.ClickException("No memory schemas found. Check paths.memory_schema_files.")
    if not contracts:
        raise click.ClickException("No tool contracts found. Check paths.contract_files.")
    if cfg.paths.identity_files and not identities:
        raise click.ClickException("No agent identity files found. Check paths.identity_files.")

    resolved = Path(config_path).expanduser().resolve()
    click.echo(f"Config valid: {resolved}")
    click.echo(f"Policies loaded: {len(policies)}")
    click.echo(f"Tool contracts loaded: {len(contracts)}")
    click.echo(f"Memory schemas loaded: {len(memories)}")
    click.echo(f"Agent identities loaded: {len(identities)}")
