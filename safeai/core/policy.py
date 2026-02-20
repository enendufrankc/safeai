"""Policy model and first-match evaluator."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import Any, Callable, Iterable

from safeai.core.models import PolicyDecisionModel, PolicyRuleModel

DecisionAction = str
PolicyRuleLoader = Callable[[], list["PolicyRule"]]


@dataclass(frozen=True)
class PolicyContext:
    boundary: str
    data_tags: list[str]
    agent_id: str = "unknown"
    tool_name: str | None = None
    action_type: str | None = None


@dataclass(frozen=True)
class PolicyDecision:
    action: DecisionAction
    policy_name: str | None
    reason: str
    fallback_template: str | None = None


@dataclass(frozen=True)
class PolicyRule:
    name: str
    boundary: list[str]
    action: DecisionAction
    reason: str
    condition: dict[str, Any]
    priority: int = 100
    fallback_template: str | None = None


class PolicyEngine:
    """Deterministic first-match policy evaluator with default deny."""

    def __init__(self, rules: list[PolicyRule] | None = None) -> None:
        self._lock = RLock()
        self._rules: list[PolicyRule] = sorted(rules or [], key=lambda item: item.priority)
        self._reload_callback: PolicyRuleLoader | None = None
        self._watched_files: tuple[Path, ...] = ()
        self._file_mtimes: dict[Path, int] = {}

    def load(self, rules: list[PolicyRule]) -> None:
        with self._lock:
            self._rules = sorted(rules, key=lambda item: item.priority)

    def evaluate(self, context: PolicyContext) -> PolicyDecision:
        with self._lock:
            rules = tuple(self._rules)

        for rule in rules:
            if self._matches(rule, context):
                validated = PolicyDecisionModel(
                    action=rule.action,
                    policy_name=rule.name,
                    reason=rule.reason,
                    fallback_template=rule.fallback_template,
                )
                return PolicyDecision(**validated.model_dump())
        validated = PolicyDecisionModel(
            action="block",
            policy_name=None,
            reason="default deny",
            fallback_template=None,
        )
        return PolicyDecision(**validated.model_dump())

    def register_reload(self, files: list[Path], loader: PolicyRuleLoader) -> None:
        watched = tuple(sorted({Path(path).expanduser().resolve() for path in files}, key=str))
        with self._lock:
            self._reload_callback = loader
            self._watched_files = watched
            self._file_mtimes = self._snapshot_mtimes(watched)

    def reload_if_changed(self) -> bool:
        with self._lock:
            watched = self._watched_files
            previous = dict(self._file_mtimes)
            callback = self._reload_callback

        if callback is None or not watched:
            return False

        current = self._snapshot_mtimes(watched)
        if current == previous:
            return False

        self.reload()
        return True

    def reload(self) -> bool:
        with self._lock:
            callback = self._reload_callback
            watched = self._watched_files

        if callback is None:
            return False

        fresh_rules = sorted(callback(), key=lambda item: item.priority)
        fresh_mtimes = self._snapshot_mtimes(watched)
        with self._lock:
            self._rules = fresh_rules
            self._file_mtimes = fresh_mtimes
        return True

    def _matches(self, rule: PolicyRule, context: PolicyContext) -> bool:
        if context.boundary not in rule.boundary:
            return False

        cond = rule.condition or {}

        data_tags = _coerce_values(cond.get("data_tags"), lower=True)
        context_tags = expand_tag_hierarchy(context.data_tags)
        if data_tags and not data_tags.intersection(context_tags):
            return False

        tools = _coerce_values(cond.get("tools"))
        tool = cond.get("tool")
        if tool:
            tools.update(_coerce_values(tool))
        if tools and context.tool_name not in tools:
            return False

        agents = _coerce_values(cond.get("agents"))
        agent = cond.get("agent")
        if agent:
            agents.update(_coerce_values(agent))
        if agents and context.agent_id not in agents:
            return False

        return True

    @staticmethod
    def _snapshot_mtimes(files: tuple[Path, ...]) -> dict[Path, int]:
        mtimes: dict[Path, int] = {}
        for file_path in files:
            try:
                mtimes[file_path] = file_path.stat().st_mtime_ns
            except OSError:
                mtimes[file_path] = -1
        return mtimes


def normalize_rules(raw_items: list[dict[str, Any]]) -> list[PolicyRule]:
    """Convert raw policy dictionaries into ordered rule objects."""
    rules: list[PolicyRule] = []
    for item in raw_items:
        validated = PolicyRuleModel.model_validate(item)
        rules.append(
            PolicyRule(
                name=validated.name,
                boundary=list(validated.boundary),
                action=validated.action,
                reason=validated.reason,
                condition=dict(validated.condition),
                priority=validated.priority,
                fallback_template=_normalize_optional_text(validated.fallback_template),
            )
        )
    return sorted(rules, key=lambda item: item.priority)


def expand_tag_hierarchy(tags: Iterable[str]) -> set[str]:
    """Expand dotted tags into their parent hierarchy.

    Example: ``personal.pii`` -> {``personal``, ``personal.pii``}
    """
    expanded: set[str] = set()
    for raw_tag in tags:
        tag = _normalize_value(raw_tag, lower=True)
        if not tag:
            continue
        parts = [part for part in tag.split(".") if part]
        for idx in range(1, len(parts) + 1):
            expanded.add(".".join(parts[:idx]))
    return expanded


def _coerce_values(value: Any, *, lower: bool = False) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, str):
        candidates = [value]
    elif isinstance(value, (list, tuple, set, frozenset)):
        candidates = [str(item) for item in value]
    else:
        candidates = [str(value)]

    normalized: set[str] = set()
    for item in candidates:
        token = _normalize_value(item, lower=lower)
        if token:
            normalized.add(token)
    return normalized


def _normalize_value(value: str, *, lower: bool = False) -> str:
    token = str(value).strip()
    return token.lower() if lower else token


def _normalize_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    token = str(value).strip()
    return token or None
