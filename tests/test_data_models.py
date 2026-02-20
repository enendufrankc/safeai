"""Validation tests for hardened core data models."""

from __future__ import annotations

import unittest

from pydantic import ValidationError

from safeai.core.models import (
    AuditEventModel,
    DetectionModel,
    MemorySchemaDocumentModel,
    PolicyRuleModel,
)


class DataModelValidationTests(unittest.TestCase):
    def test_detection_rejects_invalid_span(self) -> None:
        with self.assertRaises(ValidationError):
            DetectionModel(detector="email", tag="personal.pii", start=20, end=10, value="x")

    def test_policy_rule_rejects_invalid_action(self) -> None:
        with self.assertRaises(ValidationError):
            PolicyRuleModel(
                name="bad-action",
                boundary=["input"],
                action="deny",  # type: ignore[arg-type]
                reason="bad",
                condition={},
                priority=1,
            )

    def test_audit_model_rejects_invalid_tag(self) -> None:
        with self.assertRaises(ValidationError):
            AuditEventModel(
                boundary="input",
                action="allow",
                policy_name="p",
                reason="ok",
                data_tags=["Bad Tag"],
                agent_id="a1",
            )

    def test_memory_schema_requires_memory_payload(self) -> None:
        with self.assertRaises(ValidationError):
            MemorySchemaDocumentModel(version="v1alpha1")


if __name__ == "__main__":
    unittest.main()
