# SafeAI Build Plan (Execution Blueprint)

## 1) Build objective

Build SafeAI as an open-source, framework-agnostic runtime security layer that ships in this order:

1. MVP Python SDK and CLI (input/output boundaries, policy engine, memory schema, audit logs)
2. Tool control and agent identity
3. Secret handling and approval workflows
4. Sidecar/gateway proxy and scale features
5. Dashboard and enterprise operations

This plan maps to:
- `SafeAI-docs/04-product-requirements.md`
- `SafeAI-docs/05-feature-specification.md`
- `SafeAI-docs/07-system-design.md`
- `SafeAI-docs/08-technology-and-data-design.md`
- `SafeAI-docs/10-product-roadmap.md`
- `SafeAI-docs/12-lean-startup-docs.md`

## 2) Planning assumptions

- Pre-kickoff governance and standards gate: February 23-27, 2026
- Formal engineering kickoff: Monday, March 2, 2026
- Primary language: Python 3.10+
- Team at kickoff: 2 engineers (lead engineer + security engineer)
- Build priority: SDK-first before proxy/dashboard
- Security posture: default deny, fail closed

## 3) Workstreams

Run these in parallel each sprint:

1. Core runtime
   - classifier, policy engine, scanner, output guard, interceptor, memory, audit
2. Developer experience
   - CLI, config scaffolding, examples, docs
3. Quality and security
   - unit/integration/perf/security tests, threat tests, dependency scanning
4. Release and operations
   - packaging, CI/CD, versioning, observability, release notes
5. Validation loop
   - user interviews, integration feedback, false-positive tuning

## 4) Phase-by-phase execution plan

| Phase | Dates | Goal | Must-ship deliverables | Exit gate |
|---|---|---|---|---|
| Pre-kickoff (OSS standards) | Feb 23-Feb 27, 2026 | Establish governance and trust baseline | governance docs, contribution policy, security disclosure policy, CI supply-chain checks, compatibility policy | governance gate approved; branch protection + required checks enabled |
| Sprint 0 | Mar 2-Mar 6, 2026 | Setup and architecture baseline | repo scaffold, package structure, CI, lint/test pipeline, schema skeletons, starter docs | CI green, baseline architecture review complete |
| Phase 1 (Foundation) | Mar 9-Apr 3, 2026 | Ship MVP SDK + CLI | input scanner, output guard, policy engine, memory schema enforcement, audit logging, `safeai init/scan/validate`, starter policies | PyPI release candidate, <20ms boundary checks (MVP path), integration in one real agent |
| Phase 2 (Tool control) | Apr 6-May 1, 2026 | Enforce action boundary | tool contracts, tool interceptor, response filtering, agent identity, `safeai logs`, LangChain adapter | tool calls blocked/allowed by contract + policy, full audit trail for action boundary |
| Phase 3 (Secrets + approvals) | May 4-May 29, 2026 | Prevent credential exposure and gate irreversible actions | capability tokens (TTL), env + Vault backends, CLI approval flow, memory retention purge, encrypted handles, Claude/Google ADK adapters | secrets never in prompts/memory/logs, approval workflow working in end-to-end tests |
| Phase 4 (Proxy + scale) | Jun 1-Jul 10, 2026 | Deploy as infrastructure | FastAPI proxy mode, gateway mode, hot policy reload, agent-to-agent enforcement, health endpoints, Prometheus metrics | <50ms p99 added latency, policy reload <=5s, load test target met |
| Phase 5 (Dashboard + enterprise) | Jul 13-Sep 4, 2026 | Security team operations | web dashboard, approval UI, compliance reports, RBAC, multi-tenant policy sets, alerting rules | security team can investigate incidents without engineering help |
| Phase 6 (Ecosystem) | Sep 2026+ | Expand adoption and integrations | plugin system, more framework adapters, structured/file scanning, policy templates | active external contributors and partner integrations |

## 5) Pre-kickoff OSS governance and standards plan

Deliver these before formal engineering kickoff:

1. Governance model
   - `GOVERNANCE.md` with decision rules and maintainer responsibilities
   - `MAINTAINERS.md` with area ownership and renewal expectations
