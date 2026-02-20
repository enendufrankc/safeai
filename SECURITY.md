# Security Policy

## Supported versions

Until the first stable release, only the default branch (`main`) is considered supported for security fixes.

## Reporting a vulnerability

Please report vulnerabilities privately.

Preferred channels:

1. GitHub Private Vulnerability Reporting (Security Advisories) for this repository
2. Direct contact to project maintainers listed in `MAINTAINERS.md`

Do not disclose vulnerability details in public issues.

## What to include in a report

- Title and severity assessment
- Affected component(s)
- Reproduction steps or proof of concept
- Demonstrated impact
- Environment details
- Suggested remediation (if available)

## Response targets

- Initial acknowledgment: within 48 hours
- Triage and severity assessment: within 5 business days
- Status updates: at least weekly until resolution

## Disclosure process

1. Confirm report validity and impact.
2. Identify affected versions and fix strategy.
3. Prepare a patch and regression tests.
4. Coordinate release timing and advisory publication.
5. Publish advisory with remediation guidance.

## Out of scope

The following are generally out of scope unless they demonstrate a concrete boundary-control bypass in SafeAI itself:

- Model hallucinations without enforcement-layer bypass
- Prompt injection examples with no SafeAI policy/control failure
- Vulnerabilities only present in unsupported forks or heavily modified local deployments

## Security updates

Security fixes will be communicated through repository releases and advisories.

