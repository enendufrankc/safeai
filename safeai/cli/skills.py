# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 SafeAI Contributors
"""safeai skills — install and manage SafeAI skills."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import click
import httpx
from rich.console import Console
from rich.table import Table

console = Console()

REGISTRY_URL = "https://raw.githubusercontent.com/enendufrankc/safeai/main/skills-registry.json"
LOCK_FILE = ".safeai/skills.json"
SKILLS_DIR = ".safeai/skills"

# Where each source directory inside a skill package is installed (relative to project root)
DEST_MAP: dict[str, str | None] = {
    "plugins": "plugins",
    "policies": "policies",
    "contracts": "contracts",
    "schemas": "schemas",
    "agents": "agents",
    "skill": None,  # → .safeai/skills/<name>/
}


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------


@click.group(name="skills")
def skills_group() -> None:
    """Install and manage SafeAI skills."""


@skills_group.command(name="add")
@click.argument("skill")
@click.option("--config", default="safeai.yaml", help="Path to safeai config file.")
@click.option("--project-path", default=".", help="Target project directory.")
@click.option("--force", is_flag=True, help="Reinstall even if already installed.")
def add_command(skill: str, config: str, project_path: str, force: bool) -> None:
    """Install a skill into the current project.

    \b
    SKILL SOURCES:
      <name>                   Install from the SafeAI skills registry
      npm:<package>            Install directly from npm
      github:<user>/<repo>     Install from a GitHub repository
      ./path/to/skill          Install from a local directory

    \b
    EXAMPLES:
      safeai skills add langchain-adapter
      safeai skills add healthcare-policies
      safeai skills add github:enendufrankc/safeai-skills/safeai-deploy
      safeai skills add ./my-custom-skill
    """
    root = Path(project_path).resolve()
    _add_skill(skill, root, force=force)


@skills_group.command(name="install")
@click.argument("skill")
@click.option("--project-path", default=".", help="Target project directory.")
@click.option("--force", is_flag=True, help="Reinstall even if already installed.")
def install_command(skill: str, project_path: str, force: bool) -> None:
    """Alias for 'safeai skills add'."""
    root = Path(project_path).resolve()
    _add_skill(skill, root, force=force)


@skills_group.command(name="remove")
@click.argument("skill")
@click.option("--project-path", default=".", help="Target project directory.")
def remove_command(skill: str, project_path: str) -> None:
    """Uninstall a skill from the current project."""
    root = Path(project_path).resolve()
    _remove_skill(skill, root)


@skills_group.command(name="list")
@click.option("--project-path", default=".", help="Target project directory.")
@click.option("--json-output", "json_out", is_flag=True, help="Output as JSON.")
def list_command(project_path: str, json_out: bool) -> None:
    """List installed skills."""
    root = Path(project_path).resolve()
    lock = _read_lock(root)
    installed = lock.get("installed", {})

    if json_out:
        click.echo(json.dumps(installed, indent=2))
        return

    if not installed:
        console.print("\n  No skills installed yet.")
        console.print("  Run: [bold]safeai skills search[/bold]\n")
        return

    table = Table(title=f"Installed Skills ({len(installed)})", show_lines=True)
    table.add_column("Name", style="bold cyan")
    table.add_column("Version")
    table.add_column("Source")
    table.add_column("Installed At")
    table.add_column("Files")

    for name, info in installed.items():
        table.add_row(
            name,
            info.get("version", "unknown"),
            info.get("source", ""),
            info.get("installed_at", "")[:10],
            str(len(info.get("files", []))),
        )

    console.print(table)


@skills_group.command(name="search")
@click.argument("query", required=False, default=None)
@click.option("--category", default=None, help="Filter by category.")
@click.option("--tag", default=None, help="Filter by tag.")
@click.option("--json-output", "json_out", is_flag=True, help="Output as JSON.")
@click.option("--project-path", default=".", help="Target project directory.")
def search_command(
    query: str | None, category: str | None, tag: str | None, json_out: bool, project_path: str
) -> None:
    """Search available skills in the registry."""
    registry = _load_registry()
    skills = registry.get("skills", [])

    if query:
        q = query.lower()
        skills = [
            s for s in skills
            if q in s["name"]
            or q in s.get("description", "").lower()
            or any(q in t for t in s.get("tags", []))
        ]
    if category:
        skills = [s for s in skills if s.get("category") == category]
    if tag:
        skills = [s for s in skills if tag in s.get("tags", [])]

    if json_out:
        click.echo(json.dumps(skills, indent=2))
        return

    if not skills:
        msg = f' for "{query}"' if query else ""
        console.print(f"\n  No skills found{msg}.\n")
        return

    root = Path(project_path).resolve()
    lock = _read_lock(root)
    installed = lock.get("installed", {})

    label = f'Skills matching "{query}"' if query else "Available Skills"
    table = Table(title=f"{label} ({len(skills)})", show_lines=True)
    table.add_column("Name", style="bold cyan")
    table.add_column("Version")
    table.add_column("Category")
    table.add_column("Description")
    table.add_column("Installed", style="green")

    for s in skills:
        inst = "✓ " + installed[s["name"]]["version"] if s["name"] in installed else ""
        table.add_row(
            s["name"],
            s.get("version", ""),
            s.get("category", ""),
            s.get("description", "")[:60] + ("…" if len(s.get("description", "")) > 60 else ""),
            inst,
        )

    console.print(table)
    console.print("\n  Install with: [bold]safeai skills add <name>[/bold]\n")


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------


def _add_skill(name_or_source: str, root: Path, force: bool = False) -> None:
    name, source = _resolve_source(name_or_source)
    lock = _read_lock(root)

    if name in lock["installed"] and not force:
        ver = lock["installed"][name]["version"]
        console.print(f"\n  [yellow][i] {name}@{ver} is already installed.[/yellow]")
        console.print("  Use [bold]--force[/bold] to reinstall.\n")
        return

    console.print(f"\n  Installing skill: [bold cyan]{name}[/bold cyan]  ({source})\n")

    with tempfile.TemporaryDirectory(prefix="safeai-skill-") as tmp:
        tmp_path = Path(tmp)
        skill_dir = _download(source, tmp_path, name)
        manifest = _read_manifest(skill_dir)
        installed_files = _install_files(skill_dir, manifest, name, root)

    lock["installed"][name] = {
        "version": manifest.get("version", "unknown"),
        "source": source,
        "installed_at": datetime.now(timezone.utc).isoformat(),
        "files": installed_files,
    }
    _write_lock(root, lock)

    console.print(f"\n  [green]✓ Installed:[/green] {name}@{manifest.get('version', 'unknown')}")
    if manifest.get("description"):
        console.print(f"    {manifest['description']}")
    if installed_files:
        console.print("\n  Files installed:")
        for f in installed_files:
            console.print(f"    · {f}")
    if manifest.get("postInstall"):
        console.print(f"\n  [bold]Post-install note:[/bold] {manifest['postInstall']}")
    console.print("")


def _remove_skill(name: str, root: Path) -> None:
    lock = _read_lock(root)
    entry = lock["installed"].get(name)
    if not entry:
        console.print(f"\n  [yellow][i] Skill '{name}' is not installed.[/yellow]\n")
        return

    removed = []
    for rel in entry.get("files", []):
        abs_path = root / rel
        if abs_path.exists():
            if abs_path.is_dir():
                shutil.rmtree(abs_path)
            else:
                abs_path.unlink()
            removed.append(rel)

    # Remove skill directory if it exists
    skill_dir = root / SKILLS_DIR / name
    if skill_dir.exists():
        shutil.rmtree(skill_dir)

    del lock["installed"][name]
    _write_lock(root, lock)

    console.print(f"\n  [green]✓ Removed:[/green] {name}")
    for f in removed:
        console.print(f"    · {f}")
    console.print("")


# ---------------------------------------------------------------------------
# Source resolution
# ---------------------------------------------------------------------------


def _resolve_source(input_: str) -> tuple[str, str]:
    if input_.startswith(("./", "/", "../")):
        abs_path = Path(input_).resolve()
        manifest = _read_manifest(abs_path)
        return manifest.get("name", abs_path.name), f"local:{abs_path}"

    if input_.startswith("npm:"):
        pkg = input_[4:]
        return pkg.removeprefix("safeai-skill-"), input_

    if input_.startswith("github:"):
        parts = input_[7:].split("/")
        name = parts[-1].removeprefix("safeai-skill-").split("@")[0]
        return name, input_

    # Registry lookup
    registry = _load_registry()
    for skill in registry.get("skills", []):
        if skill["name"] == input_:
            return skill["name"], skill["source"]

    # Fall back to npm
    return input_.removeprefix("safeai-skill-"), f"npm:safeai-skill-{input_}"


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------


def _download(source: str, tmp: Path, name: str) -> Path:
    if source.startswith("local:"):
        return Path(source[6:])

    if source.startswith("npm:"):
        return _download_npm(source[4:], tmp)

    if source.startswith("github:"):
        return _download_github(source[7:], tmp, name)

    raise ValueError(f"Unknown source format: {source}")


def _download_npm(pkg: str, tmp: Path) -> Path:
    console.print(f"  Downloading from npm: [dim]{pkg}[/dim]")
    try:
        subprocess.run(
            ["npm", "pack", pkg, "--pack-destination", str(tmp), "--quiet"],
            check=True, capture_output=True,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"npm pack failed for '{pkg}': {e.stderr.decode()}") from e

    tarballs = list(tmp.glob("*.tgz"))
    if not tarballs:
        raise RuntimeError(f"npm pack produced no tarball for {pkg}")

    extract_dir = tmp / "extracted"
    extract_dir.mkdir()
    subprocess.run(["tar", "xzf", str(tarballs[0]), "-C", str(extract_dir)], check=True)

    package_dir = extract_dir / "package"
    return package_dir if package_dir.exists() else extract_dir


def _download_github(spec: str, tmp: Path, name: str) -> Path:
    parts = spec.split("/")
    if len(parts) >= 3:
        user, repo_and_ref = parts[0], parts[1]
        subparts = parts[2:]
        subpath: str | None = "/".join(subparts) if subparts else None
    else:
        user, repo_and_ref = parts[0], parts[1]
        subpath = None

    repo, ref = (repo_and_ref.split("@") + ["main"])[:2]
    zip_url = f"https://github.com/{user}/{repo}/archive/refs/heads/{ref}.zip"
    console.print(f"  Downloading from GitHub: [dim]{user}/{repo}@{ref}[/dim]")

    zip_path = tmp / "skill.zip"
    with httpx.stream("GET", zip_url, follow_redirects=True) as r:
        r.raise_for_status()
        with open(zip_path, "wb") as f:
            for chunk in r.iter_bytes():
                f.write(chunk)

    extract_dir = tmp / "extracted"
    extract_dir.mkdir()
    subprocess.run(["unzip", "-q", str(zip_path), "-d", str(extract_dir)], check=True)

    root_folders = [d for d in extract_dir.iterdir() if d.is_dir()]
    skill_dir = root_folders[0]
    if subpath:
        skill_dir = skill_dir / subpath
    return skill_dir


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------


def _read_manifest(skill_dir: Path) -> dict:
    manifest_path = skill_dir / "safeai-skill.json"
    if manifest_path.exists():
        return json.loads(manifest_path.read_text())
    pkg_path = skill_dir / "package.json"
    if pkg_path.exists():
        pkg = json.loads(pkg_path.read_text())
        return {"name": pkg.get("name"), "version": pkg.get("version"), "description": pkg.get("description")}
    return {"name": skill_dir.name, "version": "unknown"}


# ---------------------------------------------------------------------------
# File installation
# ---------------------------------------------------------------------------


def _install_files(skill_dir: Path, manifest: dict, name: str, root: Path) -> list[str]:
    installed: list[str] = []

    for entry in skill_dir.iterdir():
        if entry.is_dir():
            if entry.name == "skill":
                dest = root / SKILLS_DIR / name
                dest.mkdir(parents=True, exist_ok=True)
                shutil.copytree(entry, dest, dirs_exist_ok=True)
                installed.append(f"{SKILLS_DIR}/{name}")
            elif entry.name in DEST_MAP and DEST_MAP[entry.name] is not None:
                dest_name = DEST_MAP[entry.name]
                assert dest_name is not None
                dest_dir = root / dest_name
                dest_dir.mkdir(parents=True, exist_ok=True)
                for src_file in _list_files(entry):
                    rel = src_file.relative_to(entry)
                    dest_file = dest_dir / rel
                    dest_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_file, dest_file)
                    installed.append(str(Path(dest_name) / rel))
        elif entry.name == "plugin.py":
            dest_dir = root / "plugins"
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / f"{name}.py"
            shutil.copy2(entry, dest)
            installed.append(f"plugins/{name}.py")

    return installed


def _list_files(directory: Path) -> list[Path]:
    files = []
    for p in directory.rglob("*"):
        if p.is_file():
            files.append(p)
    return files


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def _load_registry() -> dict:
    try:
        resp = httpx.get(REGISTRY_URL, timeout=3.0)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        pass

    # Fall back to bundled registry (next to this package)
    bundled = Path(__file__).parent.parent.parent / "skills-registry.json"
    if bundled.exists():
        return json.loads(bundled.read_text())
    return {"version": "1", "skills": []}


# ---------------------------------------------------------------------------
# Lock file
# ---------------------------------------------------------------------------


def _read_lock(root: Path) -> dict:
    lock_path = root / LOCK_FILE
    if not lock_path.exists():
        return {"version": "1", "installed": {}}
    try:
        return json.loads(lock_path.read_text())
    except Exception:
        return {"version": "1", "installed": {}}


def _write_lock(root: Path, lock: dict) -> None:
    lock_path = root / LOCK_FILE
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(json.dumps(lock, indent=2))