2. Contribution and community standards
   - `CONTRIBUTING.md` with DCO/sign-off requirement (`git commit -s`)
   - `CODE_OF_CONDUCT.md`
   - issue and PR templates with required verification and security-impact sections
3. Security policy and disclosure process
   - `SECURITY.md` with private reporting path, response SLA, disclosure flow, and advisory channels
   - explicit out-of-scope list for invalid reports
4. Supply-chain and CI security baseline
   - least-privilege GitHub workflow permissions
   - pinned action versions/SHAs where practical
   - CodeQL, dependency updates, secret scanning, vulnerability scans
   - required status checks enabled on protected branches
5. Compatibility and standards contract
   - `COMPATIBILITY.md` for semver/deprecation/migration rules
   - versioned JSON Schemas for policy, tool contracts, and memory schema

Governance gate criteria:
- Core governance/security docs merged and discoverable from `README.md`
- PR/issue templates active
- branch protection and required checks active
- first compatibility contract published

## 6) Detailed MVP build plan (Phase 1)

### Week 1 (Mar 9-13): Core policy and data model
- Implement Pydantic models for policy, detections, decisions, audit event, memory schema.
- Implement policy loader/validator and deterministic evaluator (first-match + default deny).
- Implement classification taxonomy and tag hierarchy matching.
- Add unit tests for policy evaluation edge cases.

### Week 2 (Mar 16-20): Input and output boundaries
- Implement built-in detectors (email, phone, SSN, credit card, API key/token, URL creds).
- Implement input scanner pipeline (classify -> evaluate -> allow/redact/block).
- Implement output guard pipeline with configurable fallback templates.
- Add performance benchmarks for detector and policy path.

### Week 3 (Mar 23-27): Memory + audit + CLI
- Implement memory controller with schema validation and silent drop for disallowed fields.
- Implement structured JSON audit logger and local query interface.
- Implement `safeai init`, `safeai validate`, `safeai scan`.
- Generate starter project files (`safeai.yaml`, `policies/default.yaml`, `contracts/`, `schemas/`).

### Week 4 (Mar 30-Apr 3): Hardening and release
- Build integration tests for full request flow.
- Run false-positive and detection coverage test set.
- Write quick-start docs and one end-to-end example integration.
- Publish release candidate and cut `v0.1.0` after gate review.

## 7) Core dependency order (critical path)

1. Data models and policy engine
2. Classifier and detectors
3. Input/output components
4. Memory controller and audit logger
5. CLI and config scaffolding
6. Framework adapters
7. Proxy/gateway
8. Dashboard

Do not start proxy/dashboard before SDK core gates are green.

## 8) Release gates by maturity level

### MVP (`v0.1.0`)
- FR coverage: FR-1 to FR-5, FR-11 to FR-22, FR-26 to FR-29 (where applicable to MVP scope)
- Latency: <20ms typical boundary checks
- Accuracy: >90% on built-in detector suite
- False positive rate: <5% on validation corpus
- Usability: install-to-first-value under 30 minutes

### Tool control release (`v0.2.0`)
- Contract validation and response stripping fully enforced
- Agent identity and action-boundary audit events complete

### Secrets/approvals release (`v0.3.0`)
- No secrets in agent context/memory/logs verified by tests
- Approval flow required for irreversible actions

### Infrastructure release (`v0.4.0`)
- Sidecar/gateway mode stable
- p99 overhead and reload SLOs met in load tests

## 9) Definition of done (every sprint)

- Feature code merged with tests and docs in same PR set
- Security review completed for boundary/policy/secret logic changes
- Benchmarks rerun for touched boundary paths
- Changelog and migration notes updated
- Demo scenario recorded for sprint review

## 10) Immediate next actions (next 5 business days)

1. Add governance baseline files: `GOVERNANCE.md`, `MAINTAINERS.md`, `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`, `SECURITY.md`.
2. Add contribution ops templates: `.github/PULL_REQUEST_TEMPLATE.md` and issue forms (bug + feature).
3. Add CI security baseline: CodeQL, Dependabot, secrets scanning, vulnerability scanning, required-check workflow.
4. Publish `COMPATIBILITY.md` and initial JSON Schemas for policy/contracts/memory.
5. After governance gate passes, initialize repository skeleton from `SafeAI-docs/08-technology-and-data-design.md` and begin Sprint 0.
