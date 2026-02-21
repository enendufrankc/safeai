# Secret Detection

SafeAI scans all inbound text for leaked credentials before they reach your agent. The `scan_input` method detects API keys, tokens, passwords, and other secrets using a library of built-in pattern detectors, blocking or redacting them so sensitive material never enters your pipeline.

## Quick Example

```python
from safeai import SafeAI

ai = SafeAI.quickstart()

result = ai.scan_input("API_KEY=sk-ABCDEF1234567890")
print(result.action)   # "block"
print(result.detections)
# [Detection(type="api_key", value="sk-ABCDEF****", span=(8, 30))]
```

## Full Example

```python
from safeai import SafeAI

ai = SafeAI.from_config("safeai.yaml")

user_message = """
Here are my credentials:
  AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
  AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
  DATABASE_URL=postgres://admin:s3cret@db.internal:5432/prod
"""

result = ai.scan_input(user_message)

if result.action == "block":
    print("Blocked — secrets detected:")
    for d in result.detections:
        print(f"  [{d.type}] at position {d.span}")
else:
    # safe to forward to agent
    agent.handle(result.safe_text)
```

!!! warning "Secrets are never forwarded"
    When `scan_input` detects a secret, the default action is **block**. The original text is never passed downstream. You can switch to **redact** mode if you need the surrounding text but want the secret values masked.

## Configuration

```yaml title="safeai.yaml"
scan:
  secret_detection:
    enabled: true
    action: block          # block | redact
    detectors:
      - api_key
      - aws_access_key
      - aws_secret_key
      - database_url
      - jwt_token
      - private_key
      - credit_card
      - password_assignment
    sensitivity: high      # low | medium | high
```

### Built-in Detectors

| Detector             | Description                              |
|----------------------|------------------------------------------|
| `api_key`            | Generic API keys (`sk-`, `pk-`, etc.)    |
| `aws_access_key`     | AWS access key IDs (`AKIA...`)           |
| `aws_secret_key`     | AWS secret access keys                   |
| `database_url`       | Connection strings with credentials      |
| `jwt_token`          | JSON Web Tokens                          |
| `private_key`        | PEM-encoded private keys                 |
| `credit_card`        | Credit/debit card numbers                |
| `password_assignment`| Inline password assignments              |

### Custom Detector Patterns via Plugins

You can register additional detectors using the plugin system:

```python
from safeai import SafeAI
from safeai.plugins import register_detector

@register_detector("internal_token")
def detect_internal_token(text):
    """Detect internal service tokens with prefix 'itk_'."""
    import re
    matches = re.finditer(r"itk_[A-Za-z0-9]{32,}", text)
    return [
        {"type": "internal_token", "span": (m.start(), m.end())}
        for m in matches
    ]

ai = SafeAI.quickstart()
result = ai.scan_input("Token: itk_abcdef1234567890abcdef1234567890")
# Detection triggered for internal_token
```

!!! tip "Combine with policy engine"
    Secret detections produce data tags such as `secret.api_key`. You can write policies that react to these tags with fine-grained actions. See the [Policy Engine guide](policy-engine.md) for details.

## See Also

- [API Reference — `scan_input`](../reference/safeai.md)
- [Structured Scanning guide](structured-scanning.md) for nested JSON payloads
- [Policy Engine guide](policy-engine.md) for tag-based rules
