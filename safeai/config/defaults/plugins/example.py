"""Example SafeAI plugin scaffold.

This file is copied by `safeai init` to `plugins/example.py`.
"""

from __future__ import annotations

from safeai.middleware.base import BaseMiddleware


class ExamplePluginAdapter(BaseMiddleware):
    """Minimal plugin adapter scaffold."""

    def middleware(self) -> dict[str, str]:
        return {"name": "ExamplePluginAdapter"}


def safeai_detectors() -> list[tuple[str, str, str]]:
    """Return additional (name, tag, regex) detector tuples."""
    return [
        ("ticket_id", "internal.ticket", r"\bTKT-[0-9]{4,10}\b"),
    ]


def safeai_adapters() -> dict[str, type[BaseMiddleware]]:
    """Return plugin-provided framework adapters."""
    return {"example_plugin_adapter": ExamplePluginAdapter}


def safeai_policy_templates() -> dict[str, dict]:
    """Return plugin-provided policy templates."""
    return {
        "plugin-baseline": {
            "version": "v1alpha1",
            "policies": [
                {
                    "name": "plugin-block-internal-ticket-exfil",
                    "boundary": ["output"],
                    "priority": 30,
                    "condition": {"data_tags": ["internal.ticket"]},
                    "action": "redact",
                    "reason": "Internal ticket IDs should not leave trusted boundaries.",
                }
            ],
        }
    }
