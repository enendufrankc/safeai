"""SafeAI end-to-end example for SDK mode."""

from __future__ import annotations

from pathlib import Path

from safeai import SafeAI


def run_example(config_path: str = "safeai.yaml") -> None:
    safeai = SafeAI.from_config(config_path)

    inbound = "Please send this secret token=sk-ABCDEFGHIJKLMNOPQRSTUV to support."
    scanned = safeai.scan_input(inbound, agent_id="assistant-1")
    print("[input] action=", scanned.decision.action)
    print("[input] filtered=", repr(scanned.filtered))

    model_output = "Contact alice@example.com for account support."
    guarded = safeai.guard_output(model_output, agent_id="assistant-1")
    print("[output] action=", guarded.decision.action)
    print("[output] safe_output=", repr(guarded.safe_output))

    if safeai.memory:
        safeai.memory_write("user_preference", "en-US", agent_id="assistant-1")
        remembered = safeai.memory_read("user_preference", agent_id="assistant-1")
        print("[memory] user_preference=", remembered)

    recent = safeai.query_audit(limit=5)
    print("[audit] recent events=", len(recent))


if __name__ == "__main__":
    path = Path("safeai.yaml")
    if not path.exists():
        raise SystemExit("safeai.yaml not found. Run: safeai init")
    run_example(str(path))
