---
name: langchain-adapter
description: >
  Wraps any LangChain tool with SafeAI input, output, and action boundary
  enforcement. Registers the SafeAILangChainAdapter and a langchain-baseline
  policy template that blocks secrets in tool arguments and redacts PII from
  tool responses. Use when the user has a LangChain project and wants to add
  SafeAI guardrails, protect tool calls, redact PII from chain outputs, or
  enforce security policies on LangChain agents and tools.
tier: stable
owner: SafeAI Contributors
domain: security
functional-area: ai-safety
---

# LangChain Adapter

Installs SafeAI boundary enforcement for LangChain tool calls.

## What Gets Installed

- `plugins/langchain-adapter.py` — registers `langchain_adapter` and the `langchain-baseline` policy template

## Usage

```python
from safeai import SafeAI

ai = SafeAI.from_config("safeai.yaml")
adapter = ai.plugin_manager.build_adapter("langchain_adapter")

@adapter.wrap_tool("my_tool", agent_id="my-agent")
def my_tool(query: str) -> str:
    return search(query)
```

## Policy Template

Activate the bundled `langchain-baseline` template:

```yaml
# In safeai.yaml paths section, or install via:
safeai templates install langchain-baseline
```

Covers: block secrets in tool args, redact PII from tool output.
