# PII Protection

SafeAI prevents your agent from leaking personally identifiable information. The `guard_output` method scans outbound text for emails, phone numbers, Social Security numbers, credit card numbers, and other PII, then blocks or redacts the response before it reaches the end user.

## Quick Example

```python
from safeai import SafeAI

ai = SafeAI.quickstart()

result = ai.guard_output("Contact alice@example.com for details.")
print(result.action)     # "redact"
print(result.safe_text)  # "Contact [EMAIL REDACTED] for details."
```

## Full Example

```python
from safeai import SafeAI

ai = SafeAI.quickstart(pii_mode="redact")

agent_response = """
Patient Summary:
  Name: Jane Doe
  SSN: 123-45-6789
  Phone: (555) 867-5309
  Email: jane.doe@hospital.org
  Card on file: 4111-1111-1111-1111
"""

result = ai.guard_output(agent_response)

if result.detections:
    print(f"Redacted {len(result.detections)} PII instance(s)")
    for d in result.detections:
        print(f"  [{d.type}] {d.original_value!r} → {d.replacement!r}")

# Send the safe version to the user
send_to_user(result.safe_text)
```

!!! danger "Default mode is redact"
    By default, `guard_output` **redacts** PII rather than blocking the entire response. Switch to `block_pii` mode if any PII detection should prevent the response from being sent at all.

## Block vs. Redact Modes

Choose the mode that fits your compliance requirements:

```python
# Redact mode — mask PII, keep surrounding text
ai = SafeAI.quickstart(pii_mode="redact")

# Block mode — reject the entire response if PII is found
ai = SafeAI.quickstart(pii_mode="block")
```

| Mode     | Behavior                                      | Use case                              |
|----------|-----------------------------------------------|---------------------------------------|
| `redact` | Replace PII with placeholders like `[EMAIL REDACTED]` | Customer-facing chat, logs   |
| `block`  | Reject the entire output                      | Strict compliance, healthcare, finance|

## Configuration

```yaml title="safeai.yaml"
guard:
  pii_protection:
    enabled: true
    mode: redact           # block | redact
    detectors:
      - email
      - phone
      - ssn
      - credit_card
      - name
      - address
    redaction_format: "[{TYPE} REDACTED]"
```

### Built-in PII Detectors

| Detector      | Pattern Example                    | Redacted As                |
|---------------|------------------------------------|----------------------------|
| `email`       | `alice@example.com`                | `[EMAIL REDACTED]`         |
| `phone`       | `(555) 867-5309`                   | `[PHONE REDACTED]`         |
| `ssn`         | `123-45-6789`                      | `[SSN REDACTED]`           |
| `credit_card` | `4111-1111-1111-1111`              | `[CREDIT_CARD REDACTED]`   |
| `name`        | Named entity recognition           | `[NAME REDACTED]`          |
| `address`     | Physical mailing addresses         | `[ADDRESS REDACTED]`       |

!!! info "Custom redaction format"
    Override the placeholder format in your config. For example, set `redaction_format: "***"` to replace all PII with asterisks instead of typed labels.

## See Also

- [API Reference — `guard_output`](../reference/safeai.md)
- [Secret Detection guide](secret-detection.md) for inbound scanning
- [Policy Engine guide](policy-engine.md) for tag-based PII rules
