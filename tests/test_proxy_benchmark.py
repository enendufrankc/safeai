"""Proxy latency/throughput regression gates for Phase 4."""

from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from click.testing import CliRunner
from fastapi.testclient import TestClient

from safeai.cli.init import init_command
from safeai.proxy.server import create_app


class ProxyBenchmarkTests(unittest.TestCase):
    def _build_client(self, work: Path) -> TestClient:
        init_result = CliRunner().invoke(init_command, ["--path", str(work)])
        self.assertEqual(init_result.exit_code, 0, msg=init_result.output)
        app = create_app(config_path=str(work / "safeai.yaml"), mode="sidecar")
        return TestClient(app)

    def test_scan_input_proxy_regression_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client = self._build_client(Path(tmp_dir))
            iterations = 250
            started = time.perf_counter()
            for _ in range(iterations):
                response = client.post(
                    "/v1/scan/input",
                    json={"text": "internal summary for routing", "agent_id": "default-agent"},
                )
                self.assertEqual(response.status_code, 200)
            elapsed = time.perf_counter() - started
            avg = elapsed / iterations
            throughput = iterations / elapsed if elapsed else float("inf")

            self.assertLess(avg, 0.08, msg=f"Average /v1/scan/input latency too high: {avg:.6f}s")
            self.assertGreater(throughput, 100, msg=f"Proxy throughput regression: {throughput:.1f} req/s")

    def test_intercept_tool_proxy_regression_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            client = self._build_client(Path(tmp_dir))
            iterations = 180
            started = time.perf_counter()
            for _ in range(iterations):
                response = client.post(
                    "/v1/intercept/tool",
                    json={
                        "phase": "request",
                        "tool_name": "send_email",
                        "parameters": {
                            "to": "ops@example.com",
                            "subject": "Subject",
                            "body": "Body",
                        },
                        "data_tags": ["internal"],
                        "agent_id": "default-agent",
                    },
                )
                self.assertEqual(response.status_code, 200)
            elapsed = time.perf_counter() - started
            avg = elapsed / iterations
            throughput = iterations / elapsed if elapsed else float("inf")

            self.assertLess(avg, 0.08, msg=f"Average /v1/intercept/tool latency too high: {avg:.6f}s")
            self.assertGreater(throughput, 80, msg=f"Proxy intercept throughput regression: {throughput:.1f} req/s")


if __name__ == "__main__":
    unittest.main()
