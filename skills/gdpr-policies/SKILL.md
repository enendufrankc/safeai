---
name: gdpr-policies
description: >
  GDPR-aligned policy set for AI agent projects processing EU personal data.
  Redacts PII from all AI outputs (data minimisation, Art. 5), blocks
  unconsented personal data on input (lawful basis, Art. 6), and requires
  human approval for third-party data transfers (Art. 44), erasure requests
  (Art. 17), and data portability exports (Art. 20). Use when the user is
  building an AI application that processes EU resident data, needs GDPR
  compliance, wants to enforce data minimisation, or must gate data subject
  rights requests behind human review.
tier: stable
owner: SafeAI Contributors
domain: privacy
functional-area: compliance
---

# GDPR Policies

Installs a GDPR-aligned policy set that enforces personal data boundaries and gates data subject rights operations.

## What Gets Installed

- `policies/gdpr.yaml` — 7 policies covering PII redaction, personal data input blocking, transfer/erasure/export approval, credentials blocking

## Policy Summary

| Policy | Boundary | Action |
|--------|----------|--------|
| Redact PII from all outputs | output | redact |
| Block PII on input | input | block |
| Approve third-party transfers | action | require_approval |
| Approve data erasure (Art. 17) | action | require_approval |
| Approve data exports (Art. 20) | action | require_approval |
| Block credentials everywhere | input, action, output | block |
| Allow non-personal data | all | allow |

## GDPR References

- Art. 5 — Principles of data processing (minimisation)
- Art. 6 — Lawfulness of processing
- Art. 17 — Right to erasure
- Art. 20 — Right to data portability
- Art. 44 — Transfers to third countries

## Verify

```bash
safeai scan "User email: jane.doe@example.com phone: +44 7911 123456"
# → action: block  tags: [personal.pii]
```
