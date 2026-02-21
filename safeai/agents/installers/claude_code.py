"""Claude Code hook installer — writes .claude/settings.json."""

from __future__ import annotations

import json
from pathlib import Path

import click


def install(config_path: str = "safeai.yaml", project_path: str = ".") -> None:
    """Install SafeAI hooks into a Claude Code project."""
    project = Path(project_path).resolve()
    settings_dir = project / ".claude"
    settings_file = settings_dir / "settings.json"

    hook_cmd = f"safeai hook --config {config_path} --profile claude-code"

    hooks = {
        "PreToolUse": hook_cmd + " --event pre_tool_use",
        "PostToolUse": hook_cmd + " --event post_tool_use",
    }

    settings: dict = {}
    if settings_file.exists():
        try:
            settings = json.loads(settings_file.read_text())
        except (json.JSONDecodeError, OSError):
            pass

    settings.setdefault("hooks", {})
    for event, cmd in hooks.items():
        existing = settings["hooks"].get(event, [])
        if cmd not in existing:
            existing.append(cmd)
        settings["hooks"][event] = existing

    settings_dir.mkdir(parents=True, exist_ok=True)
    settings_file.write_text(json.dumps(settings, indent=2) + "\n")
    click.echo(f"Wrote Claude Code hooks to {settings_file}")
