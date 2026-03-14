# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 SafeAI Contributors
"""Advanced API namespace for SafeAI — progressive disclosure facade.

Exposes specialised methods (contracts, identities, capabilities, secrets,
interception, framework adapters, plugins, templates, and the AI intelligence
layer) through ``SafeAI.advanced`` so the main class surface stays small and
beginner-friendly.  Every method delegates to the *same* implementation on the
parent :class:`SafeAI` instance, so behaviour is identical.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from safeai.api import SafeAI
    from safeai.core.approval import ApprovalRequest
    from safeai.core.contracts import ContractValidationResult
    from safeai.core.identity import AgentIdentityValidationResult
    from safeai.core.interceptor import InterceptResult, ResponseInterceptResult
    from safeai.secrets.base import SecretBackend
    from safeai.secrets.capability import CapabilityValidationResult
    from safeai.secrets.manager import ResolvedSecret


class AdvancedAPI:
    """Namespace for advanced SafeAI operations.

    Accessed via the :pyattr:`SafeAI.advanced` property::

        ai = SafeAI.quickstart()
        result = ai.advanced.validate_tool_request("db.query", ["personal.pii"])

    All methods delegate to the parent :class:`SafeAI` instance, so
    ``ai.advanced.method(...)`` is equivalent to ``ai.method(...)``.
    """

    __slots__ = ("_parent",)

    def __init__(self, parent: SafeAI) -> None:
        self._parent = parent

    # ------------------------------------------------------------------
    # Contract & Identity Validation
    # ------------------------------------------------------------------

    def validate_tool_request(
        self, tool_name: str, data_tags: list[str]
    ) -> ContractValidationResult:
        return self._parent.contracts.validate_request(
            tool_name=tool_name, data_tags=data_tags
        )

    def validate_agent_identity(
        self,
        agent_id: str,
        *,
        tool_name: str | None = None,
        data_tags: list[str] | None = None,
    ) -> AgentIdentityValidationResult:
        return self._parent.identities.validate(
            agent_id=agent_id, tool_name=tool_name, data_tags=data_tags
        )

    # ------------------------------------------------------------------
    # Capability Token Management
    # ------------------------------------------------------------------

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
        return self._parent.capabilities.issue(
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
        return self._parent.capabilities.validate(
            token_id,
            agent_id=agent_id,
            tool_name=tool_name,
            action=action,
            session_id=session_id,
        )

    def revoke_capability_token(self, token_id: str) -> bool:
        return self._parent.capabilities.revoke(token_id)

    def purge_expired_capability_tokens(self) -> int:
        return self._parent.capabilities.purge_expired()

    # ------------------------------------------------------------------
    # Approval Management
    # ------------------------------------------------------------------

    def list_approval_requests(
        self,
        *,
        status: str | None = None,
        agent_id: str | None = None,
        tool_name: str | None = None,
        newest_first: bool = True,
        limit: int = 100,
    ) -> list[ApprovalRequest]:
        typed_status = (
            status if status in {"pending", "approved", "denied", "expired"} else None
        )
        return self._parent.approvals.list_requests(
            status=typed_status,  # type: ignore[arg-type]
            agent_id=agent_id,
            tool_name=tool_name,
            newest_first=newest_first,
            limit=limit,
        )

    def approve_request(
        self, request_id: str, *, approver_id: str, note: str | None = None
    ) -> bool:
        return self._parent.approvals.approve(
            request_id, approver_id=approver_id, note=note
        )

    def deny_request(
        self, request_id: str, *, approver_id: str, note: str | None = None
    ) -> bool:
        return self._parent.approvals.deny(
            request_id, approver_id=approver_id, note=note
        )

    # ------------------------------------------------------------------
    # Secret Management
    # ------------------------------------------------------------------

    def register_secret_backend(
        self, name: str, backend: SecretBackend, *, replace: bool = False
    ) -> None:
        self._parent.secrets.register_backend(name, backend, replace=replace)

    def list_secret_backends(self) -> list[str]:
        return self._parent.secrets.list_backends()

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
        # Delegate to the parent's resolve_secret which includes audit logging
        return self._parent.resolve_secret(
            token_id=token_id,
            secret_key=secret_key,
            agent_id=agent_id,
            tool_name=tool_name,
            action=action,
            session_id=session_id,
            backend=backend,
        )

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
        # Delegate to the parent's resolve_secrets which includes audit logging
        return self._parent.resolve_secrets(
            token_id=token_id,
            secret_keys=secret_keys,
            agent_id=agent_id,
            tool_name=tool_name,
            action=action,
            session_id=session_id,
            backend=backend,
        )

    # ------------------------------------------------------------------
    # Tool Interception
    # ------------------------------------------------------------------

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
        from safeai.core.interceptor import ToolCall

        return self._parent._action.intercept_request(
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
        from safeai.core.interceptor import ToolCall

        return self._parent._action.intercept_response(
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

    # ------------------------------------------------------------------
    # Framework Adapters
    # ------------------------------------------------------------------

    def wrap(self, fn):
        return self._parent.wrap(fn)

    def langchain_adapter(self):
        from safeai.middleware.langchain import SafeAILangChainAdapter

        return SafeAILangChainAdapter(self._parent)

    def claude_adk_adapter(self):
        from safeai.middleware.claude_adk import SafeAIClaudeADKAdapter

        return SafeAIClaudeADKAdapter(self._parent)

    def google_adk_adapter(self):
        from safeai.middleware.google_adk import SafeAIGoogleADKAdapter

        return SafeAIGoogleADKAdapter(self._parent)

    def crewai_adapter(self):
        from safeai.middleware.crewai import SafeAICrewAIAdapter

        return SafeAICrewAIAdapter(self._parent)

    def autogen_adapter(self):
        from safeai.middleware.autogen import SafeAIAutoGenAdapter

        return SafeAIAutoGenAdapter(self._parent)

    # ------------------------------------------------------------------
    # Plugin Management
    # ------------------------------------------------------------------

    def list_plugins(self) -> list[dict[str, Any]]:
        return self._parent.plugins.list_plugins()

    def list_plugin_adapters(self) -> list[str]:
        return self._parent.plugins.adapter_names()

    def plugin_adapter(self, name: str) -> Any:
        return self._parent.plugins.build_adapter(name, self._parent)

    # ------------------------------------------------------------------
    # Policy Templates
    # ------------------------------------------------------------------

    def list_policy_templates(self) -> list[dict[str, Any]]:
        return self._parent.templates.list_templates()

    def load_policy_template(self, name: str) -> dict[str, Any]:
        return self._parent.templates.load(name)

    def search_policy_templates(self, **kwargs: Any) -> list[dict[str, Any]]:
        return self._parent.templates.search(**kwargs)

    def install_policy_template(self, name: str) -> str:
        return self._parent.templates.install(name)

    # ------------------------------------------------------------------
    # AI Intelligence Layer
    # ------------------------------------------------------------------

    def register_ai_backend(
        self, name: str, backend: Any, *, default: bool = True
    ) -> None:
        registry = self._parent._ensure_ai_registry()
        registry.register(name, backend, default=default)

    def list_ai_backends(self) -> list[str]:
        return self._parent._ensure_ai_registry().list_backends()

    def intelligence_auto_config(
        self, project_path: str = ".", framework_hint: str | None = None
    ) -> Any:
        return self._parent.intelligence_auto_config(
            project_path=project_path, framework_hint=framework_hint
        )

    def intelligence_recommend(self, since: str = "7d") -> Any:
        return self._parent.intelligence_recommend(since=since)

    def intelligence_explain(self, event_id: str) -> Any:
        return self._parent.intelligence_explain(event_id=event_id)

    def intelligence_compliance(
        self, framework: str = "hipaa", config_path: str | None = None
    ) -> Any:
        return self._parent.intelligence_compliance(
            framework=framework, config_path=config_path
        )

    def intelligence_integrate(
        self, target: str = "langchain", project_path: str = "."
    ) -> Any:
        return self._parent.intelligence_integrate(
            target=target, project_path=project_path
        )

    # ------------------------------------------------------------------
    # Agent-to-Agent
    # ------------------------------------------------------------------

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
        return self._parent.intercept_agent_message(
            message=message,
            source_agent_id=source_agent_id,
            destination_agent_id=destination_agent_id,
            data_tags=data_tags,
            session_id=session_id,
            approval_request_id=approval_request_id,
        )
