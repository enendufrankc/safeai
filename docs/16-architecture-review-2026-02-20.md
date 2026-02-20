# SafeAI Architecture Review Record (Sprint 0)

Date: 2026-02-20
Review scope: Sprint 0 baseline architecture and Phase 1 readiness
Reviewers: SafeAI core team

## Decisions recorded

1. Enforcement model remains boundary-first and default-deny.
2. Policy evaluation remains deterministic (first-match by priority).
3. Policy files stay external to agent code and support hot reload.
4. Data tags use hierarchical matching (parent tag matches child tag).
5. Output guard supports policy-driven fallback templates for `block` and `redact`.
6. Memory writes are schema-bound with silent drop for disallowed/type-mismatched fields.
7. Memory retention is enforced by per-field/default retention durations and purge operations.
8. Audit data remains structured JSON with in-process query filtering for MVP.

## Interfaces approved

- SDK facade: `SafeAI.from_config`, `scan_input`, `guard_output`, `query_audit`, memory helpers.
- CLI baseline: `safeai init`, `safeai validate`, `safeai scan`, `safeai logs`, `safeai serve`.
- Config contracts:
  - policy schema: `schemas/v1alpha1/policy.schema.json`
  - memory schema: `schemas/v1alpha1/memory.schema.json`
  - tool contract schema: `schemas/v1alpha1/tool-contract.schema.json`

## Risks and mitigations

1. Risk: false positives from regex detectors.
   Mitigation: expose custom detector config and benchmark regression tests.
2. Risk: policy complexity drift.
   Mitigation: schema validation plus explicit priority ordering and tests.
3. Risk: audit log growth and query latency.
   Mitigation: keep query filters simple in MVP and add pluggable backends in Phase 2+.
4. Risk: performance regression with added validation.
   Mitigation: benchmark gate tests in CI and release criteria.

## Exit outcome

Architecture baseline is approved for Phase 1 completion and release-candidate preparation, with remaining work tracked in `docs/15-delivery-tracker.md`.
