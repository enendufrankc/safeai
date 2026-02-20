# SafeAI Governance

This document defines how the SafeAI project is governed.
It applies to this repository and project-owned sub-repositories unless stated otherwise.

## 1) Principles

- Security and user trust come first.
- Decisions should be transparent, documented, and reversible.
- Public interfaces should remain stable unless a documented breaking change is approved.
- Project direction is informed by contributors, users, and maintainers.

## 2) Roles

### Maintainers

Maintainers are responsible for technical direction and repository stewardship:

- Review and merge pull requests.
- Manage releases and deprecations.
- Approve policy, schema, and security-impacting changes.
- Enforce contribution and security policies.

Maintainer area ownership is listed in `MAINTAINERS.md`.

### Contributors

Contributors submit code, docs, tests, issues, and proposals.
Contributors do not need maintainer status to participate.

## 3) Decision model

### Routine changes

Routine changes (bug fixes, docs updates, non-breaking internal refactors) may merge with:

- At least 1 maintainer approval
- Passing required CI checks

### Significant changes

Significant changes require explicit design discussion and at least 2 maintainer approvals:

- Public API or CLI behavior changes
- Policy schema or contract schema changes
- Compatibility and migration-impacting changes
- New major dependencies or architectural shifts

Discussion can happen in an issue, PR design section, or RFC-style doc.

### Security-sensitive changes

Changes that affect boundary enforcement, credential handling, memory protection, or audit integrity require:

- At least 2 maintainer approvals
- At least 1 approval from a maintainer owning security/compliance

## 4) Governance changes

Changes to this governance model require:

- A pull request titled with `[governance]`
- A minimum 7-day review window
- A 2/3 majority of active maintainers

## 5) Maintainer lifecycle

### Becoming a maintainer

Typical baseline:

- Consistent contributions over time
- High-quality code reviews
- Ownership of at least one project area
- Demonstrated reliability in security and compatibility decisions

New maintainers are nominated by an existing maintainer and confirmed by majority vote of active maintainers.

### Renewal and inactivity

- Maintainer status is reviewed every 12 months.
- Maintainers with no meaningful activity for 90+ days may be marked inactive.
- Inactive maintainers do not count toward voting quorum until reactivated.

### Removal

Maintainers may be removed by 2/3 majority vote of active maintainers for:

- Extended inactivity
- Repeated policy violations
- Conduct violations

## 6) Repository administration

- Branch protection and required checks are mandatory on protected branches.
- Direct pushes to protected branches are disabled except for approved automation accounts.
- Security advisories and incident responses are handled per `SECURITY.md`.

## 7) Conduct

All project participation is subject to `CODE_OF_CONDUCT.md`.

