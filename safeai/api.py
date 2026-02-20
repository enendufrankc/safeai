"""Public SafeAI API facade."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from safeai.config.loader import load_config, load_memory_bundle, load_policy_bundle
from safeai.core.audit import AuditLogger
from safeai.core.classifier import Classifier
from safeai.core.guard import GuardResult, OutputGuard
from safeai.core.memory import MemoryController
from safeai.core.policy import PolicyEngine, normalize_rules
from safeai.core.scanner import InputScanner, ScanResult


class SafeAI:
    """Runtime orchestration for boundary components."""

    def __init__(
        self,
        policy_engine: PolicyEngine,
        classifier: Classifier,
        audit_logger: AuditLogger,
        memory_controller: MemoryController | None = None,
    ) -> None:
        self.policy_engine = policy_engine
        self.classifier = classifier
        self.audit = audit_logger
        self.memory = memory_controller
        self._input = InputScanner(classifier=classifier, policy_engine=policy_engine, audit_logger=audit_logger)
        self._output = OutputGuard(classifier=classifier, policy_engine=policy_engine, audit_logger=audit_logger)

    @classmethod
    def from_config(cls, path: str | Path) -> "SafeAI":
        cfg = load_config(path)
        config_path = Path(path).expanduser().resolve()
        policy_files, raw_rules = load_policy_bundle(config_path, cfg.paths.policy_files, version=cfg.version)
        policy_engine = PolicyEngine(normalize_rules(raw_rules))

        def _reload_rules():
            _, fresh_rules = load_policy_bundle(config_path, cfg.paths.policy_files, version=cfg.version)
            return normalize_rules(fresh_rules)

        policy_engine.register_reload(policy_files, _reload_rules)
        _, memory_docs = load_memory_bundle(config_path, cfg.paths.memory_schema_files, version=cfg.version)
        memory = MemoryController.from_documents(memory_docs) if memory_docs else None
        classifier = Classifier()
        audit = AuditLogger(cfg.audit.file_path)
        return cls(
            policy_engine=policy_engine,
            classifier=classifier,
            audit_logger=audit,
            memory_controller=memory,
        )

    def scan_input(self, data: str, agent_id: str = "unknown") -> ScanResult:
        return self._input.scan(data, agent_id=agent_id)

    def guard_output(self, data: str, agent_id: str = "unknown") -> GuardResult:
        return self._output.guard(data, agent_id=agent_id)

    def reload_policies(self) -> bool:
        """Reload policies only when watched files changed."""
        return self.policy_engine.reload_if_changed()

    def force_reload_policies(self) -> bool:
        """Always reload policies from configured files."""
        return self.policy_engine.reload()

    def memory_write(self, key: str, value: Any, *, agent_id: str = "unknown") -> bool:
        if not self.memory:
            return False
        return self.memory.write(key=key, value=value, agent_id=agent_id)

    def memory_read(self, key: str, *, agent_id: str = "unknown") -> Any:
        if not self.memory:
            return None
        return self.memory.read(key=key, agent_id=agent_id)

    def memory_purge_expired(self) -> int:
        if not self.memory:
            return 0
        return self.memory.purge_expired()

    def query_audit(self, **filters: Any) -> list[dict[str, Any]]:
        return self.audit.query(**filters)

    def wrap(self, fn):
        """Minimal function wrapper placeholder for framework adapters."""

        def _wrapped(*args: Any, **kwargs: Any) -> Any:
            return fn(*args, **kwargs)

        return _wrapped
