"""safeai init command."""

from __future__ import annotations

import shutil
from pathlib import Path

import click

DEFAULT_FILES = {
    Path("safeai.yaml"): Path("config/defaults/safeai.yaml"),
    Path("policies/default.yaml"): Path("config/defaults/policies/default.yaml"),
    Path("contracts/example.yaml"): Path("config/defaults/contracts/example.yaml"),
    Path("schemas/memory.yaml"): Path("config/defaults/schemas/memory.yaml"),
}


@click.command(name="init")
@click.option("--path", "target_path", default=".", show_default=True, help="Project directory.")
def init_command(target_path: str) -> None:
    """Scaffold default SafeAI config files."""
    base = Path(target_path).expanduser().resolve()
    package_root = Path(__file__).resolve().parents[1]

    created: list[Path] = []
    skipped: list[Path] = []

    for rel_target, rel_source in DEFAULT_FILES.items():
        source = package_root / rel_source
        target = base / rel_target
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            skipped.append(target)
            continue
        shutil.copyfile(source, target)
        created.append(target)

    click.echo("SafeAI initialized")
    for path in created:
        click.echo(f"  created: {path}")
    for path in skipped:
        click.echo(f"  skipped: {path} (already exists)")
