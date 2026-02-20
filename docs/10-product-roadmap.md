# SafeAI: product roadmap

## Roadmap philosophy

Ship the smallest useful thing first. Expand based on real user feedback, not speculation. Every release should make SafeAI more useful without making it harder to operate.

---

## Phase 1: Foundation (weeks 1-4)

Theme: Core engine that works as a Python SDK

Goal: A developer can `pip install safeai`, wrap their agent's tool calls, and get immediate protection against the most common data leakage patterns.

### Deliverables

| Feature | Description | Priority |
|---------|-------------|----------|
| Input scanner | Text classification with built-in PII detectors (email, phone, SSN, credit card, API keys) | P0 |
| Output guard | Scan agent responses, redact or block sensitive data | P0 |
| Policy engine | YAML-based policies with default-deny posture | P0 |
| Data classifier | Regex-based detection with configurable patterns | P0 |
| Memory controller | Schema-based memory with allow-listed fields | P0 |
| Audit logger | Structured JSON logging to stdout/file | P0 |
| CLI: `safeai init` | Scaffold config files for a new project | P1 |
| CLI: `safeai scan` | Test inputs/outputs against policies | P1 |
| CLI: `safeai validate` | Validate policy and config files | P1 |
| Default policies | Starter policy set covering common safety rules | P1 |
| Documentation | Installation, quick start, first policy guide | P0 |

### Success criteria
- Developer integrates SafeAI in under 30 minutes
- Built-in detectors catch > 90% of common PII patterns
- Policy engine correctly evaluates all test cases
- < 20ms overhead per boundary check

### Exit criteria
- Published to PyPI
- README with quick start guide
- 10+ unit and integration tests passing
- At least one real agent integration example

---

## Phase 2: Tool control (weeks 5-8)

Theme: Control what agents can do, not just what they say

Goal: Developers can define tool contracts, intercept tool calls, and enforce capability-based access.

### Deliverables

| Feature | Description | Priority |
|---------|-------------|----------|
| Tool call interceptor | Intercept and validate tool calls against contracts | P0 |
| Tool contracts | YAML-based declarations of tool data boundaries | P0 |
| Response filtering | Strip unauthorized fields from tool responses | P0 |
| Agent identity | Assign IDs to agents for per-agent policy scoping | P1 |
| Framework adapters | LangChain middleware adapter | P1 |
| Custom classifiers | User-defined regex patterns in policy files | P1 |
| CLI: `safeai logs` | Query and display audit trail | P1 |

### Success criteria
- Tool calls are validated against contracts before execution
- Unauthorized response fields are stripped silently
- LangChain integration works with < 10 lines of code
- Audit trail captures all tool-related decisions

---

## Phase 3: Secrets and approvals (weeks 9-12)

Theme: Handle credentials safely and gate irreversible actions

Goal: Agents never touch raw secrets. High-risk actions require human approval.

### Deliverables

| Feature | Description | Priority |
|---------|-------------|----------|
| Capability-based credentials | Ephemeral secret injection with TTL | P0 |
| Secret backends | Environment variables, HashiCorp Vault integration | P0 |
| Human approval workflows | CLI-based approval for high-risk actions | P0 |
| Approval context | Show approvers what data and action are involved | P1 |
| Memory retention enforcement | Automatic purge of expired data | P1 |
| Encrypted memory handles | Sensitive fields stored as encrypted references | P1 |
| Framework adapters | Claude ADK, Google ADK adapters | P1 |

### Success criteria
- Secrets never appear in agent context, memory, or logs
- Approval workflow blocks irreversible actions until approved
- Capability tokens expire automatically after TTL
- At least two secret backends working

---

## Phase 4: Proxy and scale (weeks 13-18)

Theme: Deploy SafeAI as infrastructure, not just a library

Goal: SafeAI runs as a sidecar or gateway that any agent system can route through.

### Deliverables

