# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 SafeAI Contributors
"""Public SafeAI API facade."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from safeai.advanced import AdvancedAPI

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
from safeai.core.scanner import FileScanResult, InputScanner, ScanResult
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
        """Initialize the SafeAI runtime orchestrator.

        SafeAI is the central facade that wires together all boundary-enforcement
        components (scanning, guarding, interception, policy evaluation, auditing,
        memory, contracts, identities, capabilities, secrets, approvals, and plugins).

        Args:
            policy_engine: Engine that evaluates policy rules against data-tag contexts.
            classifier: Detector-backed classifier used to tag data flowing through boundaries.
            audit_logger: Logger that persists audit events to a JSONL file.
            memory_controller: Optional schema-enforced agent memory store.
            contract_registry: Optional registry of tool-level data-tag contracts.
            identity_registry: Optional registry of agent identity declarations.
            capability_manager: Optional manager for scoped capability tokens.
            secret_manager: Optional secret resolution manager.
            approval_manager: Optional human-in-the-loop approval gate.
            plugin_manager: Optional plugin manager for third-party extensions.
            memory_auto_purge_expired: If True, automatically purge expired memory
                entries on every read/write operation.
        """
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

    @property
    def advanced(self) -> "AdvancedAPI":
        """Access advanced API methods (contracts, identities, capabilities, secrets, etc.)."""
        if not hasattr(self, "_advanced"):
            from safeai.advanced import AdvancedAPI

            self._advanced = AdvancedAPI(self)
        return self._advanced

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
        """Create a SafeAI instance from a YAML/JSON configuration file.

        Loads policy rules, memory schemas, tool contracts, agent identities,
        plugins, audit settings, and approval configuration from the paths
        declared in the config file.

        Args:
            path: Path to the SafeAI configuration file (YAML or JSON).

        Returns:
            A fully configured SafeAI instance.
        """
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
        audit = AuditLogger(_resolve_optional_path(config_path, cfg.audit.file_path))
        capabilities = CapabilityTokenManager()
        approvals = ApprovalManager(
            file_path=_resolve_optional_path(config_path, cfg.approvals.file_path),
            default_ttl=cfg.approvals.default_ttl,
        )
        instance = cls(
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

        # Auto-register secret backends from config
        if cfg.secrets.enabled:
            for backend_cfg in cfg.secrets.backends:
                try:
                    instance._register_secret_backend_from_config(backend_cfg)
                except Exception as exc:
                    import logging
                    logging.getLogger(__name__).warning(
                        "Failed to register secret backend '%s': %s", backend_cfg.name, exc
                    )

        return instance

    def scan_input(self, data: str, agent_id: str = "unknown") -> ScanResult:
        """Scan text data through the input boundary.

        Classifies the input, evaluates policy rules, and returns a decision
        (allow, block, or redact) along with any detections.

        Args:
            data: Raw text to scan.
            agent_id: Identifier of the agent submitting the input.

        Returns:
            ScanResult containing the policy decision, detections, and filtered text.
        """
        return self._input.scan(data, agent_id=agent_id)

    def guard_output(self, data: str, agent_id: str = "unknown") -> GuardResult:
        """Guard text data at the output boundary.

        Classifies the outbound text, evaluates policy rules, and returns a
        decision (allow, block, or redact) with any detections.

        Args:
            data: Outbound text to guard.
            agent_id: Identifier of the agent producing the output.

        Returns:
            GuardResult containing the policy decision, detections, and filtered text.
        """
        return self._output.guard(data, agent_id=agent_id)

    def scan_structured_input(self, payload: Any, *, agent_id: str = "unknown") -> StructuredScanResult:
        """Scan a structured payload (dict, list, or nested object) through the input boundary.

        Recursively walks the payload, classifies string values, evaluates
        policy rules, and returns detections with JSON-path locations.

        Args:
            payload: Structured data (typically a dict or list) to scan.
            agent_id: Identifier of the agent submitting the payload.

        Returns:
            StructuredScanResult with the policy decision, path-level detections,
            and a filtered copy of the payload.
        """
        return self._structured.scan(payload, agent_id=agent_id)

    def scan_file_input(self, file_path: str | Path, *, agent_id: str = "unknown") -> FileScanResult:
        """Scan a file through the input boundary.

        Supports JSON files (structured scan) and all other text files (text scan).

        Args:
            file_path: Path to the file to scan.
            agent_id: Agent requesting the scan.

        Returns:
            FileScanResult with mode, decision, detections, and filtered content.
            Supports dict-style access for backward compatibility.

        Raises:
            FileNotFoundError: If the file does not exist.
        """
        resolved = Path(file_path).expanduser().resolve()
        if not resolved.exists() or not resolved.is_file():
            raise FileNotFoundError(f"file not found: {resolved}")
        raw = resolved.read_bytes()
        suffix = resolved.suffix.strip().lower()
        size_bytes = len(raw)

        if suffix == ".json":
            payload = json.loads(raw.decode("utf-8", errors="strict"))
            structured = self.scan_structured_input(payload, agent_id=agent_id)
            return FileScanResult(
                mode="structured",
                file_path=str(resolved),
                size_bytes=size_bytes,
                decision={
                    "action": structured.decision.action,
                    "policy_name": structured.decision.policy_name,
                    "reason": structured.decision.reason,
                },
                detections=[
                    {
                        "path": item.path,
                        "detector": item.detector,
                        "tag": item.tag,
                        "start": item.start,
                        "end": item.end,
                    }
                    for item in structured.detections
                ],
                filtered=structured.filtered,
            )

        text = raw.decode("utf-8", errors="replace")
        scan = self.scan_input(text, agent_id=agent_id)
        return FileScanResult(
            mode="text",
            file_path=str(resolved),
            size_bytes=size_bytes,
            decision={
                "action": scan.decision.action,
                "policy_name": scan.decision.policy_name,
                "reason": scan.decision.reason,
            },
            detections=[
                {
                    "detector": item.detector,
                    "tag": item.tag,
                    "start": item.start,
                    "end": item.end,
                }
                for item in scan.detections
            ],
            filtered=scan.filtered,
        )

    def reload_policies(self) -> bool:
        """Reload policies only when watched files changed."""
        return self.policy_engine.reload_if_changed()

    def force_reload_policies(self) -> bool:
        """Always reload policies from configured files."""
        return self.policy_engine.reload()

    def memory_write(self, key: str, value: Any, *, agent_id: str = "unknown", strict: bool = False) -> bool:
        """Write a value to schema-enforced agent memory.

        Args:
            key: Field name defined in the memory schema.
            value: Value to store. Must match the field's declared type.
            agent_id: Agent performing the write.
            strict: If True, raise MemoryValidationError on failure instead of returning False.

        Returns:
            True if the write succeeded, False otherwise.
        """
        if not self.memory:
            return False
        self._auto_purge_memory(trigger="memory_write", agent_id=agent_id)
        result = self.memory.write(key=key, value=value, agent_id=agent_id, strict=strict)
        return bool(result)

    def memory_read(self, key: str, *, agent_id: str = "unknown") -> Any:
        """Read a value from agent memory.

        Args:
            key: Field name to read.
            agent_id: Agent performing the read.

        Returns:
            The stored value, or None if not found / expired / no memory configured.
        """
        if not self.memory:
            return None
        self._auto_purge_memory(trigger="memory_read", agent_id=agent_id)
        result = self.memory.read(key=key, agent_id=agent_id)
        return result.value if result.found else None

    def memory_purge_expired(self) -> int:
        """Manually purge all expired entries from agent memory.

        Emits an audit event when entries are purged.

        Returns:
            The number of memory entries that were purged.
        """
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
        """Resolve an encrypted memory handle, subject to policy gating.

        Looks up the handle metadata, evaluates action-boundary policy rules
        against the handle's data tag, and — if allowed — decrypts and returns
        the stored value.  Returns None when the handle is missing, policy
        blocks access, or decryption fails.

        Args:
            handle_id: Opaque identifier returned by a previous memory write.
            agent_id: Agent requesting the resolution.
            session_id: Optional session scope for audit context.
            source_agent_id: Optional originating agent for multi-agent flows.
            destination_agent_id: Optional target agent for multi-agent flows.

        Returns:
            The decrypted value, or None if resolution is denied or fails.
        """
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
        """Query the audit log with optional filters.

        Args:
            **filters: Keyword arguments forwarded to the audit logger's query
                method (e.g., ``event_id``, ``agent_id``, ``boundary``, ``last``,
                ``limit``).

        Returns:
            A list of audit event dictionaries matching the filters.
        """
        return self.audit.query(**filters)

    def validate_tool_request(self, tool_name: str, data_tags: list[str]) -> ContractValidationResult:
        """Validate a tool invocation against its registered data-tag contract.

        Args:
            tool_name: Name of the tool being invoked.
            data_tags: Data tags present in the request payload.

        Returns:
            ContractValidationResult indicating whether the contract allows the
            given data tags.
        """
        return self.contracts.validate_request(tool_name=tool_name, data_tags=data_tags)

    def validate_agent_identity(
        self,
        agent_id: str,
        *,
        tool_name: str | None = None,
        data_tags: list[str] | None = None,
    ) -> AgentIdentityValidationResult:
        """Validate an agent's declared identity and permissions.

        Checks that the agent is registered and, optionally, that it is
        permitted to invoke the specified tool or handle the given data tags.

        Args:
            agent_id: Identifier of the agent to validate.
            tool_name: Optional tool name to check against the agent's allowed tools.
            data_tags: Optional data tags to check against the agent's allowed tags.

        Returns:
            AgentIdentityValidationResult with a valid flag and reason.
        """
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
    ) -> Any:
        """Issue a scoped, time-limited capability token to an agent.

        Capability tokens grant an agent permission to perform specific actions
        on a specific tool, optionally scoped to a session and a set of secret
        keys.

        Args:
            agent_id: Agent the token is issued to.
            tool_name: Tool the token grants access to.
            actions: List of permitted actions (e.g., ``["invoke", "read"]``).
            ttl: Time-to-live string (e.g., ``"10m"``, ``"1h"``).
            secret_keys: Optional list of secret keys the token may resolve.
            session_id: Optional session scope for the token.
            metadata: Optional extra metadata stored with the token.

        Returns:
            The issued capability token object.

        Example::

            token = ai.issue_capability_token(
                agent_id="data-agent",
                tool_name="db_query",
                actions=["invoke"],
                ttl="5m",
                secret_keys=["DB_PASSWORD"],
            )
            result = ai.validate_capability_token(
                token.token_id,
                agent_id="data-agent",
                tool_name="db_query",
            )
        """
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
        """Validate a capability token for a specific agent, tool, and action.

        Args:
            token_id: Identifier of the capability token to validate.
            agent_id: Agent presenting the token.
            tool_name: Tool the agent wants to use.
            action: Action the agent wants to perform (default ``"invoke"``).
            session_id: Optional session scope to validate against.

        Returns:
            CapabilityValidationResult indicating whether the token is valid.
        """
        return self.capabilities.validate(
            token_id,
            agent_id=agent_id,
            tool_name=tool_name,
            action=action,
            session_id=session_id,
        )

    def revoke_capability_token(self, token_id: str) -> bool:
        """Revoke a previously issued capability token.

        Args:
            token_id: Identifier of the token to revoke.

        Returns:
            True if the token was found and revoked, False otherwise.
        """
        return self.capabilities.revoke(token_id)

    def purge_expired_capability_tokens(self) -> int:
        """Remove all expired capability tokens from the token store.

        Returns:
            The number of tokens that were purged.
        """
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
        """List human-in-the-loop approval requests.

        Args:
            status: Filter by status (``"pending"``, ``"approved"``, ``"denied"``,
                or ``"expired"``). None returns all statuses.
            agent_id: Filter by the requesting agent.
            tool_name: Filter by the tool the request targets.
            newest_first: If True, return newest requests first.
            limit: Maximum number of requests to return.

        Returns:
            A list of ApprovalRequest objects matching the filters.
        """
        typed_status = status if status in {"pending", "approved", "denied", "expired"} else None
        return self.approvals.list_requests(
            status=typed_status,  # type: ignore[arg-type]
            agent_id=agent_id,
            tool_name=tool_name,
            newest_first=newest_first,
            limit=limit,
        )

    def approve_request(self, request_id: str, *, approver_id: str, note: str | None = None) -> bool:
        """Approve a pending approval request.

        Args:
            request_id: Identifier of the approval request.
            approver_id: Identifier of the human or system approving the request.
            note: Optional free-text note attached to the approval.

        Returns:
            True if the request was successfully approved, False otherwise.
        """
        return self.approvals.approve(request_id, approver_id=approver_id, note=note)

    def deny_request(self, request_id: str, *, approver_id: str, note: str | None = None) -> bool:
        """Deny a pending approval request.

        Args:
            request_id: Identifier of the approval request.
            approver_id: Identifier of the human or system denying the request.
            note: Optional free-text note attached to the denial.

        Returns:
            True if the request was successfully denied, False otherwise.
        """
        return self.approvals.deny(request_id, approver_id=approver_id, note=note)

    def register_secret_backend(
        self,
        name: str,
        backend: SecretBackend,
        *,
        replace: bool = False,
    ) -> None:
        """Register a named secret backend for secret resolution.

        Args:
            name: Unique name for the backend (e.g., ``"vault"``, ``"env"``).
            backend: A SecretBackend implementation that can resolve secret keys.
            replace: If True, replace an existing backend with the same name.
        """
        self.secrets.register_backend(name, backend, replace=replace)

    def _register_secret_backend_from_config(self, cfg) -> None:
        """Register a secret backend from YAML config."""
        import os
        if cfg.type == "vault":
            from safeai.secrets.vault import VaultSecretBackend
            url = os.environ.get(cfg.url_env or "VAULT_ADDR", "")
            token = os.environ.get(cfg.token_env or "VAULT_TOKEN", "")
            self.register_secret_backend(cfg.name, VaultSecretBackend(url=url, token=token))
        elif cfg.type == "aws":
            from safeai.secrets.aws import AWSSecretBackend
            region = os.environ.get(cfg.region_env or "AWS_REGION", "us-east-1")
            self.register_secret_backend(cfg.name, AWSSecretBackend(region_name=region))
        elif cfg.type == "env":
            from safeai.secrets.env import EnvSecretBackend
            self.register_secret_backend(cfg.name, EnvSecretBackend())
        else:
            raise ValueError(
                f"Unknown secret backend type: '{cfg.type}'\n"
                f"Fix: Use one of: vault, aws, env"
            )

    def list_secret_backends(self) -> list[str]:
        """List the names of all registered secret backends.

        Returns:
            A list of backend name strings.
        """
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
        """Resolve a single secret key using a capability token, with full audit logging.

        Validates the capability token, retrieves the secret from the specified
        backend, and emits an audit event recording the outcome.

        Args:
            token_id: Capability token authorizing the secret access.
            secret_key: Key of the secret to resolve (e.g., ``"DB_PASSWORD"``).
            agent_id: Agent requesting the secret.
            tool_name: Tool the secret is being resolved for.
            action: Capability action to validate (default ``"invoke"``).
            session_id: Optional session scope for token validation.
            backend: Name of the secret backend to use (default ``"env"``).

        Returns:
            ResolvedSecret containing the secret value and metadata.

        Raises:
            SecretAccessDeniedError: If the capability token is invalid or
                does not authorize the requested secret.
            SecretNotFoundError: If the secret key does not exist in the backend.

        Example::

            token = ai.issue_capability_token(
                agent_id="worker",
                tool_name="api_call",
                actions=["invoke"],
                secret_keys=["API_KEY"],
            )
            secret = ai.resolve_secret(
                token_id=token.token_id,
                secret_key="API_KEY",
                agent_id="worker",
                tool_name="api_call",
            )
        """
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
        """Resolve multiple secret keys in a single call.

        Iterates over the requested keys, resolving each via ``resolve_secret``.
        If any key is not found, raises SecretNotFoundError after attempting all.

        Args:
            token_id: Capability token authorizing the secret access.
            secret_keys: List of secret keys to resolve.
            agent_id: Agent requesting the secrets.
            tool_name: Tool the secrets are being resolved for.
            action: Capability action to validate (default ``"invoke"``).
            session_id: Optional session scope for token validation.
            backend: Name of the secret backend to use (default ``"env"``).

        Returns:
            A dict mapping each secret key to its ResolvedSecret.

        Raises:
            SecretNotFoundError: If one or more keys could not be found.
        """
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
        """Intercept a tool invocation at the action boundary.

        Runs the full interception pipeline: policy evaluation, contract
        validation, identity checks, capability-token verification, and
        approval gating.  Returns a decision (allow, block, redact, or
        require_approval) with audit logging.

        Args:
            tool_name: Name of the tool being invoked.
            parameters: Parameters the agent is passing to the tool.
            data_tags: Data tags present in the request payload.
            agent_id: Identifier of the invoking agent.
            session_id: Optional session scope for the request.
            source_agent_id: Optional originating agent in multi-agent flows.
            destination_agent_id: Optional target agent in multi-agent flows.
            action_type: Optional label for the kind of action (e.g., ``"tool_call"``).
            capability_token_id: Optional capability token authorizing the call.
            capability_action: Action to validate on the token (default ``"invoke"``).
            approval_request_id: Optional pre-existing approval request to validate.

        Returns:
            InterceptResult with the decision, detections, and filtered parameters.

        Example::

            result = ai.intercept_tool_request(
                tool_name="send_email",
                parameters={"to": "user@example.com", "body": "Hello"},
                data_tags=["personal.pii"],
                agent_id="assistant",
            )
            if result.decision.action == "allow":
                send_email(**result.filtered_parameters)
        """
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
        """Intercept a tool's response at the action boundary.

        Classifies the response payload, evaluates policy rules, and returns
        a decision with optional redaction of sensitive fields.

        Args:
            tool_name: Name of the tool that produced the response.
            response: The tool's response payload as a dict.
            agent_id: Identifier of the agent receiving the response.
            request_data_tags: Data tags from the original request, for context.
            session_id: Optional session scope.
            source_agent_id: Optional originating agent in multi-agent flows.
            destination_agent_id: Optional target agent in multi-agent flows.
            action_type: Optional label for the kind of action.

        Returns:
            ResponseInterceptResult with the decision and filtered response.
        """
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

    def wrap(self, fn: Any) -> Any:
        """Wrap a function for use with framework adapters.

        Args:
            fn: The callable to wrap.

        Returns:
            A wrapped callable that delegates to the original function.
        """

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
        """List all loaded plugins and their metadata.

        Returns:
            A list of dicts, each describing a loaded plugin.
        """
        return self.plugins.list_plugins()

    def list_plugin_adapters(self) -> list[str]:
        """List the names of all adapter classes provided by loaded plugins.

        Returns:
            A list of adapter name strings.
        """
        return self.plugins.adapter_names()

    def plugin_adapter(self, name: str) -> Any:
        """Build and return a plugin adapter instance by name.

        Args:
            name: Name of the adapter to instantiate.

        Returns:
            An adapter instance bound to this SafeAI runtime.
        """
        return self.plugins.build_adapter(name, self)

    def list_policy_templates(self) -> list[dict[str, Any]]:
        """List all available policy templates from the built-in catalog and plugins.

        Returns:
            A list of dicts, each describing a policy template with its name,
            description, and tags.
        """
        return self.templates.list_templates()

    def load_policy_template(self, name: str) -> dict[str, Any]:
        """Load the full content of a policy template by name.

        Args:
            name: Name of the template to load.

        Returns:
            A dict containing the template's rules, metadata, and description.
        """
        return self.templates.load(name)

    def search_policy_templates(self, **kwargs: Any) -> list[dict[str, Any]]:
        """Search policy templates by tags, keywords, or other criteria.

        Args:
            **kwargs: Search filters forwarded to the template catalog's search
                method (e.g., ``tags``, ``keyword``).

        Returns:
            A list of matching template metadata dicts.
        """
        return self.templates.search(**kwargs)

    def install_policy_template(self, name: str) -> str:
        """Install a policy template into the current project.

        Writes the template's policy YAML file into the project's policy
        directory so it is loaded on next initialization.

        Args:
            name: Name of the template to install.

        Returns:
            The file path where the template was written.
        """
        return self.templates.install(name)

    # --- Intelligence layer (lazy imports) ---

    def _ensure_ai_registry(self) -> Any:
        if self._ai_backends is None:
            from safeai.intelligence.backend import AIBackendRegistry

            self._ai_backends = AIBackendRegistry()
        return self._ai_backends

    def register_ai_backend(self, name: str, backend: Any, *, default: bool = True) -> None:
        """Register an AI backend for the intelligence layer.

        Args:
            name: Unique name for the backend (e.g., ``"openai"``, ``"anthropic"``).
            backend: An AI backend instance implementing the backend protocol.
            default: If True, set this backend as the default for intelligence calls.
        """
        registry = self._ensure_ai_registry()
        registry.register(name, backend, default=default)

    def list_ai_backends(self) -> list[str]:
        """List the names of all registered AI backends.

        Returns:
            A list of backend name strings.
        """
        return self._ensure_ai_registry().list_backends()

    def intelligence_auto_config(
        self, project_path: str = ".", framework_hint: str | None = None
    ) -> Any:
        """Auto-generate SafeAI configuration for a project using AI analysis.

        Scans the project structure and, optionally, uses a framework hint to
        produce recommended policy rules, contracts, and identity declarations.

        Args:
            project_path: Path to the project directory to analyze.
            framework_hint: Optional framework name (e.g., ``"langchain"``) to
                tailor the recommendations.

        Returns:
            An AdvisorResult containing the generated configuration advice.
        """
        from safeai.intelligence.auto_config import AutoConfigAdvisor
        from safeai.intelligence.sanitizer import MetadataSanitizer

        backend = self._ensure_ai_registry().get()
        advisor = AutoConfigAdvisor(backend=backend, sanitizer=MetadataSanitizer())
        return advisor.advise(project_path=project_path, framework_hint=framework_hint)

    def intelligence_recommend(self, since: str = "7d") -> Any:
        """Generate policy recommendations based on recent audit events.

        Analyzes audit history from the specified time window and uses the AI
        backend to suggest policy improvements.

        Args:
            since: Time window for audit events (e.g., ``"7d"``, ``"24h"``).

        Returns:
            An AdvisorResult containing recommended policy changes.
        """
        from safeai.intelligence.recommender import RecommenderAdvisor
        from safeai.intelligence.sanitizer import MetadataSanitizer

        backend = self._ensure_ai_registry().get()
        sanitizer = MetadataSanitizer()
        events = self.query_audit(last=since)
        advisor = RecommenderAdvisor(backend=backend, sanitizer=sanitizer)
        return advisor.advise(events=events)

    def intelligence_explain(self, event_id: str) -> Any:
        """Explain a specific audit event using AI-powered incident analysis.

        Retrieves the event and surrounding context, then asks the AI backend
        to produce a human-readable explanation of what happened and why.

        Args:
            event_id: Identifier of the audit event to explain.

        Returns:
            An AdvisorResult with the incident explanation, or an error result
            if the event is not found.
        """
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
        """Check current SafeAI configuration against a compliance framework.

        Uses the AI backend to evaluate whether the loaded policies satisfy
        the requirements of the specified compliance framework.

        Args:
            framework: Compliance framework to check (e.g., ``"hipaa"``, ``"gdpr"``).
            config_path: Optional path to a SafeAI config file to analyze.

        Returns:
            An AdvisorResult with compliance findings and gaps.
        """
        from safeai.intelligence.compliance import ComplianceAdvisor
        from safeai.intelligence.sanitizer import MetadataSanitizer

        backend = self._ensure_ai_registry().get()
        advisor = ComplianceAdvisor(backend=backend, sanitizer=MetadataSanitizer())
        return advisor.advise(framework=framework, config_path=config_path)

    def intelligence_integrate(self, target: str = "langchain", project_path: str = ".") -> Any:
        """Get AI-powered advice for integrating SafeAI with a target framework.

        Analyzes the project and produces step-by-step integration guidance
        tailored to the specified framework.

        Args:
            target: Framework to integrate with (e.g., ``"langchain"``, ``"crewai"``).
            project_path: Path to the project directory.

        Returns:
            An AdvisorResult with integration instructions and code snippets.
        """
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
        """Intercept an agent-to-agent message at the action boundary.

        Classifies the message body, merges detected tags with any explicitly
        provided tags, evaluates policy rules, handles approval gating, and
        emits an audit event.  The message may be allowed, redacted, or blocked.

        Args:
            message: The text message being sent between agents.
            source_agent_id: Identifier of the sending agent.
            destination_agent_id: Identifier of the receiving agent.
            data_tags: Optional explicit data tags to include alongside
                auto-detected tags.
            session_id: Optional session scope for policy and approval context.
            approval_request_id: Optional pre-existing approval request ID to
                validate instead of creating a new one.

        Returns:
            A dict with keys ``"decision"`` (action, policy_name, reason),
            ``"data_tags"``, ``"filtered_message"``, and ``"approval_request_id"``.

        Example::

            result = ai.intercept_agent_message(
                message="Patient SSN is 123-45-6789",
                source_agent_id="triage-agent",
                destination_agent_id="billing-agent",
            )
            if result["decision"]["action"] == "allow":
                send_to_agent(result["filtered_message"])
        """
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
