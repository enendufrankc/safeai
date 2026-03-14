# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 SafeAI Contributors
"""SafeAI quickstart example — minimal setup with built-in defaults."""

from safeai import SafeAI

ai = SafeAI.quickstart()

# --- Input boundary ---
scan = ai.scan_input("Please process token=sk-ABCDEF1234567890ABCDEF")
print(f"Input scan: action={scan.decision.action}, reason={scan.decision.reason}")

# --- Output boundary ---
guard = ai.guard_output("Contact alice@example.com for details.")
print(f"Output guard: action={guard.decision.action}")
print(f"Safe output: {guard.safe_output}")
