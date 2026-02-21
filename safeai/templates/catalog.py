"""Policy template catalog (built-in + plugin-provided packs)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from safeai.plugins.manager import PluginManager


class PolicyTemplateCatalog:
    """Lookup and load policy templates from built-in and plugin sources."""

    def __init__(self, plugin_manager: PluginManager | None = None) -> None:
        self._plugins = plugin_manager or PluginManager()
        self._builtin_templates = _discover_builtin_templates()
        self._plugin_templates = self._plugins.policy_templates()

    def list_templates(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for name in sorted(self._builtin_templates.keys()):
            rows.append({"name": name, "source": "builtin", "path": str(self._builtin_templates[name])})
        for name in sorted(self._plugin_templates.keys()):
            rows.append({"name": name, "source": "plugin", "path": None})
        return rows

    def load(self, name: str) -> dict[str, Any]:
        token = str(name).strip().lower()
        if not token:
            raise KeyError("template name is required")
        plugin_doc = self._plugin_templates.get(token)
        if plugin_doc is not None:
            return dict(plugin_doc)
        file_path = self._builtin_templates.get(token)
        if file_path is None:
            raise KeyError(f"policy template '{token}' not found")
        loaded = yaml.safe_load(file_path.read_text(encoding="utf-8")) or {}
        if not isinstance(loaded, dict):
            raise ValueError(f"Policy template '{token}' at {file_path} is not a YAML object")
        return loaded


def _discover_builtin_templates() -> dict[str, Path]:
    template_dir = Path(__file__).resolve().parents[1] / "config" / "defaults" / "policies" / "templates"
    rows: dict[str, Path] = {}
    if not template_dir.exists():
        return rows
    for file_path in sorted(template_dir.glob("*.yaml")):
        rows[file_path.stem.strip().lower()] = file_path
    return rows
