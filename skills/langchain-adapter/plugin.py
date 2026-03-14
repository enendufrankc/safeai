# SPDX-License-Identifier: Apache-2.0
"""SafeAI LangChain adapter skill plugin.

Registers the SafeAILangChainAdapter so it is available to any SafeAI
instance that loads this plugin file. Also ships a 'langchain-baseline'
policy template that enforces safe defaults for LangChain tool usage.

Usage after install:
    from safeai import SafeAI
    ai = SafeAI.from_config("safeai.yaml")

    # Get the adapter
    adapter = ai.plugin_manager.build_adapter("langchain_adapter")

    # Wrap a tool function
    @adapter.wrap_tool("my_tool", agent_id="my-agent")
    def my_tool(query: str) -> str:
        return search(query)
"""

from __future__ import annotations

from safeai.middleware.base import BaseMiddleware


def safeai_adapters() -> dict[str, type[BaseMiddleware]]:
    """Register the LangChain adapter under the key 'langchain_adapter'."""
    try:
        from safeai.middleware.langchain import SafeAILangChainAdapter
        return {"langchain_adapter": SafeAILangChainAdapter}
    except ImportError:
        return {}


def safeai_policy_templates() -> dict[str, dict]:
    """Provide a ready-to-use LangChain safety policy template."""
    return {
        "langchain-baseline": {
            "version": "v1alpha1",
            "policies": [
                {
                    "name": "lc-block-secrets-in-tool-input",
                    "boundary": ["action"],
                    "priority": 5,
                    "condition": {"data_tags": ["secret.credential", "secret.token", "secret"]},
                    "action": "block",
                    "reason": "Secrets must not be passed as tool arguments.",
                },
                {
                    "name": "lc-redact-pii-from-tool-output",
                    "boundary": ["output"],
                    "priority": 10,
                    "condition": {"data_tags": ["personal.pii", "personal.phi", "personal"]},
                    "action": "redact",
                    "reason": "PII must be redacted from LangChain tool responses.",
                },
                {
                    "name": "lc-approve-web-requests",
                    "boundary": ["action"],
                    "priority": 20,
                    "condition": {"tool_name": "requests_get"},
                    "action": "require_approval",
                    "reason": "Outbound HTTP requests require human approval.",
                },
                {
                    "name": "lc-allow-default",
                    "boundary": ["input", "action", "output"],
                    "priority": 1000,
                    "condition": {},
                    "action": "allow",
                    "reason": "Allow when no restrictive policy matched.",
                },
            ],
        }
    }
