# Required Status Checks (Branch Protection)

Apply these required checks to the protected `main` branch:

1. `Governance Gate / Required standards files`
2. `Governance Gate / Schema JSON validity`
3. `Quality Gate / Lint, type-check, tests, benchmarks (3.11)`
4. `Quality Gate / Lint, type-check, tests, benchmarks (3.12)`
5. `CodeQL / Analyze`
6. `Dependency Review / dependency-review`
7. `Secret Scan / gitleaks`

Notes:
- Exact check names may vary slightly by GitHub UI formatting.
- Update this file if workflow job names change.
