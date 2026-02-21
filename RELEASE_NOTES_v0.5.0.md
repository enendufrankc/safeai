# SafeAI v0.5.0 Release Notes

Date: 2026-02-20  
Status: Phase 5 release gate passed

## Scope included

1. Dashboard backend services
- new dashboard API surface for overview, audit query, incidents, approvals, compliance reporting, tenant policy sets, and alerts
- endpoints integrated into proxy runtime for sidecar and gateway deployments

2. Dashboard frontend and approvals UI
- new web dashboard at `/dashboard`
- approval queue with approve/deny actions backed by policy-bound approval state
- incidents and operations summary views for security teams

3. Compliance reporting
- report generation endpoint with boundary/action/policy/agent summaries
- approval metrics, memory-retention evidence counts, and anomaly flags

4. RBAC and tenant isolation
- scoped dashboard users with role permissions
- tenant-scoped event and approval filtering
- admin controls for per-tenant policy set management

5. Alerting rules and channels
- file-backed alert rule definitions and evaluation runtime
- configurable filters, thresholds, and windows
- alert event sink to structured alert log file

6. Enterprise defaults and quality gates
- `safeai init` now scaffolds dashboard defaults (`tenants/policy-sets.yaml`, `alerts/default.yaml`)
- full Phase 5 integration suite added (`tests/test_dashboard_phase5.py`)

## Validation summary

- `ruff check safeai tests` passed.
- `mypy safeai` passed.
- `python3 -m unittest discover -s tests -v` passed (`93` tests).

## Packaging note

- Local wheel/sdist build remains blocked in this environment because `python3 -m build` requires module `build`, which is not installed locally.
- CI release should build artifacts in a controlled environment with build dependencies available.
