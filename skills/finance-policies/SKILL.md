---
name: finance-policies
description: >
  PCI-DSS aligned policy set for AI agent projects handling payment data.
  Blocks primary account numbers (PAN), CVV codes, routing and account numbers
  at input and action boundaries. Redacts cardholder data from all AI outputs.
  Requires human approval for payment charges, refunds, and card storage.
  References PCI DSS v4.0 Requirements 3, 4, 7, 8. Use when the user is
  building a fintech or e-commerce AI application, handling payment cards,
  needs PCI-DSS compliance, or wants to prevent cardholder data from entering
  or leaving an AI agent boundary.
tier: stable
owner: SafeAI Contributors
domain: finance
functional-area: compliance
---

# Finance Policies (PCI-DSS)

Installs a PCI-DSS aligned policy set that enforces cardholder data boundaries across all three SafeAI enforcement layers.

## What Gets Installed

- `policies/pci-dss.yaml` — 8 policies covering PAN/CVV blocking, cardholder data redaction, payment tool approval, credentials blocking

## Policy Summary

| Policy | Boundary | Action |
|--------|----------|--------|
| Block cardholder data on input | input | block |
| Block cardholder data in tool args | action | block |
| Redact cardholder data from output | output | redact |
| Approve payment charges | action | require_approval |
| Approve refunds | action | require_approval |
| Approve card storage | action | require_approval |
| Block credentials everywhere | input, action, output | block |
| Allow non-financial data | all | allow |

## PCI-DSS References

- Req 3 — Protect stored cardholder data
- Req 3.3 — Sensitive authentication data must not be stored
- Req 3.4 — PAN must be masked in displays
- Req 7 — Restrict access by business need to know
- Req 8 — Identify and authenticate access to system components

## Verify

```bash
safeai scan "Charge card 4532015112830366 CVV 123"
# → action: block  tags: [personal.financial]
```
