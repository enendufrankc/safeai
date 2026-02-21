# Governance

This document describes how the SafeAI project is governed, how decisions are made, and how contributors advance to maintainer roles.

---

## Principles

The SafeAI project operates under three governing principles:

1. **Security first.** Decisions that affect boundary enforcement, policy evaluation, or secret handling are held to the highest review standard. Security never takes a back seat to velocity.

2. **Transparent process.** All decisions are made in public (on GitHub issues, PRs, and discussions) unless they involve a security vulnerability under coordinated disclosure.

3. **Stable APIs.** Users and plugin authors depend on SafeAI's interfaces. Breaking changes require explicit justification, a deprecation cycle, and migration guidance.

---

## Roles

### Maintainers

Maintainers have write access to the repository and are responsible for:

- Reviewing and merging pull requests
- Triaging issues and security reports
- Making release decisions
- Enforcing the Code of Conduct
- Guiding project direction

Current maintainers are listed in `MAINTAINERS.md` in the repository root.

### Contributors

Anyone who has had a pull request merged is a contributor. Contributors can:

- Open issues and pull requests
- Participate in discussions
- Review pull requests (non-binding reviews)
- Propose governance changes

---

## Decision Model

Decisions fall into three tiers based on their impact:

### Routine decisions

**Examples:** Bug fixes, documentation improvements, minor refactors, new test cases.

**Process:** 1 maintainer approval on the pull request.

### Significant decisions

**Examples:** New features, API additions, new CLI commands, dependency changes, new framework adapters.

**Process:** 2 maintainer approvals on the pull request. If maintainers disagree, discussion continues until consensus is reached.

### Security decisions

**Examples:** Changes to boundary enforcement, policy evaluation logic, secret handling, encryption, audit logging, access control.

**Process:** 2 maintainer approvals + 1 security owner approval. Security owners are maintainers with domain expertise in the affected area.

!!! info
    If the project has fewer than 3 active maintainers, security decisions require all active maintainers to approve.

---

## Governance Changes

Changes to this governance document follow their own process:

1. Open a pull request modifying this document.
2. Allow a 7-day review period for all maintainers and contributors to comment.
3. Require a 2/3 majority of active maintainers to approve.
4. No silent merges -- the review period cannot be shortened.

---

## Maintainer Lifecycle

### Becoming a maintainer

Contributors are nominated for maintainer status based on sustained, high-quality contributions. The criteria are:

- **Track record:** Multiple merged PRs demonstrating understanding of the codebase and its design principles.
- **Review quality:** Thoughtful, constructive code reviews on other contributors' PRs.
- **Reliability:** Consistent participation over time (not just a burst of activity).
- **Judgment:** Demonstrated ability to balance competing concerns (security, usability, compatibility, velocity).

Any existing maintainer can nominate a contributor. Nomination requires approval from all existing maintainers.

### Stepping down

Maintainers can step down at any time by opening a PR to remove themselves from `MAINTAINERS.md`. We appreciate the time and effort of all maintainers, past and present.

### Inactive maintainers

If a maintainer has not participated in any review, issue, or discussion for 6 months, another maintainer may propose transitioning them to emeritus status. The inactive maintainer is contacted first. If there is no response within 30 days, they are moved to emeritus and their write access is removed. Emeritus maintainers can be reinstated by requesting it and receiving approval from the active maintainers.

---

## Dispute Resolution

If maintainers cannot reach consensus on a decision:

1. The disagreement is documented in the relevant PR or issue.
2. A 7-day discussion period is opened for all maintainers to weigh in.
3. After the discussion period, a majority vote among active maintainers decides the outcome.
4. If the vote is tied, the status quo is maintained (the change is not merged).
