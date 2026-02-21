"""Phase 5 dashboard and enterprise integration tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import yaml
from click.testing import CliRunner
from fastapi.testclient import TestClient

from safeai.cli.init import init_command
from safeai.proxy.server import create_app


class DashboardPhase5Tests(unittest.TestCase):
    def _build_client(self, work: Path) -> TestClient:
        init_result = CliRunner().invoke(init_command, ["--path", str(work)])
        self.assertEqual(init_result.exit_code, 0, msg=init_result.output)
        app = create_app(config_path=str(work / "safeai.yaml"), mode="sidecar")
        return TestClient(app)

    @staticmethod
    def _auth(user: str, tenant: str | None = None) -> dict[str, str]:
        headers = {"x-safeai-user": user}
        if tenant:
            headers["x-safeai-tenant"] = tenant
        return headers

    def test_dashboard_overview_approval_ui_and_compliance_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            work = Path(tmp_dir)
            client = self._build_client(work)
            runtime = client.app.state.runtime

            client.post(
                "/v1/scan/input",
                json={"text": "token=sk-ABCDEF1234567890ABCDEF", "agent_id": "default-agent"},
            )
            client.post(
                "/v1/guard/output",
                json={"text": "Contact jane@example.com", "agent_id": "default-agent"},
            )
            pending = runtime.safeai.approvals.create_request(
                reason="deployment requires approval",
                policy_name="deployment-approval",
                agent_id="default-agent",
                tool_name="deploy_prod",
                data_tags=["internal"],
            )

            headers = self._auth("security-admin")
            overview = client.get("/v1/dashboard/overview?last=24h", headers=headers)
            self.assertEqual(overview.status_code, 200)
            overview_body = overview.json()
            self.assertGreaterEqual(int(overview_body["events_total"]), 1)
            self.assertGreaterEqual(int(overview_body["pending_approvals"]), 1)

            queue = client.get("/v1/dashboard/approvals?status=pending&limit=10", headers=headers)
            self.assertEqual(queue.status_code, 200)
            self.assertEqual(queue.json()[0]["status"], "pending")

            approved = client.post(
                f"/v1/dashboard/approvals/{pending.request_id}/approve",
                json={"note": "verified by security"},
                headers=headers,
            )
            self.assertEqual(approved.status_code, 200)
            self.assertEqual(approved.json()["status"], "approved")

            report = client.post(
                "/v1/dashboard/compliance/report",
                json={"last": "24h"},
                headers=self._auth("security-auditor"),
            )
            self.assertEqual(report.status_code, 200)
            report_body = report.json()
            self.assertIn("summary", report_body)
            self.assertIn("approval_stats", report_body["summary"])

            dashboard = client.get("/dashboard")
            self.assertEqual(dashboard.status_code, 200)
            self.assertIn("SafeAI Security Dashboard", dashboard.text)

    def test_rbac_blocks_approval_decision_for_viewer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            work = Path(tmp_dir)
            client = self._build_client(work)
            runtime = client.app.state.runtime
            pending = runtime.safeai.approvals.create_request(
                reason="email send requires approval",
                policy_name="email-approval",
                agent_id="default-agent",
                tool_name="send_email",
                data_tags=["internal"],
            )

            denied = client.post(
                f"/v1/dashboard/approvals/{pending.request_id}/deny",
                json={"note": "viewer should not decide"},
                headers=self._auth("security-viewer"),
            )
            self.assertEqual(denied.status_code, 403)

            listed = client.get("/v1/dashboard/approvals?status=pending", headers=self._auth("security-viewer"))
            self.assertEqual(listed.status_code, 200)
            self.assertGreaterEqual(len(listed.json()), 1)

    def test_tenant_isolation_and_policy_set_management(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            work = Path(tmp_dir)
            CliRunner().invoke(init_command, ["--path", str(work)])

            config_path = work / "safeai.yaml"
            config_doc = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            config_doc["dashboard"]["users"] = [
                {"user_id": "security-admin", "role": "admin", "tenants": ["*"]},
                {"user_id": "tenant-a-viewer", "role": "viewer", "tenants": ["tenant-a"]},
                {"user_id": "tenant-b-viewer", "role": "viewer", "tenants": ["tenant-b"]},
            ]
            config_path.write_text(yaml.safe_dump(config_doc, sort_keys=False), encoding="utf-8")

            tenant_path = work / "tenants" / "policy-sets.yaml"
            tenant_doc = {
                "version": "v1alpha1",
                "tenants": [
                    {
                        "tenant_id": "tenant-a",
                        "name": "Tenant A",
                        "policy_files": ["policies/default.yaml"],
                        "agents": ["agent-a"],
                    },
                    {
                        "tenant_id": "tenant-b",
                        "name": "Tenant B",
                        "policy_files": ["policies/default.yaml"],
                        "agents": ["agent-b"],
                    },
                ],
            }
            tenant_path.write_text(yaml.safe_dump(tenant_doc, sort_keys=False), encoding="utf-8")

            app = create_app(config_path=str(config_path), mode="sidecar")
            client = TestClient(app)

            client.post("/v1/scan/input", json={"text": "internal request", "agent_id": "agent-a"})
            client.post("/v1/scan/input", json={"text": "internal request", "agent_id": "agent-b"})

            events_a = client.post(
                "/v1/dashboard/events/query",
                json={"boundary": "input", "last": "1h", "limit": 50},
                headers=self._auth("tenant-a-viewer"),
            )
            self.assertEqual(events_a.status_code, 200)
            agent_ids = {row.get("agent_id") for row in events_a.json()["events"]}
            self.assertEqual(agent_ids, {"agent-a"})

            update = client.put(
                "/v1/dashboard/tenants/tenant-a/policies",
                json={
                    "name": "Tenant A Updated",
                    "policy_files": ["policies/default.yaml", "policies/strict.yaml"],
                    "agents": ["agent-a", "agent-a2"],
                },
                headers=self._auth("security-admin"),
            )
            self.assertEqual(update.status_code, 200)
            self.assertIn("policies/strict.yaml", update.json()["policy_files"])

            blocked = client.get(
                "/v1/dashboard/tenants/tenant-a/policies",
                headers=self._auth("tenant-b-viewer"),
            )
            self.assertEqual(blocked.status_code, 403)

    def test_alert_rule_trigger_and_alert_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            work = Path(tmp_dir)
            client = self._build_client(work)
            headers = self._auth("security-admin")

            rule = client.post(
                "/v1/dashboard/alerts/rules",
                json={
                    "rule_id": "blocked-now",
                    "name": "Blocked decisions now",
                    "threshold": 1,
                    "window": "1h",
                    "filters": {"actions": ["block"]},
                    "channels": ["file"],
                },
                headers=headers,
            )
            self.assertEqual(rule.status_code, 200)

            client.post(
                "/v1/scan/input",
                json={"text": "token=sk-ABCDEF1234567890ABCDEF", "agent_id": "default-agent"},
            )

            evaluated = client.post(
                "/v1/dashboard/alerts/evaluate",
                json={"last": "1h"},
                headers=headers,
            )
            self.assertEqual(evaluated.status_code, 200)
            self.assertGreaterEqual(int(evaluated.json()["triggered_count"]), 1)

            alert_log = work / "logs" / "alerts.log"
            self.assertTrue(alert_log.exists())
            lines = [line for line in alert_log.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertGreaterEqual(len(lines), 1)
            payloads = [json.loads(line) for line in lines]
            rule_ids = {row.get("rule_id") for row in payloads}
            self.assertIn("blocked-now", rule_ids)


if __name__ == "__main__":
    unittest.main()
