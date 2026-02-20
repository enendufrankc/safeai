"""Lightweight performance regression gates for boundary paths."""

from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from safeai import SafeAI
from safeai.core.policy import PolicyContext


class BenchmarkGateTests(unittest.TestCase):
    def test_policy_and_classifier_path_regression_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            work = Path(tmp_dir)
            from click.testing import CliRunner

            from safeai.cli.init import init_command

            init_result = CliRunner().invoke(init_command, ["--path", str(work)])
            self.assertEqual(init_result.exit_code, 0, msg=init_result.output)

            sdk = SafeAI.from_config(work / "safeai.yaml")
            text = "Contact me at alice@example.com and token=sk-ABCDEFGHIJKLMNOPQRSTUV"

            start = time.perf_counter()
            for _ in range(1000):
                detections = sdk.classifier.classify_text(text)
                tags = sorted({item.tag for item in detections})
                sdk.policy_engine.evaluate(
                    PolicyContext(boundary="output", data_tags=tags, agent_id="agent-1")
                )
            elapsed = time.perf_counter() - start

            # Generous gate intended to catch severe regressions, not micro-tune latency.
            self.assertLess(elapsed, 5.0, msg=f"classifier+policy loop too slow: {elapsed:.3f}s")

    def test_boundary_end_to_end_regression_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            work = Path(tmp_dir)
            from click.testing import CliRunner

            from safeai.cli.init import init_command

            init_result = CliRunner().invoke(init_command, ["--path", str(work)])
            self.assertEqual(init_result.exit_code, 0, msg=init_result.output)

            sdk = SafeAI.from_config(work / "safeai.yaml")
            text = "email alice@example.com"

            start = time.perf_counter()
            for _ in range(200):
                sdk.scan_input(text, agent_id="agent-1")
                sdk.guard_output(text, agent_id="agent-1")
            elapsed = time.perf_counter() - start

            self.assertLess(elapsed, 5.0, msg=f"scan+guard loop too slow: {elapsed:.3f}s")


if __name__ == "__main__":
    unittest.main()
