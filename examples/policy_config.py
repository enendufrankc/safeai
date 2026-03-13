"""SafeAI policy configuration example — custom YAML rules."""

from pathlib import Path
from textwrap import dedent

from safeai import SafeAI

# Write a minimal policy file
policy_path = Path("_example_policy.yaml")
policy_path.write_text(dedent("""\
    version: v1alpha1
    policies:
      - name: block-api-keys
        conditions:
          data_tags: ["secret.api_key"]
          boundary: input
        action: block
        reason: API keys are not allowed in prompts.
        priority: 1

      - name: redact-email
        conditions:
          data_tags: ["pii.email"]
          boundary: output
        action: redact
        reason: Email addresses must be redacted in responses.
        priority: 2

      - name: allow-all
        conditions: {}
        action: allow
        priority: 100
"""))

try:
    ai = SafeAI.quickstart()
    ai.policy_engine.load_file(str(policy_path))

    # Blocked: API key detected
    result = ai.scan_input("Use key sk-SECRET1234567890ABCDEF")
    print(f"API key scan: {result.decision.action} — {result.decision.reason}")

    # Redacted: email detected
    result = ai.guard_output("Reply to bob@company.com")
    print(f"Email guard:  {result.decision.action}")
    print(f"Safe output:  {result.safe_output}")

    # Allowed: clean input
    result = ai.scan_input("Hello, how are you?")
    print(f"Clean input:  {result.decision.action}")
finally:
    policy_path.unlink(missing_ok=True)
