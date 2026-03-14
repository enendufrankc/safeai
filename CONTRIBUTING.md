# Contributing to SafeAI

Thanks for your interest in contributing to SafeAI. Contributions are welcome.

## 1) Ways to contribute

- Report bugs and edge cases
- Propose features and design improvements
- Improve docs and examples
- Contribute code and tests
- Review pull requests

## 2) Local development setup

### Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### First time setup

```bash
git clone https://github.com/enendufrankc/safeai.git
cd safeai
uv sync --extra dev --extra all
```

Or with pip:

```bash
pip install -e ".[dev,all]"
```

### Verify your setup

Run the full test suite:

```bash
uv run python -m pytest tests/ -v
```

Run linting and type checks:

```bash
uv run ruff check safeai tests
uv run mypy safeai
```

### Make a change

1. Create a branch: `git checkout -b my-fix`
2. Edit code under `safeai/`
3. Add or update tests under `tests/`
4. Run `uv run python -m pytest tests/ -v` to verify
5. Run `uv run ruff check safeai tests && uv run mypy safeai` to lint
6. Commit with sign-off: `git commit -s -m "Fix: description"`
7. Push and open a PR

### Common issues

- **Import errors after install**: Make sure you installed with `.[dev,all]` extras.
- **Type check failures**: Run `uv run mypy safeai` to see specific errors.
- **Ruff formatting**: Run `uv run ruff format safeai tests` to auto-fix style issues.

## 3) Start with an issue for larger changes

Before implementing substantial work, open an issue describing:

- Problem statement and use case
- Proposed approach
- Alternatives considered
- Risks (security, compatibility, performance)

Small fixes and documentation updates can be submitted directly as pull requests.

## 4) Development standards

- Add or update tests for behavioral changes.
- Keep changes focused and scoped to one concern.
- Update docs for user-visible or API/schema changes.
- Ensure required CI checks pass.

## 5) Commit and sign-off policy (DCO)

All commits must be signed off by a human author.
Use:

```bash
git commit -s -m "your message"
```

By signing off, you certify compliance with the Developer Certificate of Origin:
https://developercertificate.org/

## 6) AI-assisted contribution policy

AI tools are permitted with the following conditions:

- You are fully responsible for correctness, licensing, and security of submitted code.
- You must be able to explain your changes during review.
- If AI assistance was substantial, disclose it in the PR description.
- Do not post unreviewed AI-generated responses as review replies.

## 7) Pull request requirements

Each PR should include:

- Why this change is needed
- What changed and what did not change
- Security impact assessment
- Verification evidence (tests, logs, or benchmark data)
- Compatibility or migration notes (if relevant)
- Rollback/failure recovery notes (if relevant)

## 8) Security-related changes

Changes affecting policy evaluation, boundary enforcement, credential handling, memory protection, or audit integrity require:

- At least 2 maintainer approvals
- At least 1 security/compliance owner approval

See `SECURITY.md` for vulnerability reporting and disclosure process.

## 9) Response expectations

We aim to respond within these targets:

- **Issues**: Within 1 week
- **Security reports**: Within 48 hours (see `SECURITY.md`)
- **PRs from maintainers**: Within 3 business days
- **PRs from the community**: Within 1–2 weeks

SafeAI is maintained by volunteers. Response times may be longer during busy periods. If a PR has had no response after 2 weeks, feel free to leave a polite ping.

## 10) Code of conduct

All participation must follow `CODE_OF_CONDUCT.md`.

