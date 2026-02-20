# SafeAI

A universal, open security and privacy control layer that makes AI interactions predictable, auditable, and controlled, without touching how AI thinks or performs.

---

## The problem

AI agents have moved from demos to production. Teams are deploying agents that read customer records, call APIs, send emails, deploy infrastructure, and talk to other agents. The capabilities are real. So are the failures.

Today's AI systems are unsafe by default. They over-share, over-remember, act with excessive privilege, and produce no audit trail. Existing mitigations — prompt rules, framework-specific guardrails — don't transfer across stacks and don't hold up under scrutiny from security teams.

Real incidents happening now:
- Agents exposed to the open internet with full system access, discovered by security researchers in the tens of thousands
- Infostealer malware extracting gateway tokens and agent config files from developer machines
- AI platforms leaking millions of API keys and private messages through misconfigured backends
- Crafted inputs triggering agents to exfiltrate databases and cloud credentials

The industry response has been fragmented. SafeAI is a structural fix.

---

## The solution

SafeAI is a runtime control layer. It sits at the boundaries of AI interactions and enforces policies on what data goes in, what actions are permitted, and what comes out. It does not touch agent reasoning, model internals, or prompt logic.

```
User / App
    │
    ▼
┌─────────────────────────────┐
│         SafeAI Layer        │
│  ┌─────────────────────┐    │
│  │  Input Scanner      │    │  ← Classify and redact sensitive data before the model sees it
│  ├─────────────────────┤    │
│  │  Policy Engine      │    │  ← Declarative allow/deny rules for data, tools, and actions
│  ├─────────────────────┤    │
│  │  Tool Interceptor   │    │  ← Validate tool calls; strip unauthorized fields from responses
│  ├─────────────────────┤    │
│  │  Memory Controller  │    │  ← Schema-bound, session-scoped memory; secrets never stored
│  ├─────────────────────┤    │
│  │  Capability Grants  │    │  ← Ephemeral, scoped credentials; agents borrow, never own secrets
│  ├─────────────────────┤    │
│  │  Approval Gate      │    │  ← Human review only for high-risk, irreversible actions
│  ├─────────────────────┤    │
│  │  Audit Logger       │    │  ← Every decision, access, and block logged for compliance
│  └─────────────────────┘    │
└─────────────────────────────┘
    │
    ▼
AI Agent / Model / Framework
```

---

## Core principles

**Security at boundaries, not inside prompts.** AI reasoning is probabilistic. Security must be deterministic. SafeAI controls what data enters and exits and what actions are permitted. It does not try to make models reason about safety, because that doesn't hold across models or contexts.

**Least privilege by default.** Agents only see and do what policy explicitly allows, for as short a time as possible. What is not allowed does not exist from the agent's perspective. An agent cannot leak what it never received.

**Deterministic over clever.** Explicit rules over heuristics. Schemas over free-text analysis. Data tags over guesswork. When something is blocked, the reason is logged and auditable.

**Invisible when things go right.** Most requests pass silently. The system intervenes only when a boundary is crossed. That silence is the point — users and developers should forget SafeAI is there until the moment it matters.

**Framework and model agnostic.** Works with any AI stack, agent framework, or third-party API. Models change. Boundaries hold.

---

## Key capabilities

| Capability | Description |
|---|---|
| Input boundary scanner | Intercepts all input, classifies sensitive data, redacts or blocks it before the model processes it |
| Policy engine | Declarative YAML rules for data access, tool use, and approvals, external to agent code |
| Data classification | Lightweight, persistent tagging: `public`, `personal`, `confidential`, `secret` |
| Tool call interceptor | Validates tool calls against declared contracts; strips unauthorized fields from responses |
| Memory controller | Schema-bound, allow-listed, session-scoped memory; secrets are never persisted |
| Capability-based access | Agents receive ephemeral, scoped credentials per task; no long-lived secrets in agent context |
| Human approval gate | Triggered only for high-risk, irreversible actions; not for routine interactions |
| Audit logger | Every decision, access, redaction, and block is logged for compliance and forensic review |

---

## What SafeAI is not

SafeAI is boundary enforcement infrastructure. It is not an agent framework, a prompt engineering tool, a content moderation system, or a replacement for authentication and IAM. It assumes the agent is doing its job and ensures that job stays within defined limits.

---

## Design inspirations

These are proven patterns from traditional infrastructure, applied to a new execution model:

| Inspiration | What we borrowed |
|---|---|
| Open Policy Agent | Declarative, external policy as the source of truth |
| Envoy / Service Mesh | Sidecar enforcement at the boundary, transparent to the application |
| HashiCorp Vault | Ephemeral, scoped secrets; credentials issued per task, not stored |
| Kubernetes Admission Controllers | Validation at the point of execution, before action is taken |

---

## Integration modes

**Sidecar / Gateway.** Deploy alongside any AI service. Intercepts all traffic at the network boundary. No changes to agent code required.

**SDK / Middleware.** Embed directly into your application. Policy files drive behavior; the SDK provides the enforcement hooks.

**Client-side proxy.** For users of third-party AI APIs. Intercepts and enforces policies locally before data leaves the machine.

---

## Open source approach

The enforcement engine and policy evaluation logic are fully open source. Security comes from architecture, not obscurity.

- Default policy is deny all
- Policies and secrets are environment-specific and never committed to the repo
- Anyone can audit how decisions are made
- Enterprise features extend the open core without replacing it

---

## How you know it's working

Most interactions should pass with no intervention. If you're seeing frequent blocks or approvals on routine requests, policy is probably misconfigured, not too strict.

More concretely: a security engineer should be able to open the audit log, pick any blocked request, and explain within a minute exactly which rule triggered and why. If they can't, the logging isn't detailed enough or the policy is too clever.

---

## Documentation

| Document | Description |
|---|---|
| [Vision & Philosophy](./01-vision-and-philosophy.md) | Core principles and motivation |
| [Conceptual Framework](./02-conceptual-framework.md) | Architecture concepts and mental models |
| [Personas & User Journeys](./03-personas-and-user-journeys.md) | Who uses SafeAI and how |
| [Product Requirements](./04-product-requirements.md) | Functional and non-functional requirements |
| [Feature Specification](./05-feature-specification.md) | Detailed feature specs with acceptance criteria |
| [UX/UI Design](./06-ux-ui-design.md) | Interface design and developer experience |
| [System Design](./07-system-design.md) | Architecture and component design |
| [Technology & Data Design](./08-technology-and-data-design.md) | Tech stack and data model |
| [Compliance & Governance](./09-compliance-and-governance.md) | Regulatory alignment and governance model |
| [Product Roadmap](./10-product-roadmap.md) | Phased delivery plan |
| [Go-to-Market Strategy](./11-go-to-market-strategy.md) | Target segments and launch strategy |
| [Lean Startup Docs](./12-lean-startup-docs.md) | Hypothesis, experiments, and learning |
| [Business Plan & Pitch](./13-business-plan-and-pitch.md) | Business model and investor narrative |
| [Delivery Tracker](./15-delivery-tracker.md) | Single source of truth for implementation status and next tasks |
| [Architecture Review 2026-02-20](./16-architecture-review-2026-02-20.md) | Sprint 0 architecture review record and decisions |
| [Quickstart](./17-quickstart.md) | Install-to-first-value guide with end-to-end SDK example |

---

## Status

Sprint 0 and Phase 1 are complete, with `v0.1.0rc1` prepared.
Current execution status and next tasks are tracked in `docs/15-delivery-tracker.md`.