| Feature | Description | Priority |
|---------|-------------|----------|
| HTTP proxy mode | FastAPI-based proxy for sidecar deployment | P0 |
| Gateway mode | Centralized proxy for multi-agent environments | P0 |
| Hot policy reload | Policy file changes take effect without restart | P0 |
| Agent-to-agent enforcement | Inter-agent messages treated as trust boundaries | P1 |
| Health checks | `/health` endpoint with component status | P1 |
| Prometheus metrics | Request counts, decision distribution, latency | P1 |
| OpenTelemetry traces | Per-boundary-crossing trace spans | P2 |

### Success criteria
- Proxy mode adds < 50ms latency p99
- Supports 1000+ requests/second on a single node
- Policy reload takes effect within 5 seconds
- Works with any language/framework via HTTP

---

## Phase 5: Dashboard and enterprise (weeks 19-26)

Theme: Give security teams visibility and control

Goal: Security teams manage policies, review audit trails, and approve actions through a web interface.

### Deliverables

| Feature | Description | Priority |
|---------|-------------|----------|
| Web dashboard | Overview, audit log search, policy management | P0 |
| Approval UI | Web-based approval workflow for high-risk actions | P0 |
| Compliance reports | Generate audit reports for specific time ranges | P1 |
| Multi-tenant policies | Separate policy sets per team or environment | P1 |
| Role-based access | Dashboard access control | P1 |
| Alerting rules | Configurable alerts on policy violation patterns | P1 |
| AWS Secrets Manager backend | Additional secret backend | P2 |

### Success criteria
- Security team can investigate incidents without engineering help
- Compliance reports satisfy SOC 2 and GDPR audit requirements
- Approval queue response time < 30 seconds
- Dashboard loads in < 2 seconds

---

## Phase 6: Ecosystem and community (weeks 27+)

Goal: Broad framework support, community contributions, and ecosystem growth.

### Deliverables

| Feature | Description | Priority |
|---------|-------------|----------|
| Plugin system | Community-contributed classifiers and backends | P1 |
| Additional framework adapters | CrewAI, AutoGen, custom frameworks | P1 |
| Structured data scanning | JSON/XML field-level classification | P1 |
| File and image scanning | Pre-process uploaded files and images | P2 |
| Voice/audio support | Redaction for speech-to-text pipelines | P2 |
| Browser extension | Client-side protection for third-party AI tools | P2 |
| Policy marketplace | Shared policy templates for industries (healthcare, finance, etc.) | P3 |

---

## Roadmap visualization

```
Week:  1    4    8    12   18   26   27+
       │────│────│────│────│────│────│───▶
       │ P1 │ P2 │ P3 │  P4   │ P5  │ P6
       │    │    │    │       │     │
       │Core│Tool│Sec │Proxy  │Dash │Eco
       │SDK │Ctrl│+Apv│+Scale │+Ent │sys
```

## Risk-adjusted timeline

| Phase | Optimistic | Realistic | Risk factor |
|-------|-----------|-----------|-------------|
| P1: Foundation | 3 weeks | 4 weeks | Low: well-defined scope |
| P2: Tool Control | 3 weeks | 4 weeks | Medium: framework adapter complexity |
| P3: Secrets/Approvals | 3 weeks | 4 weeks | Medium: secret backend integration |
| P4: Proxy/Scale | 4 weeks | 6 weeks | Medium: performance tuning |
| P5: Dashboard | 6 weeks | 8 weeks | High: UI/UX iteration |
| P6: Ecosystem | Ongoing | Ongoing | Community-dependent |

## Decision points

- After Phase 1: Is SDK-only mode sufficient for early users, or do they need proxy mode sooner?
- After Phase 3: Is the open-source engine ready for a managed cloud offering?
- After Phase 4: Is there demand for a commercial dashboard, or should it stay open-source?
- After Phase 5: Should a Go-based proxy be built for higher-throughput deployments?
