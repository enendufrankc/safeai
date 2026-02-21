"""Metadata sanitizer — ensures AI agents never see raw protected data."""

from __future__ import annotations

import ast
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

BANNED_METADATA_KEYS = frozenset({
    "secret_key",
    "capability_token_id",
    "matched_value",
    "raw_content",
    "raw_input",
    "raw_output",
})

SAFE_METADATA_KEYS = frozenset({
    "phase",
    "action_type",
    "message_length",
    "filtered_length",
    "purged_count",
    "resolution",
    "encrypted",
    "secret_backend",
    "result",
})

_EVENT_PASSTHROUGH_KEYS = frozenset({
    "event_id",
    "timestamp",
    "boundary",
    "action",
    "policy_name",
    "reason",
    "data_tags",
    "agent_id",
    "tool_name",
    "session_id",
    "source_agent_id",
    "destination_agent_id",
})


@dataclass(frozen=True)
class SanitizedAuditEvent:
    event_id: str = ""
    timestamp: str = ""
    boundary: str = ""
    action: str = ""
    policy_name: str = ""
    reason: str = ""
    data_tags: tuple[str, ...] = ()
    agent_id: str = ""
    tool_name: str = ""
    session_id: str = ""
    source_agent_id: str = ""
    destination_agent_id: str = ""
    safe_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SanitizedAuditAggregate:
    total_events: int = 0
    events_by_action: dict[str, int] = field(default_factory=dict)
    events_by_boundary: dict[str, int] = field(default_factory=dict)
    events_by_policy: dict[str, int] = field(default_factory=dict)
    events_by_agent: dict[str, int] = field(default_factory=dict)
    events_by_tool: dict[str, int] = field(default_factory=dict)
    events_by_tag: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class CodebaseStructure:
    """Structural metadata extracted from a project — no file body content."""

    file_paths: tuple[str, ...] = ()
    imports: tuple[str, ...] = ()
    class_names: tuple[str, ...] = ()
    function_names: tuple[str, ...] = ()
    decorators: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    framework_hints: tuple[str, ...] = ()


class MetadataSanitizer:
    """Strips raw values from audit events and extracts safe metadata."""

    def __init__(self, *, metadata_only: bool = True) -> None:
        self._metadata_only = metadata_only

    def sanitize_event(self, event: dict[str, Any]) -> SanitizedAuditEvent:
        safe_meta: dict[str, Any] = {}
        raw_meta = event.get("metadata") or {}
        for k, v in raw_meta.items():
            if k in BANNED_METADATA_KEYS:
                continue
            if k in SAFE_METADATA_KEYS:
                safe_meta[k] = v

        kwargs: dict[str, Any] = {}
        for key in _EVENT_PASSTHROUGH_KEYS:
            val = event.get(key, "")
            if key == "data_tags":
                kwargs[key] = tuple(val) if isinstance(val, (list, tuple)) else ()
            else:
                kwargs[key] = str(val) if val is not None else ""

        return SanitizedAuditEvent(**kwargs, safe_metadata=safe_meta)

    def aggregate_events(self, events: list[dict[str, Any]]) -> SanitizedAuditAggregate:
        by_action: Counter[str] = Counter()
        by_boundary: Counter[str] = Counter()
        by_policy: Counter[str] = Counter()
        by_agent: Counter[str] = Counter()
        by_tool: Counter[str] = Counter()
        by_tag: Counter[str] = Counter()

        for ev in events:
            by_action[ev.get("action", "unknown")] += 1
            by_boundary[ev.get("boundary", "unknown")] += 1
            policy = ev.get("policy_name", "unknown")
            if policy:
                by_policy[policy] += 1
            agent = ev.get("agent_id", "unknown")
            if agent:
                by_agent[agent] += 1
            tool = ev.get("tool_name", "")
            if tool:
                by_tool[tool] += 1
            for tag in ev.get("data_tags", []):
                by_tag[tag] += 1

        return SanitizedAuditAggregate(
            total_events=len(events),
            events_by_action=dict(by_action),
            events_by_boundary=dict(by_boundary),
            events_by_policy=dict(by_policy),
            events_by_agent=dict(by_agent),
            events_by_tool=dict(by_tool),
            events_by_tag=dict(by_tag),
        )

    def extract_codebase_structure(self, project_path: str | Path) -> CodebaseStructure:
        root = Path(project_path).resolve()
        if not root.exists() or not root.is_dir():
            raise FileNotFoundError(f"Project path not found: {root}")
        file_paths: list[str] = []
        all_imports: list[str] = []
        all_classes: list[str] = []
        all_functions: list[str] = []
        all_decorators: list[str] = []
        dependencies: list[str] = []
        framework_hints: list[str] = []

        # Collect Python files
        for py_file in sorted(root.rglob("*.py")):
            rel = str(py_file.relative_to(root))
            if any(part.startswith(".") for part in py_file.parts):
                continue
            if "node_modules" in rel or "__pycache__" in rel:
                continue
            file_paths.append(rel)
            try:
                tree = ast.parse(py_file.read_text(encoding="utf-8", errors="replace"))
            except (SyntaxError, UnicodeDecodeError):
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        all_imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        all_imports.append(node.module)
                elif isinstance(node, ast.ClassDef):
                    all_classes.append(node.name)
                    for dec in node.decorator_list:
                        all_decorators.append(_decorator_name(dec))
                elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                    all_functions.append(node.name)
                    for dec in node.decorator_list:
                        all_decorators.append(_decorator_name(dec))

        # Collect non-Python file names
        for ext in ("*.yaml", "*.yml", "*.toml", "*.json", "*.cfg"):
            for f in sorted(root.rglob(ext)):
                rel = str(f.relative_to(root))
                if not any(part.startswith(".") for part in f.parts):
                    file_paths.append(rel)

        # Parse pyproject.toml for deps
        pyproject = root / "pyproject.toml"
        if pyproject.exists():
            try:
                text = pyproject.read_text(encoding="utf-8")
                dependencies = _extract_toml_deps(text)
            except Exception:
                pass

        # Detect frameworks from imports
        framework_map = {
            "langchain": "langchain",
            "crewai": "crewai",
            "autogen": "autogen",
            "openai": "openai",
            "anthropic": "anthropic",
            "fastapi": "fastapi",
            "flask": "flask",
            "django": "django",
        }
        unique_imports = set(all_imports)
        for imp in unique_imports:
            root_pkg = imp.split(".")[0].lower()
            if root_pkg in framework_map:
                framework_hints.append(framework_map[root_pkg])

        return CodebaseStructure(
            file_paths=tuple(sorted(set(file_paths))),
            imports=tuple(sorted(set(all_imports))),
            class_names=tuple(sorted(set(all_classes))),
            function_names=tuple(sorted(set(all_functions))),
            decorators=tuple(sorted(set(all_decorators))),
            dependencies=tuple(sorted(set(dependencies))),
            framework_hints=tuple(sorted(set(framework_hints))),
        )


def _decorator_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Call):
        return _decorator_name(node.func)
    return "unknown"


def _extract_toml_deps(text: str) -> list[str]:
    """Extract dependency names from pyproject.toml without a TOML parser."""
    deps: list[str] = []
    in_deps = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == "dependencies = [":
            in_deps = True
            continue
        if in_deps:
            if stripped == "]":
                break
            cleaned = stripped.strip(' ",')
            if cleaned:
                # Extract package name before version specifier
                for sep in (">=", "<=", "==", "!=", "<", ">", "~=", "["):
                    cleaned = cleaned.split(sep)[0]
                deps.append(cleaned.strip())
    return deps
