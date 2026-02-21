# Quickstart

SafeAI can be protecting your AI agent pipelines in two lines of code. This page walks through scanning inputs, guarding outputs, using the CLI, and wiring SafeAI into a real model call.

## Two-Line Setup

```python
from safeai import SafeAI

ai = SafeAI.quickstart()
```

`quickstart()` returns a fully configured SafeAI instance with sensible defaults: secret blocking enabled, PII redaction enabled, and an in-memory audit log. No config files required.

## Scan Inputs

Use `scan_input()` to inspect prompts before they reach your model. SafeAI detects API keys, tokens, passwords, and other secrets automatically.

```python
result = ai.scan_input("Use key AKIA5EXAMPLE1234ABCD to access the bucket")

print(result.decision.action)   # "block"
print(result.decision.reason)   # explains why the input was blocked
```

!!! note
    `scan_input` returns a result object whose `decision.action` is either `"allow"` or `"block"`. Always check the action before forwarding a prompt to your model.

## Guard Outputs

Use `guard_output()` to redact PII and enforce policies on model responses before they reach the user.

```python
result = ai.guard_output("Contact Jane Doe at jane.doe@example.com or 555-867-5309")

print(result.safe_output)
# "Contact [NAME] at [EMAIL] or [PHONE]"
```

PII categories such as names, emails, phone numbers, and addresses are redacted by default. You can customize which categories are redacted through configuration.

## CLI Quickstart

SafeAI ships with a command-line interface for scaffolding, scanning, and validating configurations.

### Initialize a project

```bash
safeai init
```

This creates a `safeai.yaml` config file and starter templates for policies, contracts, schemas, and agent definitions. See the [Configuration](configuration.md) guide for details.

### Scan a prompt from the terminal

```bash
safeai scan "Deploy with token ghp_abc123secret"
```

### Validate your config files

```bash
safeai validate
```

!!! tip
    Run `safeai validate` in CI to catch policy misconfigurations before deployment.

## Real-World Example: Gemini Integration

Below is a complete example that wraps Google Gemini with SafeAI guardrails. Inputs are scanned for secrets before reaching the model, and outputs are scrubbed for PII before reaching the user.

```python
import os
from safeai import SafeAI
from google import genai

ai = SafeAI.quickstart()
client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])


def safe_generate(prompt: str) -> str:
    # 1. Scan the incoming prompt
    scan = ai.scan_input(prompt)
    if scan.decision.action == "block":
        return f"BLOCKED: {scan.decision.reason}"

    # 2. Call the model
    response = client.models.generate_content(
        model="gemini-2.0-flash", contents=prompt
    )

    # 3. Guard the output
    guard = ai.guard_output(response.text)
    return guard.safe_output


# Usage
answer = safe_generate("Summarize the latest earnings report")
print(answer)
```

!!! warning
    Never pass the raw model response to end users without calling `guard_output()`. Even when inputs are clean, models can hallucinate PII or reproduce memorized secrets.

The same pattern works with any provider -- OpenAI, Claude, LangChain, CrewAI, AutoGen, Google ADK, or Claude ADK. Replace the model call in step 2 and the rest stays the same.

## Next: Auto-Configure with Intelligence

After trying the quickstart, let the intelligence layer generate a full configuration tailored to your project:

```bash
safeai init
safeai intelligence auto-config --path . --apply
```

This analyzes your project structure and generates policies, contracts, and agent identities automatically. See the [Intelligence Layer guide](../guides/intelligence.md) for details.

## Next Steps

- [Configuration](configuration.md) -- customize policies, rules, and audit settings via YAML.
- [Installation extras](installation.md#optional-extras) -- add vault, AWS, or MCP support.
