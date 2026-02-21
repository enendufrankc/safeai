"""Tool contract parser and validation tests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from safeai import SafeAI
from safeai.config.loader import ContractSchemaValidationError, load_contract_documents
from safeai.core.contracts import ToolContractRegistry, normalize_contracts


class ToolContractTests(unittest.TestCase):
    def test_registry_blocks_undeclared_tools(self) -> None:
        registry = ToolContractRegistry()
        result = registry.validate_request(tool_name="send_email", data_tags=["internal"])
        self.assertFalse(result.allowed)
        self.assertIn("no declared contract", result.reason)

    def test_registry_blocks_unauthorized_tags(self) -> None:
        registry = ToolContractRegistry(
            normalize_contracts(
                [
                    {
                        "version": "v1alpha1",
                        "contract": {
                            "tool_name": "send_email",
                            "accepts": {"tags": ["internal"]},
                            "emits": {"tags": ["internal"]},
                            "side_effects": {"reversible": False, "requires_approval": True},
                        },
                    }
                ]
            )
        )
        result = registry.validate_request(tool_name="send_email", data_tags=["secret.token"])
        self.assertFalse(result.allowed)
        self.assertEqual(result.unauthorized_tags, ["secret.token"])

    def test_registry_accepts_hierarchical_parent_tags(self) -> None:
        registry = ToolContractRegistry(
            normalize_contracts(
                [
                    {
                        "version": "v1alpha1",
                        "contract": {
                            "tool_name": "profile_lookup",
                            "accepts": {"tags": ["personal"]},
                            "emits": {"tags": ["internal"]},
                            "side_effects": {"reversible": True, "requires_approval": False},
                        },
                    }
                ]
            )
        )
        result = registry.validate_request(tool_name="profile_lookup", data_tags=["personal.pii"])
        self.assertTrue(result.allowed)
        self.assertEqual(result.unauthorized_tags, [])

    def test_contract_schema_validation_rejects_invalid_contract(self) -> None:
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
                        "audit:",
                        "  file_path: logs/audit.log",
                    ]
                ),
                encoding="utf-8",
            )
            (root / "contracts").mkdir(parents=True, exist_ok=True)
            (root / "contracts" / "broken.yaml").write_text(
                "\n".join(
                    [
                        "version: v1alpha1",
                        "contract:",
                        "  tool_name: send_email",
                        "  accepts: {tags: [internal]}",
                        "  emits: {tags: [internal]}",
                        "  # side_effects intentionally omitted",
                    ]
                ),
                encoding="utf-8",
            )
            with self.assertRaises(ContractSchemaValidationError):
                load_contract_documents(root / "safeai.yaml", ["contracts/*.yaml"], version="v1alpha1")

    def test_safeai_loads_contract_registry_from_config(self) -> None:
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
                        "audit:",
                        "  file_path: logs/audit.log",
                    ]
                ),
                encoding="utf-8",
            )
            (root / "policies").mkdir(parents=True, exist_ok=True)
            (root / "contracts").mkdir(parents=True, exist_ok=True)
            (root / "schemas").mkdir(parents=True, exist_ok=True)

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
                        "    tags: [internal]",
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

            sdk = SafeAI.from_config(root / "safeai.yaml")
            decision = sdk.validate_tool_request("send_email", ["personal.pii"])
            self.assertTrue(decision.allowed)
            blocked = sdk.validate_tool_request("unknown_tool", ["internal"])
            self.assertFalse(blocked.allowed)


if __name__ == "__main__":
    unittest.main()
