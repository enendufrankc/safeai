# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 SafeAI Contributors
"""SafeAI intelligence layer example — auto-config and policy recommendations.

Requires:
  - A running AI backend (e.g., Ollama with llama3.2)
  - Intelligence configured in safeai.yaml

To run:
  1. Start Ollama: ollama serve
  2. Pull model: ollama pull llama3.2
  3. Run: python examples/intelligence_usage.py
"""

from safeai import SafeAI

ai = SafeAI.from_config("safeai.yaml")

# Check if intelligence is available
status = ai.intelligence_status()
print(f"Intelligence enabled: {status.get('enabled', False)}")
print(f"Backend: {status.get('backend', 'none')}")

if not status.get("enabled"):
    print("\nIntelligence layer is not enabled.")
    print("Run 'safeai init --path .' and enable the intelligence layer,")
    print("or add an 'intelligence' section to your safeai.yaml.")
else:
    # Auto-config: analyze codebase and generate SafeAI configuration
    print("\n--- Auto-Config ---")
    print("Run: safeai intelligence auto-config --path . --output-dir .safeai-generated")

    # Policy recommendations based on recent audit events
    print("\n--- Policy Recommendations ---")
    print("Run: safeai intelligence recommend --since 7d")

    # Compliance mapping
    print("\n--- Compliance Mapping ---")
    print("Run: safeai intelligence compliance --framework hipaa")
