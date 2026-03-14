---
name: secrets-detector
description: >
  Extended secrets and credentials detector with 40+ patterns beyond the
  SafeAI built-ins. Covers Anthropic, GitHub (PAT classic/fine-grained/OAuth),
  AWS session tokens, GCP service accounts, Azure connection strings, Stripe,
  Slack, Twilio, SendGrid, npm, PyPI, JWT tokens, RSA/EC/OpenSSH/PGP private
  keys, PostgreSQL, MySQL, MongoDB, Redis connection strings, and basic-auth
  URLs. Use when the user wants broader secret detection, needs to catch
  provider-specific API keys, or is working in a multi-cloud environment.
tier: stable
owner: SafeAI Contributors
domain: security
functional-area: ai-safety
---

# Extended Secrets Detector

Installs 40+ credential detection patterns on top of SafeAI's built-in detectors.

## What Gets Installed

- `plugins/secrets-detector.py` — additional patterns tagged `secret.credential`, `secret.token`, `secret.key`, `secret.connection`

## Pattern Coverage

| Provider / Type | Tag |
|-----------------|-----|
| Anthropic API keys | `secret.credential` |
| GitHub PAT (classic, fine-grained, OAuth, app) | `secret.credential` |
| AWS secret key, session token | `secret.credential` / `secret.token` |
| GCP API key, service account JSON | `secret.credential` |
| Azure connection strings, SAS tokens | `secret.connection` / `secret.token` |
| Stripe live/test keys | `secret.credential` |
| Slack bot/user tokens, webhooks | `secret.credential` |
| Twilio auth token + SID | `secret.credential` |
| SendGrid / Mailgun keys | `secret.credential` |
| npm / PyPI tokens | `secret.credential` |
| JWT tokens | `secret.token` |
| RSA, EC, OpenSSH, PGP private keys | `secret.key` |
| PostgreSQL, MySQL, MongoDB, Redis URIs | `secret.connection` |
| Basic auth URLs, bearer headers, password= | `secret.credential` |

## Verify

```bash
safeai scan "sk-ant-api03-abcdefghijklmnopqrstuvwxyz1234567890"
# → action: block  tags: [secret.credential]
```
