"""Phase 4 proxy API integration tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml
from click.testing import CliRunner
from fastapi.testclient import TestClient

from safeai.cli.init import init_command
from safeai.proxy.server import create_app


class _FakeHTTPXResponse:
    def __init__(self, body: str, status_code: int = 200, headers: dict[str, str] | None = None) -> None:
        self.content = body.encode("utf-8")
        self.status_code = status_code
        self.headers = headers or {"content-type": "text/plain"}


class ProxyApiTests(unittest.TestCase):
    def _build_client(self, work: Path, *, mode: str = "sidecar", encrypted_memory: bool = False) -> TestClient:
        init_result = CliRunner().invoke(init_command, ["--path", str(work)])
        self.assertEqual(init_result.exit_code, 0, msg=init_result.output)

        memory_path = work / "schemas" / "memory.yaml"
        if encrypted_memory:
            memory_doc = yaml.safe_load(memory_path.read_text(encoding="utf-8"))
            memory_doc["memory"]["fields"][0]["encrypted"] = True
            memory_path.write_text(yaml.safe_dump(memory_doc, sort_keys=False), encoding="utf-8")

        app = create_app(config_path=str(work / "safeai.yaml"), mode=mode)
        return TestClient(app)

    def test_proxy_endpoints_cover_boundaries_and_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client = self._build_client(Path(tmp_dir), encrypted_memory=True)

            health = client.get("/v1/health")
            self.assertEqual(health.status_code, 200)
            self.assertEqual(health.json()["status"], "ok")

            scan = client.post(
                "/v1/scan/input",
                json={"text": "token=sk-ABCDEF1234567890ABCDEF", "agent_id": "default-agent"},
            )
            self.assertEqual(scan.status_code, 200)
            self.assertEqual(scan.json()["decision"]["action"], "block")

            structured = client.post(
                "/v1/scan/structured",
                json={
                    "payload": {"request": {"token": "sk-ABCDEF1234567890ABCDEF", "message": "deploy"}},
                    "agent_id": "default-agent",
                },
            )
            self.assertEqual(structured.status_code, 200)
            self.assertEqual(structured.json()["decision"]["action"], "block")

            json_path = Path(tmp_dir) / "scan_payload.json"
            json_path.write_text(
                json.dumps({"token": "sk-ABCDEF1234567890ABCDEF", "message": "deploy"}, ensure_ascii=True),
                encoding="utf-8",
            )
            file_scan = client.post(
                "/v1/scan/file",
                json={"path": str(json_path), "agent_id": "default-agent"},
            )
            self.assertEqual(file_scan.status_code, 200)
            self.assertEqual(file_scan.json()["mode"], "structured")
            self.assertEqual(file_scan.json()["decision"]["action"], "block")

            guarded = client.post(
                "/v1/guard/output",
                json={"text": "Contact alice@example.com", "agent_id": "default-agent"},
            )
            self.assertEqual(guarded.status_code, 200)
            self.assertEqual(guarded.json()["decision"]["action"], "redact")

            req = client.post(
                "/v1/intercept/tool",
                json={
                    "phase": "request",
                    "tool_name": "send_email",
                    "parameters": {
                        "to": "ops@example.com",
                        "subject": "S",
                        "body": "B",
                        "priority": "high",
                    },
                    "data_tags": ["internal"],
                    "agent_id": "default-agent",
                },
            )
            self.assertEqual(req.status_code, 200)
            self.assertEqual(req.json()["decision"]["action"], "allow")
            self.assertNotIn("priority", req.json()["filtered_parameters"])

            resp = client.post(
                "/v1/intercept/tool",
                json={
                    "phase": "response",
                    "tool_name": "send_email",
                    "response": {
                        "status": "sent",
                        "message_id": "m-1",
                        "recipient": "alice@example.com",
                    },
                    "data_tags": ["internal"],
                    "agent_id": "default-agent",
                },
            )
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.json()["decision"]["action"], "redact")
            self.assertNotIn("recipient", resp.json()["filtered_response"])

            write = client.post(
                "/v1/memory/write",
                json={"key": "user_preference", "value": "en-US", "agent_id": "default-agent"},
            )
            self.assertEqual(write.status_code, 200)
            self.assertTrue(write.json()["allowed"])

            read = client.post(
                "/v1/memory/read",
                json={"key": "user_preference", "agent_id": "default-agent"},
            )
            self.assertEqual(read.status_code, 200)
            handle = read.json()["value"]
            self.assertTrue(str(handle).startswith("hdl_"))

            resolved = client.post(
                "/v1/memory/resolve-handle",
                json={"handle_id": handle, "agent_id": "default-agent"},
            )
            self.assertEqual(resolved.status_code, 200)
            self.assertEqual(resolved.json()["value"], "en-US")

            purged = client.post("/v1/memory/purge-expired")
            self.assertEqual(purged.status_code, 200)
            self.assertGreaterEqual(int(purged.json()["purged"]), 0)

            audit = client.post("/v1/audit/query", json={"boundary": "action", "limit": 50})
            self.assertEqual(audit.status_code, 200)
            self.assertGreaterEqual(int(audit.json()["count"]), 1)

            reload_result = client.post("/v1/policies/reload", json={"force": True})
            self.assertEqual(reload_result.status_code, 200)
            self.assertTrue(reload_result.json()["reloaded"])

            plugins = client.get("/v1/plugins")
            self.assertEqual(plugins.status_code, 200)
            self.assertGreaterEqual(int(plugins.json()["count"]), 1)

            templates = client.get("/v1/policies/templates")
            self.assertEqual(templates.status_code, 200)
            self.assertGreaterEqual(int(templates.json()["count"]), 3)

            finance_template = client.get("/v1/policies/templates/finance")
            self.assertEqual(finance_template.status_code, 200)
            self.assertIn("policies", finance_template.json())

            metrics = client.get("/v1/metrics")
            self.assertEqual(metrics.status_code, 200)
            self.assertIn("safeai_proxy_requests_total", metrics.text)
            self.assertIn('/v1/intercept/tool', metrics.text)

    def test_gateway_mode_requires_agent_context_and_supports_agent_messages(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client = self._build_client(Path(tmp_dir), mode="gateway")

            missing = client.post(
                "/v1/intercept/tool",
                json={
                    "phase": "request",
                    "tool_name": "send_email",
                    "parameters": {"to": "ops@example.com", "subject": "S", "body": "B"},
                    "data_tags": ["internal"],
                    "agent_id": "default-agent",
                },
            )
            self.assertEqual(missing.status_code, 400)

            with_context = client.post(
                "/v1/intercept/tool",
                json={
                    "phase": "request",
                    "tool_name": "send_email",
                    "parameters": {"to": "ops@example.com", "subject": "S", "body": "B"},
                    "data_tags": ["internal"],
                    "agent_id": "default-agent",
                    "source_agent_id": "default-agent",
                    "destination_agent_id": "tool:send_email",
                },
            )
            self.assertEqual(with_context.status_code, 200)

            message = client.post(
                "/v1/intercept/agent-message",
                json={
                    "message": "Need approval context for deployment",
                    "source_agent_id": "planner-agent",
                    "destination_agent_id": "executor-agent",
                    "data_tags": ["internal"],
                    "session_id": "sess-gateway",
                },
            )
            self.assertEqual(message.status_code, 200)
            self.assertEqual(message.json()["decision"]["action"], "allow")
            self.assertIn("Need approval context", message.json()["filtered_message"])

    def test_proxy_forward_mode_filters_upstream_output_and_blocks_bad_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client = self._build_client(Path(tmp_dir))

            fake_response = _FakeHTTPXResponse("Contact alice@example.com")

            async def _fake_request(self_client, **kwargs):
                return fake_response

            with patch("httpx.AsyncClient.request", new=_fake_request):
                response = client.post(
                    "/v1/proxy/forward",
                    json={
                        "method": "POST",
                        "upstream_url": "https://upstream.example/api",
                        "json_body": {"hello": "world"},
                        "agent_id": "default-agent",
                    },
                )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["decision"]["action"], "redact")
            self.assertIn("REDACTED", response.json()["body"])

            blocked = client.post(
                "/v1/proxy/forward",
                json={
                    "method": "POST",
                    "upstream_url": "https://upstream.example/api",
                    "text_body": "token=sk-ABCDEF1234567890ABCDEF",
                    "agent_id": "default-agent",
                },
            )
            self.assertEqual(blocked.status_code, 403)
            self.assertIn("blocked", json.dumps(blocked.json(), sort_keys=True).lower())


if __name__ == "__main__":
    unittest.main()
