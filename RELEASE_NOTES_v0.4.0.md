# SafeAI v0.4.0 Release Notes

Date: 2026-02-20  
Status: Phase 4 release gate passed

## Scope included

1. Proxy boundary API surface
- full HTTP endpoints for input scan, output guard, tool interception, agent-message interception, memory read/write/resolve/purge, audit query, and policy reload
- endpoint behavior aligned with SDK boundary enforcement semantics

2. Upstream forwarding mode
- `/v1/proxy/forward` added for controlled upstream proxying
- request body pre-scanned with input policy checks
- upstream response post-processed through output guard before returning

3. Gateway mode enforcement
- sidecar/gateway runtime mode introduced
- gateway mode now requires source and destination agent IDs for action-forwarding paths
- agent-to-agent message enforcement added through API and proxy route

4. Observability and performance gates
- Prometheus-style metrics endpoint (`/v1/metrics`) with request counters, decision counters, and latency histograms
- Phase 4 integration tests for full proxy boundary behavior
- proxy regression benchmark tests for latency and throughput baselines

5. Developer operations
- `safeai serve` supports `--config`, `--mode`, and `--upstream-base-url`
- app metadata and package version updated for infrastructure release

## Validation summary

- `ruff check safeai tests` passed.
- `mypy safeai` passed.
- `python3 -m unittest discover -s tests -v` passed (`89` tests).

## Packaging note

- Local wheel/sdist build remains blocked in this environment because `python3 -m build` requires module `build`, which is not installed locally.
- CI release should build artifacts in a controlled environment with build dependencies available.
