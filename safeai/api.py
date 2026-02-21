"""Public SafeAI API facade."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

from safeai.config.loader import (
    load_config,
    load_contract_bundle,
    load_identity_bundle,
    load_memory_bundle,
    load_policy_bundle,
)
from safeai.core.approval import ApprovalManager, ApprovalRequest
from safeai.core.audit import AuditEvent, AuditLogger
from safeai.core.classifier import Classifier
from safeai.core.contracts import (
    ContractValidationResult,
    ToolContractRegistry,
    normalize_contracts,
)
from safeai.core.guard import GuardResult, OutputGuard
from safeai.core.identity import (
    AgentIdentityRegistry,
    AgentIdentityValidationResult,
    normalize_agent_identities,
)
from safeai.core.interceptor import (
    ActionInterceptor,
    InterceptResult,
    ResponseInterceptResult,
    ToolCall,
)
from safeai.core.memory import MemoryController
from safeai.core.policy import PolicyContext, PolicyEngine, normalize_rules
from safeai.core.scanner import InputScanner, ScanResult
from safeai.core.structured import StructuredScanner, StructuredScanResult
from safeai.detectors import all_detectors
from safeai.plugins.manager import PluginManager
from safeai.secrets.base import (
    SecretAccessDeniedError,
    SecretBackend,
    SecretError,
    SecretNotFoundError,
)
from safeai.secrets.capability import CapabilityTokenManager, CapabilityValidationResult
from safeai.secrets.manager import ResolvedSecret, SecretManager
from safeai.templates import PolicyTemplateCatalog


class SafeAI:
    """Runtime orchestration for boundary components."""

    def __init__(
        self,
        policy_engine: PolicyEngine,
        classifier: Classifier,
        audit_logger: AuditLogger,
        memory_controller: MemoryController | None = None,
        contract_registry: ToolContractRegistry | None = None,
        identity_registry: AgentIdentityRegistry | None = None,
        capability_manager: CapabilityTokenManager | None = None,
        secret_manager: SecretManager | None = None,
        approval_manager: ApprovalManager | None = None,
        plugin_manager: PluginManager | None = None,
        memory_auto_purge_expired: bool = True,
    ) -> None:
        self.policy_engine = policy_engine
        self.classifier = classifier
        self.audit = audit_logger
        self.memory = memory_controller
        self.contracts = contract_registry or ToolContractRegistry()
        self.identities = identity_registry or AgentIdentityRegistry()
        self.capabilities = capability_manager or CapabilityTokenManager()
        self.secrets = secret_manager or SecretManager(capability_manager=self.capabilities)
        self.approvals = approval_manager or ApprovalManager()
        self.plugins = plugin_manager or PluginManager()
        self.templates = PolicyTemplateCatalog(plugin_manager=self.plugins)
        self.memory_auto_purge_expired = memory_auto_purge_expired
        self._ai_backends: Any = None  # Lazy: AIBackendRegistry
        self._input = InputScanner(classifier=classifier, policy_engine=policy_engine, audit_logger=audit_logger)
        self._structured = StructuredScanner(
            classifier=classifier,
            policy_engine=policy_engine,
            audit_logger=audit_logger,
        )
        self._output = OutputGuard(classifier=classifier, policy_engine=policy_engine, audit_logger=audit_logger)
        self._action = ActionInterceptor(
            policy_engine=policy_engine,
            audit_logger=audit_logger,
            contract_registry=self.contracts,
            identity_registry=self.identities,
            capability_manager=self.capabilities,
            approval_manager=self.approvals,
            classifier=classifier,
        )

    @classmethod
    def quickstart(
        cls,
        *,
        block_secrets: bool = True,
        redact_pii: bool = True,
        block_pii: bool = False,
        custom_rules: list[dict] | None = None,
        audit_path: str | None = None,
    ) -> "SafeAI":
        """Create a ready-to-use SafeAI instance with sensible defaults — no config files needed.

        Basic usage::

            from safeai import SafeAI
            ai = SafeAI.quickstart()

        Customise what gets enforced::

            # Block PII instead of redacting it
            ai = SafeAI.quickstart(block_pii=True, redact_pii=False)

            # Secrets only, ignore PII
            ai = SafeAI.quickstart(redact_pii=False)

            # Everything off except your own rules
            ai = SafeAI.quickstart(block_secrets=False, redact_pii=False, custom_rules=[
                {"name": "my-rule", "boundary": ["input"], "priority": 10,
                 "condition": {"data_tags": ["secret.credential"]},
                 "action": "block", "reason": "No creds allowed."},
            ])

        Args:
            block_secrets: Block API keys, tokens, and credentials (default True).
            redact_pii: Redact emails, phone numbers, SSNs in outputs (default True).
            block_pii: Block PII entirely instead of redacting (default False).
                       If both redact_pii and block_pii are True, block wins.
            custom_rules: Extra policy rules (list of dicts) added before the
                          default-allow rules. Same format as policy YAML.
            audit_path: File path for audit log. Defaults to a temp file.
        """
        rules: list[dict] = []

        if block_secrets:
            rules.append({
                "name": "block-secrets-everywhere",
                "boundary": ["input", "action", "output"],
                "priority": 10,
                "condition": {"data_tags": ["secret.credential", "secret.token", "secret"]},
                "action": "block",
                "reason": "Secrets must never cross any boundary.",
            })

        if block_pii:
            rules.append({
                "name": "block-personal-data",
                "boundary": ["input", "action", "output"],
                "priority": 20,
                "condition": {"data_tags": ["personal", "personal.pii", "personal.phi", "personal.financial"]},
                "action": "block",
                "reason": "Personal data must not cross any boundary.",
            })
        elif redact_pii:
            rules.append({
                "name": "redact-personal-data-in-output",
                "boundary": ["output"],
                "priority": 20,
                "condition": {"data_tags": ["personal", "personal.pii", "personal.phi", "personal.financial"]},
                "action": "redact",
                "reason": "Personal data must not appear in outbound responses.",
            })

        if custom_rules:
            rules.extend(custom_rules)

        # Default-allow fallbacks (always last)
        for boundary in ("input", "action", "output"):
            rules.append({
                "name": f"allow-{boundary}-by-default",
                "boundary": [boundary],
                "priority": 1000,
                "action": "allow",
                "reason": "Allow when no restrictive policy matched.",
            })

        policy_engine = PolicyEngine(normalize_rules(rules))
        classifier = Classifier(patterns=list(all_detectors()))
        _audit_path = audit_path or str(Path(tempfile.gettempdir()) / "safeai-audit.jsonl")
        audit = AuditLogger(_audit_path)
        return cls(
            policy_engine=policy_engine,
            classifier=classifier,
            audit_logger=audit,
        )

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
        _, contract_docs = load_contract_bundle(config_path, cfg.paths.contract_files, version=cfg.version)
        contracts = ToolContractRegistry(normalize_contracts(contract_docs)) if contract_docs else ToolContractRegistry()
        _, identity_docs = load_identity_bundle(config_path, cfg.paths.identity_files, version=cfg.version)
        identities = (
            AgentIdentityRegistry(normalize_agent_identities(identity_docs))
            if identity_docs
            else AgentIdentityRegistry()
        )
        plugin_manager = (
            PluginManager.from_patterns(config_path=config_path, patterns=cfg.plugins.plugin_files)
            if cfg.plugins.enabled
            else PluginManager()
        )
        classifier = Classifier(patterns=[*all_detectors(), *plugin_manager.detector_patterns()])
        audit = AuditLogger(cfg.audit.file_path)
        capabilities = CapabilityTokenManager()
        approvals = ApprovalManager(
            file_path=_resolve_optional_path(config_path, cfg.approvals.file_path),
            default_ttl=cfg.approvals.default_ttl,
        )
        return cls(
            policy_engine=policy_engine,
            classifier=classifier,
            audit_logger=audit,
            memory_controller=memory,
            contract_registry=contracts,
            identity_registry=identities,
            capability_manager=capabilities,
            secret_manager=SecretManager(capability_manager=capabilities),
            approval_manager=approvals,
            plugin_manager=plugin_manager,
            memory_auto_purge_expired=cfg.memory_runtime.auto_purge_expired,
        )

    def scan_input(self, data: str, agent_id: str = "unknown") -> ScanResult:
        return self._input.scan(data, agent_id=agent_id)

    def guard_output(self, data: str, agent_id: str = "unknown") -> GuardResult:
        return self._output.guard(data, agent_id=agent_id)

    def scan_structured_input(self, payload: Any, *, agent_id: str = "unknown") -> StructuredScanResult:
        return self._structured.scan(payload, agent_id=agent_id)

    def scan_file_input(self, file_path: str | Path, *, agent_id: str = "unknown") -> dict[str, Any]:
        resolved = Path(file_path).expanduser().resolve()
        if not resolved.exists() or not resolved.is_file():
            raise FileNotFoundError(f"file not found: {resolved}")
        raw = resolved.read_bytes()
        suffix = resolved.suffix.strip().lower()
        size_bytes = len(raw)

        if suffix == ".json":
            payload = json.loads(raw.decode("utf-8", errors="strict"))
            structured = self.scan_structured_input(payload, agent_id=agent_id)
            return {
                "mode": "structured",
                "file_path": str(resolved),
                "size_bytes": size_bytes,
                "decision": {
                    "action": structured.decision.action,
                    "policy_name": structured.decision.policy_name,
                    "reason": structured.decision.reason,
                },
                "detections": [
                    {
                        "path": item.path,
                        "detector": item.detector,
                        "tag": item.tag,
                        "start": item.start,
                        "end": item.end,
                    }
                    for item in structured.detections
                ],
                "filtered": structured.filtered,
            }

        text = raw.decode("utf-8", errors="replace")
        scan = self.scan_input(text, agent_id=agent_id)
        return {
            "mode": "text",
            "file_path": str(resolved),
            "size_bytes": size_bytes,
            "decision": {
                "action": scan.decision.action,
                "policy_name": scan.decision.policy_name,
                "reason": scan.decision.reason,
            },
            "detections": [
                {
                    "detector": item.detector,
                    "tag": item.tag,
                    "start": item.start,
                    "end": item.end,
                }
                for item in scan.detections
            ],
            "filtered": scan.filtered,
        }

    def reload_policies(self) -> bool:
        """Reload policies only when watched files changed."""
        return self.policy_engine.reload_if_changed()

    def force_reload_policies(self) -> bool:
        """Always reload policies from configured files."""
        return self.policy_engine.reload()

    def memory_write(self, key: str, value: Any, *, agent_id: str = "unknown") -> bool:
        if not self.memory:
            return False
        self._auto_purge_memory(trigger="memory_write", agent_id=agent_id)
        return self.memory.write(key=key, value=value, agent_id=agent_id)

    def memory_read(self, key: str, *, agent_id: str = "unknown") -> Any:
        if not self.memory:
            return None
        self._auto_purge_memory(trigger="memory_read", agent_id=agent_id)
        return self.memory.read(key=key, agent_id=agent_id)

    def memory_purge_expired(self) -> int:
        if not self.memory:
            return 0
        purged = self.memory.purge_expired()
        if purged:
            self._emit_memory_retention_event(
                agent_id="system",
                reason=f"Purged {purged} expired memory entr{'y' if purged == 1 else 'ies'}",
                metadata={"phase": "retention_purge", "trigger": "manual", "purged_count": purged},
            )
        return purged

    def resolve_memory_handle(
        self,
        handle_id: str,
        *,
        agent_id: str = "unknown",
        session_id: str | None = None,
        source_agent_id: str | None = None,
        destination_agent_id: str | None = None,
    ) -> Any:
        if not self.memory:
            return None
        metadata = self.memory.handle_metadata(handle_id)
        if metadata is None:
            self._emit_memory_retention_event(
                agent_id=agent_id,
                reason=f"Memory handle '{handle_id}' not found",
                metadata={
                    "phase": "handle_resolve",
                    "handle_id": handle_id,
                    "resolution": "missing",
                },
                action="block",
                policy_name="memory-handle",
                session_id=session_id,
                source_agent_id=source_agent_id,
                destination_agent_id=destination_agent_id,
            )
            return None

        decision = self.policy_engine.evaluate(
            PolicyContext(
                boundary="action",
                data_tags=[metadata["tag"]],
                agent_id=agent_id,
                tool_name="memory.resolve_handle",
            )
        )
        if decision.action in {"block", "redact", "require_approval"}:
            self._emit_memory_retention_event(
                agent_id=agent_id,
                reason=decision.reason,
                metadata={
                    "phase": "handle_resolve",
                    "handle_id": handle_id,
                    "resolution": "policy_blocked",
                    "handle_tag": metadata["tag"],
                },
                action=decision.action,
                policy_name=decision.policy_name,
                data_tags=[metadata["tag"]],
                session_id=session_id,
                source_agent_id=source_agent_id,
                destination_agent_id=destination_agent_id,
            )
            return None

        try:
            resolved = self.memory.resolve_handle(handle_id, agent_id=agent_id)
        except Exception as exc:
            self._emit_memory_retention_event(
                agent_id=agent_id,
                reason=str(exc),
                metadata={
                    "phase": "handle_resolve",
                    "handle_id": handle_id,
                    "resolution": "resolve_failed",
                    "handle_tag": metadata["tag"],
                },
                action="block",
                policy_name="memory-handle",
                data_tags=[metadata["tag"]],
                session_id=session_id,
                source_agent_id=source_agent_id,
                destination_agent_id=destination_agent_id,
            )
            return None

        self._emit_memory_retention_event(
            agent_id=agent_id,
            reason="Resolved encrypted memory handle",
            metadata={
                "phase": "handle_resolve",
                "handle_id": handle_id,
                "resolution": "allow",
                "handle_tag": metadata["tag"],
                "encrypted": True,
            },
            action="allow",
            policy_name=decision.policy_name or "memory-handle",
            data_tags=[metadata["tag"]],
            session_id=session_id,
            source_agent_id=source_agent_id,
            destination_agent_id=destination_agent_id,
        )
        return resolved

    def query_audit(self, **filters: Any) -> list[dict[str, Any]]:
        return self.audit.query(**filters)

    def validate_tool_request(self, tool_name: str, data_tags: list[str]) -> ContractValidationResult:
        return self.contracts.validate_request(tool_name=tool_name, data_tags=data_tags)

    def validate_agent_identity(
        self,
        agent_id: str,
        *,
        tool_name: str | None = None,
        data_tags: list[str] | None = None,
    ) -> AgentIdentityValidationResult:
        return self.identities.validate(agent_id=agent_id, tool_name=tool_name, data_tags=data_tags)

    def issue_capability_token(
        self,
        *,
        agent_id: str,
        tool_name: str,
        actions: list[str],
        ttl: str = "10m",
        secret_keys: list[str] | None = None,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        return self.capabilities.issue(
            agent_id=agent_id,
            tool_name=tool_name,
            actions=actions,
            ttl=ttl,
            secret_keys=secret_keys,
            session_id=session_id,
            metadata=metadata,
        )

    def validate_capability_token(
        self,
        token_id: str,
        *,
        agent_id: str,
        tool_name: str,
        action: str = "invoke",
        session_id: str | None = None,
    ) -> CapabilityValidationResult:
        return self.capabilities.validate(
            token_id,
            agent_id=agent_id,
            tool_name=tool_name,
            action=action,
            session_id=session_id,
        )

    def revoke_capability_token(self, token_id: str) -> bool:
        return self.capabilities.revoke(token_id)

    def purge_expired_capability_tokens(self) -> int:
        return self.capabilities.purge_expired()

    def list_approval_requests(
        self,
        *,
        status: str | None = None,
        agent_id: str | None = None,
        tool_name: str | None = None,
        newest_first: bool = True,
        limit: int = 100,
    ) -> list[ApprovalRequest]:
        typed_status = status if status in {"pending", "approved", "denied", "expired"} else None
        return self.approvals.list_requests(
            status=typed_status,  # type: ignore[arg-type]
            agent_id=agent_id,
            tool_name=tool_name,
            newest_first=newest_first,
            limit=limit,
        )

    def approve_request(self, request_id: str, *, approver_id: str, note: str | None = None) -> bool:
        return self.approvals.approve(request_id, approver_id=approver_id, note=note)

    def deny_request(self, request_id: str, *, approver_id: str, note: str | None = None) -> bool:
        return self.approvals.deny(request_id, approver_id=approver_id, note=note)

    def register_secret_backend(
        self,
        name: str,
        backend: SecretBackend,
        *,
        replace: bool = False,
    ) -> None:
        self.secrets.register_backend(name, backend, replace=replace)

    def list_secret_backends(self) -> list[str]:
        return self.secrets.list_backends()

    def resolve_secret(
        self,
        *,
        token_id: str,
        secret_key: str,
        agent_id: str,
        tool_name: str,
        action: str = "invoke",
        session_id: str | None = None,
        backend: str = "env",
    ) -> ResolvedSecret:
        try:
            resolved = self.secrets.resolve_secret(
                token_id=token_id,
                secret_key=secret_key,
                agent_id=agent_id,
                tool_name=tool_name,
                action=action,
                session_id=session_id,
                backend=backend,
            )
        except SecretError as exc:
            event_action = "block" if isinstance(exc, SecretAccessDeniedError) else "deny"
            self.audit.emit(
                AuditEvent(
                    boundary="action",
                    action=event_action,
                    policy_name="secret-manager",
                    reason=str(exc),
                    data_tags=["secret"],
                    agent_id=agent_id,
                    tool_name=tool_name,
                    session_id=session_id,
                    metadata={
                        "phase": "secret_resolve",
                        "secret_backend": backend,
                        "secret_key": secret_key,
                        "capability_token_id": token_id,
                        "result": "error",
                    },
                )
            )
            raise
        self.audit.emit(
            AuditEvent(
                boundary="action",
                action="allow",
                policy_name="secret-manager",
                reason="secret resolved by scoped capability",
                data_tags=["secret"],
                agent_id=agent_id,
                tool_name=tool_name,
                session_id=session_id,
                metadata={
                    "phase": "secret_resolve",
                    "secret_backend": backend,
                    "secret_key": secret_key,
                    "capability_token_id": token_id,
                    "result": "allow",
                },
            )
        )
        return resolved

    def resolve_secrets(
        self,
        *,
        token_id: str,
        secret_keys: list[str],
        agent_id: str,
        tool_name: str,
        action: str = "invoke",
        session_id: str | None = None,
        backend: str = "env",
    ) -> dict[str, ResolvedSecret]:
        rows: dict[str, ResolvedSecret] = {}
        missing: list[str] = []
        for key in secret_keys:
            try:
                rows[key] = self.resolve_secret(
                    token_id=token_id,
                    secret_key=key,
                    agent_id=agent_id,
                    tool_name=tool_name,
                    action=action,
                    session_id=session_id,
                    backend=backend,
                )
            except SecretNotFoundError:
                missing.append(key)
                continue
        if missing:
            raise SecretNotFoundError(
                f"Unable to resolve secret key(s) from backend '{backend}': {','.join(sorted(set(missing)))}"
            )
        return rows

    def intercept_tool_request(
        self,
        tool_name: str,
        parameters: dict[str, Any],
        data_tags: list[str],
        *,
        agent_id: str = "unknown",
        session_id: str | None = None,
        source_agent_id: str | None = None,
        destination_agent_id: str | None = None,
        action_type: str | None = None,
        capability_token_id: str | None = None,
        capability_action: str = "invoke",
        approval_request_id: str | None = None,
    ) -> InterceptResult:
        return self._action.intercept_request(
            ToolCall(
                tool_name=tool_name,
                agent_id=agent_id,
                parameters=dict(parameters),
                data_tags=list(data_tags),
                session_id=session_id,
                source_agent_id=source_agent_id,
                destination_agent_id=destination_agent_id,
                action_type=action_type,
                capability_token_id=capability_token_id,
                capability_action=capability_action,
                approval_request_id=approval_request_id,
            )
        )

    def intercept_tool_response(
        self,
        tool_name: str,
        response: dict[str, Any],
        *,
        agent_id: str = "unknown",
        request_data_tags: list[str] | None = None,
        session_id: str | None = None,
        source_agent_id: str | None = None,
        destination_agent_id: str | None = None,
        action_type: str | None = None,
    ) -> ResponseInterceptResult:
        return self._action.intercept_response(
            ToolCall(
                tool_name=tool_name,
                agent_id=agent_id,
                parameters={},
                data_tags=list(request_data_tags or []),
                session_id=session_id,
                source_agent_id=source_agent_id,
                destination_agent_id=destination_agent_id,
                action_type=action_type,
            ),
            dict(response),
        )

    def wrap(self, fn):
        """Minimal function wrapper placeholder for framework adapters."""

        def _wrapped(*args: Any, **kwargs: Any) -> Any:
            return fn(*args, **kwargs)

        return _wrapped

    def langchain_adapter(self):
        """Return a LangChain adapter bound to this SafeAI instance."""
        from safeai.middleware.langchain import SafeAILangChainAdapter

        return SafeAILangChainAdapter(self)

    def claude_adk_adapter(self):
        """Return a Claude ADK adapter bound to this SafeAI instance."""
        from safeai.middleware.claude_adk import SafeAIClaudeADKAdapter

        return SafeAIClaudeADKAdapter(self)

    def google_adk_adapter(self):
        """Return a Google ADK adapter bound to this SafeAI instance."""
        from safeai.middleware.google_adk import SafeAIGoogleADKAdapter

        return SafeAIGoogleADKAdapter(self)

    def crewai_adapter(self):
        """Return a CrewAI adapter bound to this SafeAI instance."""
        from safeai.middleware.crewai import SafeAICrewAIAdapter

        return SafeAICrewAIAdapter(self)

    def autogen_adapter(self):
        """Return an AutoGen adapter bound to this SafeAI instance."""
        from safeai.middleware.autogen import SafeAIAutoGenAdapter

        return SafeAIAutoGenAdapter(self)

    def list_plugins(self) -> list[dict[str, Any]]:
        return self.plugins.list_plugins()

    def list_plugin_adapters(self) -> list[str]:
        return self.plugins.adapter_names()

    def plugin_adapter(self, name: str) -> Any:
        return self.plugins.build_adapter(name, self)

    def list_policy_templates(self) -> list[dict[str, Any]]:
        return self.templates.list_templates()

    def load_policy_template(self, name: str) -> dict[str, Any]:
        return self.templates.load(name)

    def search_policy_templates(self, **kwargs: Any) -> list[dict[str, Any]]:
        return self.templates.search(**kwargs)

    def install_policy_template(self, name: str) -> str:
        return self.templates.install(name)

    # --- Intelligence layer (lazy imports) ---

    def _ensure_ai_registry(self) -> Any:
        if self._ai_backends is None:
            from safeai.intelligence.backend import AIBackendRegistry

            self._ai_backends = AIBackendRegistry()
        return self._ai_backends

    def register_ai_backend(self, name: str, backend: Any, *, default: bool = True) -> None:
        registry = self._ensure_ai_registry()
        registry.register(name, backend, default=default)

    def list_ai_backends(self) -> list[str]:
        return self._ensure_ai_registry().list_backends()

    def intelligence_auto_config(
        self, project_path: str = ".", framework_hint: str | None = None
    ) -> Any:
        from safeai.intelligence.auto_config import AutoConfigAdvisor
        from safeai.intelligence.sanitizer import MetadataSanitizer

        backend = self._ensure_ai_registry().get()
        advisor = AutoConfigAdvisor(backend=backend, sanitizer=MetadataSanitizer())
        return advisor.advise(project_path=project_path, framework_hint=framework_hint)

    def intelligence_recommend(self, since: str = "7d") -> Any:
        from safeai.intelligence.recommender import RecommenderAdvisor
        from safeai.intelligence.sanitizer import MetadataSanitizer

        backend = self._ensure_ai_registry().get()
        sanitizer = MetadataSanitizer()
        events = self.query_audit(last=since)
        advisor = RecommenderAdvisor(backend=backend, sanitizer=sanitizer)
        return advisor.advise(events=events)

    def intelligence_explain(self, event_id: str) -> Any:
        from safeai.intelligence.incident import IncidentAdvisor
        from safeai.intelligence.sanitizer import MetadataSanitizer

        backend = self._ensure_ai_registry().get()
        sanitizer = MetadataSanitizer()
        events = self.query_audit(event_id=event_id)
        target = events[0] if events else None
        if not target:
            from safeai.intelligence.advisor import AdvisorResult

            return AdvisorResult(
                advisor_name="incident",
                status="error",
                summary=f"Event '{event_id}' not found.",
            )
        # Get surrounding context
        context_events = self.query_audit(last="1h", limit=5)
        advisor = IncidentAdvisor(backend=backend, sanitizer=sanitizer)
        return advisor.advise(event=target, context_events=context_events)

    def intelligence_compliance(
        self, framework: str = "hipaa", config_path: str | None = None
    ) -> Any:
        from safeai.intelligence.compliance import ComplianceAdvisor
        from safeai.intelligence.sanitizer import MetadataSanitizer

        backend = self._ensure_ai_registry().get()
        advisor = ComplianceAdvisor(backend=backend, sanitizer=MetadataSanitizer())
        return advisor.advise(framework=framework, config_path=config_path)

    def intelligence_integrate(self, target: str = "langchain", project_path: str = ".") -> Any:
        from safeai.intelligence.integration import IntegrationAdvisor
        from safeai.intelligence.sanitizer import MetadataSanitizer

        backend = self._ensure_ai_registry().get()
        advisor = IntegrationAdvisor(backend=backend, sanitizer=MetadataSanitizer())
        return advisor.advise(target=target, project_path=project_path)

    def intercept_agent_message(
        self,
        *,
        message: str,
        source_agent_id: str,
        destination_agent_id: str,
        data_tags: list[str] | None = None,
        session_id: str | None = None,
        approval_request_id: str | None = None,
    ) -> dict[str, Any]:
        body = str(message)
        detected_tags = {item.tag for item in self.classifier.classify_text(body)}
        explicit_tags = {str(tag).strip().lower() for tag in (data_tags or []) if str(tag).strip()}
        tags = sorted(explicit_tags.union(detected_tags))
        decision = self.policy_engine.evaluate(
            PolicyContext(
                boundary="action",
                data_tags=tags,
                agent_id=source_agent_id,
                tool_name="agent_to_agent",
                action_type="agent_to_agent",
            )
        )
        approval_id: str | None = None
        if decision.action == "require_approval":
            if approval_request_id:
                validation = self.approvals.validate(
                    approval_request_id,
                    agent_id=source_agent_id,
                    tool_name="agent_to_agent",
                    session_id=session_id,
                )
                approval_id = approval_request_id
                if validation.allowed:
                    decision = decision.__class__(
                        action="allow",
                        policy_name=decision.policy_name or "approval-gate",
                        reason=f"approval request '{approval_request_id}' approved",
                    )
                elif validation.request and validation.request.status == "denied":
                    decision = decision.__class__(
                        action="block",
                        policy_name="approval-gate",
                        reason=validation.reason,
                    )
            else:
                created = self.approvals.create_request(
                    reason=decision.reason,
                    policy_name=decision.policy_name or "approval-gate",
                    agent_id=source_agent_id,
                    tool_name="agent_to_agent",
                    session_id=session_id,
                    action_type="agent_to_agent",
                    data_tags=tags,
                    metadata={"destination_agent_id": destination_agent_id},
                    dedupe_key="|".join(
                        [
                            source_agent_id,
                            destination_agent_id,
                            session_id or "-",
                            ",".join(tags),
                            str(hash(body)),
                        ]
                    ),
                )
                approval_id = created.request_id

        if decision.action == "allow":
            filtered_message = body
        elif decision.action == "redact":
            filtered_message = "[REDACTED]"
        else:
            filtered_message = ""

        self.audit.emit(
            AuditEvent(
                boundary="action",
                action=decision.action,
                policy_name=decision.policy_name,
                reason=decision.reason,
                data_tags=tags,
                agent_id=source_agent_id,
                session_id=session_id,
                source_agent_id=source_agent_id,
                destination_agent_id=destination_agent_id,
                metadata={
                    "phase": "agent_message",
                    "action_type": "agent_to_agent",
                    "message_length": len(body),
                    "filtered_length": len(filtered_message),
                    "approval_request_id": approval_id,
                    "destination_agent_id": destination_agent_id,
                },
            )
        )
        return {
            "decision": {
                "action": decision.action,
                "policy_name": decision.policy_name,
                "reason": decision.reason,
            },
            "data_tags": tags,
            "filtered_message": filtered_message,
            "approval_request_id": approval_id,
        }

    def _auto_purge_memory(self, *, trigger: str, agent_id: str) -> int:
        if not self.memory or not self.memory_auto_purge_expired:
            return 0
        purged = self.memory.purge_expired()
        if purged:
            self._emit_memory_retention_event(
                agent_id=agent_id,
                reason=f"Purged {purged} expired memory entr{'y' if purged == 1 else 'ies'}",
                metadata={"phase": "retention_purge", "trigger": trigger, "purged_count": purged},
            )
        return purged

    def _emit_memory_retention_event(
        self,
        *,
        agent_id: str,
        reason: str,
        metadata: dict[str, Any],
        action: str = "allow",
        policy_name: str | None = "memory-retention",
        data_tags: list[str] | None = None,
        session_id: str | None = None,
        source_agent_id: str | None = None,
        destination_agent_id: str | None = None,
    ) -> None:
        self.audit.emit(
            AuditEvent(
                boundary="memory",
                action=action,
                policy_name=policy_name,
                reason=reason,
                data_tags=list(data_tags or []),
                agent_id=agent_id,
                session_id=session_id,
                source_agent_id=source_agent_id,
                destination_agent_id=destination_agent_id,
                metadata=dict(metadata),
            )
        )


def _resolve_optional_path(config_path: Path, value: str | None) -> str | None:
    if value is None:
        return None
    raw = Path(value).expanduser()
    if raw.is_absolute():
        return str(raw.resolve())
    return str((config_path.parent / raw).resolve())
