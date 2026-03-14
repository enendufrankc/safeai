# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 SafeAI Contributors
"""safeai plugins CLI commands."""

from __future__ import annotations

from pathlib import Path

import click

from safeai.cli import ui


@click.group(name="plugins")
def plugins_group() -> None:
    """Manage SafeAI plugins."""


@plugins_group.command(name="list")
@click.option("--config", "config_path", default="safeai.yaml", show_default=True, help="Path to safeai.yaml.")
def list_plugins(config_path: str) -> None:
    """List loaded plugins and their contributions."""
    config_file = Path(config_path).expanduser().resolve()
    if not config_file.exists():
        ui.bar(f"Config not found: {config_file}", style="red")
        ui.bar("Tip: Run 'safeai init' to create default config.", style="dim")
        raise SystemExit(1)

    from safeai.api import SafeAI

    sdk = SafeAI.from_config(config_file)
    plugins = sdk.list_plugins()

    if not plugins:
        ui.bar("No plugins loaded.")
        ui.bar("Tip: Add .py files to plugins/ and set plugins.enabled: true in safeai.yaml.", style="dim")
        return

    ui.step_active(f"Loaded {len(plugins)} plugin(s)")
    for plugin in plugins:
        name = plugin.get("name", "unknown")
        detectors = plugin.get("detector_count", 0)
        adapters = plugin.get("adapter_count", 0)
        templates = plugin.get("template_count", 0)
        ui.bar(f"  {name}: {detectors} detectors, {adapters} adapters, {templates} templates")
