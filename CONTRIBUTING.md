# Contributing to SafeAI

Thanks for your interest in contributing to SafeAI.
This project is currently in pre-kickoff planning and standards setup, and contributions are welcome.

## 1) Ways to contribute

- Report bugs and edge cases
- Propose features and design improvements
- Improve docs and examples
- Contribute code and tests
- Review pull requests

## 2) Start with an issue for larger changes

Before implementing substantial work, open an issue describing:

- Problem statement and use case
- Proposed approach
- Alternatives considered
- Risks (security, compatibility, performance)

Small fixes and documentation updates can be submitted directly as pull requests.

## 3) Development standards

- Add or update tests for behavioral changes.
- Keep changes focused and scoped to one concern.
- Update docs for user-visible or API/schema changes.
- Ensure required CI checks pass.

## 4) Commit and sign-off policy (DCO)

All commits must be signed off by a human author.
Use:

```bash
git commit -s -m "your message"
```

By signing off, you certify compliance with the Developer Certificate of Origin:
https://developercertificate.org/

## 5) AI-assisted contribution policy

AI tools are permitted with the following conditions:

- You are fully responsible for correctness, licensing, and security of submitted code.
- You must be able to explain your changes during review.
- If AI assistance was substantial, disclose it in the PR description.
- Do not post unreviewed AI-generated responses as review replies.

## 6) Pull request requirements

Each PR should include:

- Why this change is needed
- What changed and what did not change
- Security impact assessment
- Verification evidence (tests, logs, or benchmark data)
- Compatibility or migration notes (if relevant)
- Rollback/failure recovery notes (if relevant)

## 7) Security-related changes

Changes affecting policy evaluation, boundary enforcement, credential handling, memory protection, or audit integrity require:

- At least 2 maintainer approvals
- At least 1 security/compliance owner approval

See `SECURITY.md` for vulnerability reporting and disclosure process.

## 8) Code of conduct

All participation must follow `CODE_OF_CONDUCT.md`.

