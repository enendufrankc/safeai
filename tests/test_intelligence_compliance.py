"""Tests for the compliance advisory agent."""

from __future__ import annotations

import unittest

from safeai.intelligence.backend import AIMessage, AIResponse
from safeai.intelligence.compliance import ComplianceAdvisor
from safeai.intelligence.prompts.compliance import COMPLIANCE_REQUIREMENTS


class FakeAIBackend:
    def __init__(self, response_content: str = "", model: str = "fake") -> None:
        self.calls: list[list[AIMessage]] = []
        self._response_content = response_content
        self._model = model

    @property
    def model_name(self) -> str:
        return self._model

    def complete(self, messages: list[AIMessage], **kwargs) -> AIResponse:
        self.calls.append(messages)
        return AIResponse(content=self._response_content, model=self._model)


class ComplianceRequirementsTests(unittest.TestCase):
    def test_hipaa_requirements_exist(self) -> None:
        self.assertIn("hipaa", COMPLIANCE_REQUIREMENTS)
        self.assertIn("PHI", COMPLIANCE_REQUIREMENTS["hipaa"])

    def test_pci_dss_requirements_exist(self) -> None:
        self.assertIn("pci-dss", COMPLIANCE_REQUIREMENTS)
        self.assertIn("cardholder", COMPLIANCE_REQUIREMENTS["pci-dss"])

    def test_soc2_requirements_exist(self) -> None:
        self.assertIn("soc2", COMPLIANCE_REQUIREMENTS)
        self.assertIn("CC6.1", COMPLIANCE_REQUIREMENTS["soc2"])

    def test_gdpr_requirements_exist(self) -> None:
        self.assertIn("gdpr", COMPLIANCE_REQUIREMENTS)
        self.assertIn("Article 25", COMPLIANCE_REQUIREMENTS["gdpr"])


class ComplianceAdvisorTests(unittest.TestCase):
    def test_advise_hipaa(self) -> None:
        response = (
            "## Gap Analysis\nFull coverage.\n\n"
            "--- FILE: policies/hipaa-compliance.yaml ---\n"
            "version: v1alpha1\npolicies:\n  - name: hipaa-phi-protection\n"
        )
        backend = FakeAIBackend(response_content=response)
        advisor = ComplianceAdvisor(backend=backend)
        result = advisor.advise(framework="hipaa")

        self.assertEqual(result.status, "success")
        self.assertEqual(result.advisor_name, "compliance")
        self.assertIn("HIPAA", result.summary)
        self.assertIn("policies/hipaa-compliance.yaml", result.artifacts)

    def test_framework_mapping(self) -> None:
        """Each supported framework should produce a valid prompt."""
        for framework in COMPLIANCE_REQUIREMENTS:
            backend = FakeAIBackend(response_content="--- FILE: policies/test.yaml ---\ntest")
            advisor = ComplianceAdvisor(backend=backend)
            result = advisor.advise(framework=framework)
            self.assertEqual(result.status, "success", f"Failed for {framework}")

    def test_unknown_framework_returns_error(self) -> None:
        backend = FakeAIBackend()
        advisor = ComplianceAdvisor(backend=backend)
        result = advisor.advise(framework="unknown-framework")
        self.assertEqual(result.status, "error")
        self.assertIn("Unknown", result.summary)
        # Should not call backend
        self.assertEqual(len(backend.calls), 0)

    def test_gap_analysis_prompt_content(self) -> None:
        backend = FakeAIBackend(response_content="analysis")
        advisor = ComplianceAdvisor(backend=backend)
        advisor.advise(framework="hipaa")

        user_msg = backend.calls[0][1].content
        # Should contain HIPAA requirements
        self.assertIn("PHI", user_msg)
        self.assertIn("164.312", user_msg)

    def test_policy_generation(self) -> None:
        response = (
            "--- FILE: policies/gdpr-compliance.yaml ---\n"
            "version: v1alpha1\n"
            "policies:\n"
            "  - name: gdpr-data-protection\n"
            "    boundary: [input, output]\n"
            "    action: block\n"
        )
        backend = FakeAIBackend(response_content=response)
        advisor = ComplianceAdvisor(backend=backend)
        result = advisor.advise(framework="gdpr")
        self.assertIn("gdpr-data-protection", result.artifacts.get("policies/gdpr-compliance.yaml", ""))

    def test_backend_error(self) -> None:
        class FailingBackend:
            @property
            def model_name(self) -> str:
                return "fail"
            def complete(self, messages, **kwargs):
                raise RuntimeError("timeout")

        advisor = ComplianceAdvisor(backend=FailingBackend())
        result = advisor.advise(framework="hipaa")
        self.assertEqual(result.status, "error")


if __name__ == "__main__":
    unittest.main()
