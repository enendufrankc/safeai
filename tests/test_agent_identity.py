"""Agent identity enforcement tests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from safeai import SafeAI
from safeai.config.loader import IdentitySchemaValidationError, load_identity_documents
from safeai.core.audit import AuditLogger
from safeai.core.contracts import ToolContractRegistry, normalize_contracts
from safeai.core.identity import AgentIdentityRegistry, normalize_agent_identities
from safeai.core.interceptor import ActionInterceptor, ToolCall
from safeai.core.policy import PolicyEngine, normalize_rules


def _identity_registry() -> AgentIdentityRegistry:
    return AgentIdentityRegistry(
        normalize_agent_identities(
            [
                {
                    "version": "v1alpha1",
                    "agent": {
                        "agent_id": "ops-bot",
                        "tools": ["send_email", "profile_lookup"],
                        "clearance_tags": ["internal", "personal"],
                    },
                }
            ]
        )
    )


def _contract_registry() -> ToolContractRegistry:
    return ToolContractRegistry(
        normalize_contracts(
            [
                {
                    "version": "v1alpha1",
                    "contract": {
                        "tool_name": "send_email",
                        "accepts": {"tags": ["internal", "personal"]},
                        "emits": {"tags": ["internal", "personal"]},
                        "side_effects": {"reversible": False, "requires_approval": True},
                    },
                }
            ]
        )
    )


class AgentIdentityTests(unittest.TestCase):
    def test_registry_blocks_undeclared_agent(self) -> None:
        registry = _identity_registry()
        result = registry.validate(agent_id="unknown", tool_name="send_email", data_tags=["internal"])
        self.assertFalse(result.allowed)
        self.assertIn("is not declared", result.reason)

    def test_registry_blocks_unbound_tool(self) -> None:
        registry = _identity_registry()
        result = registry.validate(agent_id="ops-bot", tool_name="billing_export", data_tags=["internal"])
        self.assertFalse(result.allowed)
        self.assertIn("not bound to tool", result.reason)

    def test_registry_blocks_tags_above_clearance(self) -> None:
        registry = AgentIdentityRegistry(
            normalize_agent_identities(
                [
                    {
                        "version": "v1alpha1",
                        "agent": {
                            "agent_id": "support-bot",
                            "clearance_tags": ["internal"],
                        },
                    }
                ]
            )
        )
        result = registry.validate(
            agent_id="support-bot",
            tool_name="send_email",
            data_tags=["personal.pii", "internal"],
        )
        self.assertFalse(result.allowed)
        self.assertEqual(result.unauthorized_tags, ["personal.pii"])

    def test_action_interceptor_blocks_unbound_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            interceptor = ActionInterceptor(
                policy_engine=PolicyEngine(
                    normalize_rules(
                        [
                            {
                                "name": "allow-action-default",
                                "boundary": ["action"],
                                "action": "allow",
                                "reason": "allow",
                                "priority": 1000,
                            }
                        ]
                    )
                ),
                audit_logger=AuditLogger(str(Path(tmp_dir) / "audit.log")),
                contract_registry=_contract_registry(),
                identity_registry=_identity_registry(),
            )
            result = interceptor.intercept_request(
                ToolCall(
                    tool_name="send_email",
                    agent_id="unregistered-agent",
                    parameters={"to": "ops@example.com"},
                    data_tags=["internal"],
                )
            )
            self.assertEqual(result.decision.action, "block")
            self.assertEqual(result.decision.policy_name, "agent-identity")
            self.assertEqual(result.filtered_params, {})

    def test_identity_schema_validation_rejects_invalid_document(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / "agents").mkdir(parents=True, exist_ok=True)
            (root / "agents" / "broken.yaml").write_text(
                "\n".join(
                    [
                        "version: v1alpha1",
                        "agent:",
                        "  description: missing agent id",
                    ]
                ),
                encoding="utf-8",
            )
            with self.assertRaises(IdentitySchemaValidationError):
                load_identity_documents(root / "safeai.yaml", ["agents/*.yaml"], version="v1alpha1")

    def test_safeai_loads_identity_registry_from_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / "safeai.yaml").write_text(
                "\n".join(
                    [
                        "version: v1alpha1",
                        "paths:",
                        "  policy_files:",
                        "    - policies/default.yaml",
                        "  contract_files:",
                        "    - contracts/*.yaml",
                        "  memory_schema_files:",
                        "    - schemas/memory.yaml",
                        "  identity_files:",
                        "    - agents/*.yaml",
                        "audit:",
                        "  file_path: logs/audit.log",
                    ]
                ),
                encoding="utf-8",
            )
            (root / "policies").mkdir(parents=True, exist_ok=True)
            (root / "contracts").mkdir(parents=True, exist_ok=True)
            (root / "schemas").mkdir(parents=True, exist_ok=True)
            (root / "agents").mkdir(parents=True, exist_ok=True)

            (root / "policies" / "default.yaml").write_text(
                "\n".join(
                    [
                        "version: v1alpha1",
                        "policy:",
                        "  name: allow-action",
                        "  boundary: action",
                        "  action: allow",
                        "  reason: allow",
                    ]
                ),
                encoding="utf-8",
            )
            (root / "contracts" / "send_email.yaml").write_text(
                "\n".join(
                    [
                        "version: v1alpha1",
                        "contract:",
                        "  tool_name: send_email",
                        "  accepts:",
                        "    tags: [internal, personal]",
                        "  emits:",
                        "    tags: [internal, personal]",
                        "  side_effects:",
                        "    reversible: false",
                        "    requires_approval: true",
                    ]
                ),
                encoding="utf-8",
            )
            (root / "schemas" / "memory.yaml").write_text(
                "\n".join(
                    [
                        "version: v1alpha1",
                        "memory:",
                        "  name: m",
                        "  scope: session",
                        "  default_retention: 24h",
                        "  fields:",
                        "    - name: user_preference",
                        "      type: string",
                        "      tag: internal",
                    ]
                ),
                encoding="utf-8",
            )
            (root / "agents" / "default.yaml").write_text(
                "\n".join(
                    [
                        "version: v1alpha1",
                        "agent:",
                        "  agent_id: ops-bot",
                        "  tools: [send_email]",
                        "  clearance_tags: [internal, personal]",
                    ]
                ),
                encoding="utf-8",
            )

            sdk = SafeAI.from_config(root / "safeai.yaml")
            allowed = sdk.validate_agent_identity(
                "ops-bot",
                tool_name="send_email",
                data_tags=["personal.pii"],
            )
            self.assertTrue(allowed.allowed)

            blocked = sdk.validate_agent_identity(
                "ops-bot",
                tool_name="billing_export",
                data_tags=["internal"],
            )
            self.assertFalse(blocked.allowed)
            self.assertIn("not bound to tool", blocked.reason)

            req_blocked = sdk.intercept_tool_request(
                "send_email",
                {"to": "a@example.com"},
                data_tags=["internal"],
                agent_id="unknown-agent",
            )
            self.assertEqual(req_blocked.decision.policy_name, "agent-identity")
            self.assertEqual(req_blocked.decision.action, "block")


if __name__ == "__main__":
    unittest.main()
