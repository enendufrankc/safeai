# Security Policy

SafeAI is security infrastructure. We take vulnerability reports seriously and respond to them promptly.

---

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.6.x | :white_check_mark: Active |
| 0.5.x | :white_check_mark: Security fixes only |
| < 0.5.0 | :x: End of life |

We recommend always running the latest release.

---

## Reporting Vulnerabilities

!!! danger "Do not file public issues for security vulnerabilities"
    If you discover a security vulnerability, please report it privately. Do **not** open a public GitHub issue.

### How to report

Send your report to the maintainers listed in `MAINTAINERS.md` via:

- **GitHub Security Advisories:** Use the "Report a vulnerability" button on the [Security tab](https://github.com/enendufrankc/safeai/security/advisories) of the repository.
- **Email:** If Security Advisories are not available, contact the maintainers directly via the email addresses listed in `MAINTAINERS.md`.

### What to include

Your report should include as much of the following as possible:

- **Description** of the vulnerability
- **Affected component** (e.g., policy engine, secret handling, audit logger)
- **Steps to reproduce** the issue
- **Impact assessment** -- what can an attacker achieve?
- **Suggested fix** (if you have one)
- **Your contact information** for follow-up questions

---

## Response Targets

| Milestone | Target |
|-----------|--------|
| Acknowledgment | 48 hours |
| Initial triage and severity assessment | 5 business days |
| Fix development and testing | Depends on severity |
| Patch release | As soon as fix is verified |
| Public disclosure | After patch is available |

!!! note
    These are targets, not guarantees. Complex vulnerabilities may require more time for proper remediation.

---

## Disclosure Process

We follow a coordinated disclosure process:

1. **Report received.** We acknowledge receipt within 48 hours.
2. **Triage.** We assess the severity and affected versions within 5 business days.
3. **Fix development.** We develop and test a fix in a private branch.
4. **Patch release.** We publish a new release with the fix.
5. **Advisory.** We publish a GitHub Security Advisory with details of the vulnerability and the fix.
6. **Credit.** We credit the reporter in the advisory (unless they request anonymity).

We will coordinate disclosure timing with the reporter. We ask reporters to allow us reasonable time to develop and release a fix before public disclosure.

---

## Out of Scope

The following are generally not considered security vulnerabilities in SafeAI:

- **Misconfigured policies** -- SafeAI enforces the policies you configure. If your policies permit unsafe behavior, that is a configuration issue, not a vulnerability.
- **Denial of service via large inputs** -- While we aim to handle large inputs gracefully, extreme inputs that cause slow processing are a performance issue, not a security issue.
- **Dependencies** -- Vulnerabilities in third-party dependencies should be reported to those projects. If a dependency vulnerability affects SafeAI's security posture, please do report it to us.
- **Social engineering** -- Attacks that require tricking a maintainer into merging malicious code are out of scope for this policy.

---

## Security Best Practices

When using SafeAI in production:

- Keep SafeAI updated to the latest supported version.
- Review and test policy changes before deploying them.
- Enable audit logging and monitor for unexpected enforcement patterns.
- Use the principle of least privilege: start restrictive and open up as needed.
- Rotate any secrets managed through SafeAI's secret backends regularly.
- Run `safeai validate` in CI to catch configuration errors before deployment.
