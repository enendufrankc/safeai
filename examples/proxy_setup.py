"""SafeAI proxy setup example — start and test the sidecar proxy."""

import subprocess
import sys
import time

import httpx


def main() -> None:
    print("Starting SafeAI proxy in sidecar mode...")
    proc = subprocess.Popen(
        [sys.executable, "-m", "safeai.cli.main", "serve", "--mode", "sidecar", "--port", "8910"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        time.sleep(2)

        # Health check
        r = httpx.get("http://127.0.0.1:8910/v1/health")
        print(f"Health: {r.status_code} — {r.json()}")

        # Scan input
        r = httpx.post(
            "http://127.0.0.1:8910/v1/scan/input",
            json={"text": "My key is sk-TEST1234567890123456", "agent_id": "demo"},
        )
        print(f"Scan:   {r.status_code} — action={r.json()['decision']['action']}")

        # Guard output
        r = httpx.post(
            "http://127.0.0.1:8910/v1/guard/output",
            json={"text": "Email jane@test.com for info", "agent_id": "demo"},
        )
        print(f"Guard:  {r.status_code} — action={r.json()['decision']['action']}")

        # Metrics
        r = httpx.get("http://127.0.0.1:8910/v1/metrics")
        print(f"Metrics: {r.status_code} — {len(r.text)} bytes")

    finally:
        proc.terminate()
        proc.wait()
        print("Proxy stopped.")


if __name__ == "__main__":
    main()
