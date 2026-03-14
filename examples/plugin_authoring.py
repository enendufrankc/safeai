# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 SafeAI Contributors
"""SafeAI plugin authoring example — custom detector and policy template."""

from safeai import SafeAI


# --- Define a custom plugin inline ---
def safeai_detectors():
    """Register custom detector patterns."""
    return [
        (r"PROJ-\d{4,8}", "internal.project_id", "project_id_detector"),
    ]


def safeai_policy_templates():
    """Register a custom policy template."""
    return [
        {
            "name": "internal-ids",
            "description": "Block internal project IDs from leaving the system.",
            "template": {
                "version": "v1alpha1",
                "policies": [
                    {
                        "name": "block-project-ids",
                        "conditions": {
                            "data_tags": ["internal.project_id"],
                            "boundary": "output",
                        },
                        "action": "redact",
                        "reason": "Internal project IDs must not appear in output.",
                        "priority": 1,
                    },
                ],
            },
        }
    ]


# --- Use the plugin ---
ai = SafeAI.quickstart()

# Register custom detectors manually (normally loaded from plugins/*.py)
for pattern, tag, name in safeai_detectors():
    ai.scanner.add_pattern(pattern, tag, name)

# Test detection
result = ai.scan_input("Update PROJ-12345 with the new data")
print(f"Detected tags: {result.tags}")
print(f"Decision: {result.decision.action}")
