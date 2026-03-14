---
name: healthcare-policies
description: >
  HIPAA-aligned policy set for AI agent projects handling health data.
  Blocks protected health information (PHI) at input and action boundaries,
  redacts PHI from all AI outputs, and requires human approval for clinical
  tool calls (patient record queries and updates). References HIPAA 45 CFR
  §164.502, §164.514, §164.526. Use when the user is building a healthcare
  AI application, working with patient data, needs HIPAA compliance, or wants
  to prevent PHI from entering or leaving an AI agent boundary.
tier: stable
owner: SafeAI Contributors
domain: healthcare
functional-area: compliance
---

# Healthcare Policies (HIPAA)

Installs a HIPAA-aligned policy set that enforces PHI boundaries across all three SafeAI enforcement layers.

## What Gets Installed

- `policies/hipaa.yaml` — 7 policies covering PHI blocking, PII redaction, secrets blocking, clinical tool approval

## Policy Summary

| Policy | Boundary | Action |
|--------|----------|--------|
| Block PHI on input | input | block |
| Block PHI in tool args | action | block |
| Redact PHI from output | output | redact |
| Approve patient record queries | action | require_approval |
| Approve patient record updates | action | require_approval |
| Block credentials everywhere | input, action, output | block |
| Allow non-PHI | all | allow |

## HIPAA References

- §164.502 — Uses and disclosures of PHI
- §164.514(b)(2) — 18 PHI identifier categories
- §164.526 — Amendment of PHI

## Verify

```bash
safeai scan "Patient Jane Doe SSN 123-45-6789 DOB 1985-03-14"
# → action: block  tags: [personal.phi, personal.pii]
```
