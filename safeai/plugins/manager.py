# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 SafeAI Contributors
"""Dynamic plugin loader for detectors, adapters, and policy templates."""

from __future__ import annotations

import importlib.util
import logging
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Callable

from safeai.config.loader import resolve_files

logger = logging.getLogger(__name__)

DetectorTuple = tuple[str, str, str]
AdapterFactory = Callable[[Any], Any] | type


@dataclass(frozen=True)
class PluginModule:
    name: str
    path: str
    detectors: tuple[DetectorTuple, ...]
    adapters: dict[str, AdapterFactory]
    policy_templates: dict[str, dict[str, Any]]


class PluginManager:
    """Load and expose plugin-provided runtime extensions."""

    def __init__(self, plugins: list[PluginModule] | None = None) -> None:
        self._plugins = list(plugins or [])

    @classmethod
    def from_patterns(cls, *, config_path: str | Path, patterns: list[str]) -> "PluginManager":
        files = resolve_files(config_path, patterns)
        plugins = [load_plugin(file_path) for file_path in files]
        return cls(plugins)

    def list_plugins(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for plugin in self._plugins:
            rows.append(
                {
                    "name": plugin.name,
                    "path": plugin.path,
                    "detector_count": len(plugin.detectors),
                    "adapter_count": len(plugin.adapters),
                    "template_count": len(plugin.policy_templates),
                }
            )
        return rows

    def detector_patterns(self) -> list[DetectorTuple]:
        rows: list[DetectorTuple] = []
        seen: set[DetectorTuple] = set()
        for plugin in self._plugins:
            for detector in plugin.detectors:
                if detector in seen:
                    continue
                seen.add(detector)
                rows.append(detector)
        return rows

    def adapter_names(self) -> list[str]:
        return sorted({name for plugin in self._plugins for name in plugin.adapters.keys()})

    def build_adapter(self, name: str, safeai: Any) -> Any:
        token = str(name).strip().lower()
        if not token:
            raise KeyError("adapter name is required")
        for plugin in self._plugins:
            factory = plugin.adapters.get(token)
            if factory is None:
                continue
            if isinstance(factory, type):
                return factory(safeai)
            return factory(safeai)
        raise KeyError(f"plugin adapter '{token}' not found")

    def policy_templates(self) -> dict[str, dict[str, Any]]:
        rows: dict[str, dict[str, Any]] = {}
        for plugin in self._plugins:
            for name, payload in plugin.policy_templates.items():
                rows[name] = payload
        return rows


def load_plugin(path: str | Path) -> PluginModule:
    file_path = Path(path).expanduser().resolve()
    try:
        module_name = f"safeai_plugin_{file_path.stem}_{abs(hash(str(file_path))) & 0xFFFFFFF:x}"
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            raise ValueError(f"Unable to load plugin module spec from {file_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        name = str(getattr(module, "SAFEAI_PLUGIN_NAME", file_path.stem))
        detectors = _normalize_detectors(
            _call_or_attr(module, "safeai_detectors", "SAFEAI_DETECTORS", default=[]),
            plugin_name=name,
        )
        adapters = _normalize_adapters(
            _call_or_attr(module, "safeai_adapters", "SAFEAI_ADAPTERS", default={}),
            plugin_name=name,
        )
        templates = _normalize_templates(
            _call_or_attr(module, "safeai_policy_templates", "SAFEAI_POLICY_TEMPLATES", default={}),
            plugin_name=name,
        )
        logger.info(
            "Loaded plugin '%s': %d detectors, %d adapters, %d templates",
            name,
            len(detectors),
            len(adapters),
            len(templates),
        )
        return PluginModule(
            name=name,
            path=str(file_path),
            detectors=detectors,
            adapters=adapters,
            policy_templates=templates,
        )
    except Exception as exc:
        logger.warning("Failed to load plugin '%s': %s", path, exc)
        raise


def _call_or_attr(module: ModuleType, fn_name: str, attr_name: str, *, default: Any) -> Any:
    callback = getattr(module, fn_name, None)
    if callable(callback):
        return callback()
    value = getattr(module, attr_name, default)
    return value


def _normalize_detectors(value: Any, *, plugin_name: str = "") -> tuple[DetectorTuple, ...]:
    rows: list[DetectorTuple] = []
    if not isinstance(value, (list, tuple)):
        return ()
    for item in value:
        if not isinstance(item, (list, tuple)) or len(item) < 3:
            logger.debug("Skipped invalid detector in '%s': expected tuple of 3+, got %r", plugin_name, item)
            continue
        name = str(item[0]).strip()
        tag = str(item[1]).strip().lower()
        pattern = str(item[2]).strip()
        if not name or not tag or not pattern:
            logger.debug("Skipped invalid detector in '%s': empty field in (%r, %r, %r)", plugin_name, name, tag, pattern)
            continue
        rows.append((name, tag, pattern))
    return tuple(rows)


def _normalize_adapters(value: Any, *, plugin_name: str = "") -> dict[str, AdapterFactory]:
    if not isinstance(value, dict):
        return {}
    rows: dict[str, AdapterFactory] = {}
    for key, item in value.items():
        name = str(key).strip().lower()
        if not name:
            logger.debug("Skipped invalid adapter in '%s': empty key", plugin_name)
            continue
        if not callable(item) and not isinstance(item, type):
            logger.debug("Skipped invalid adapter in '%s': '%s' is not callable", plugin_name, key)
            continue
        rows[name] = item
    return rows


def _normalize_templates(value: Any, *, plugin_name: str = "") -> dict[str, dict[str, Any]]:
    if not isinstance(value, dict):
        return {}
    rows: dict[str, dict[str, Any]] = {}
    for key, item in value.items():
        name = str(key).strip().lower()
        if not name or not isinstance(item, dict):
            logger.debug("Skipped invalid template in '%s': key=%r, value type=%s", plugin_name, key, type(item).__name__)
            continue
        rows[name] = dict(item)
    return rows
