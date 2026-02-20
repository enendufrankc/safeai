## Summary

Describe the problem and fix in 2-5 bullets:

- Problem:
- Why it matters:
- What changed:
- What did not change (scope boundary):

## Change Type

- [ ] Bug fix
- [ ] Feature
- [ ] Refactor
- [ ] Docs
- [ ] Security hardening
- [ ] CI/infra

## Scope

- [ ] Core runtime (classifier/policy/scanner/interceptor/guard)
- [ ] SDK or middleware adapters
- [ ] CLI
- [ ] Policy schema/contracts/memory schema
- [ ] Audit/observability
- [ ] Docs/examples
- [ ] CI/CD

## Linked Work

- Closes #
- Related #

## User-visible or Behavior Changes

List user-visible behavior changes, defaults, or config impacts.
If none, write `None`.

## Security Impact (required)

- New permissions/capabilities? (`Yes/No`)
- Secrets/credential handling changed? (`Yes/No`)
- Boundary enforcement behavior changed? (`Yes/No`)
- Data access scope changed? (`Yes/No`)
- Audit logging behavior changed? (`Yes/No`)
- If any answer is `Yes`, describe risk and mitigation:

## Verification

### What was tested

- Unit tests:
- Integration tests:
- Manual validation:
- Benchmark/perf checks (if relevant):

### Evidence

Attach at least one:

- [ ] Failing test/log before + passing after
- [ ] Test output snippets
- [ ] Benchmark numbers
- [ ] Screenshot/recording (for UX changes)

## Compatibility and Migration

- Backward compatible? (`Yes/No`)
- Schema/API/CLI breaking change? (`Yes/No`)
- Migration required? (`Yes/No`)
- If yes, exact migration steps:

## Rollback Plan

- Fast disable/revert path:
- Known bad symptoms to watch:

## Checklist

- [ ] I can explain and defend this change end-to-end.
- [ ] I added/updated tests for behavior changes.
- [ ] I updated docs for user-visible or API/schema changes.
- [ ] I assessed security impact and recorded it above.
- [ ] I confirmed scope is limited to one coherent change.

