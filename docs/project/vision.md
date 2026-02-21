# Vision

## AI agents should feel safe and predictable

SafeAI exists because AI agents are becoming autonomous participants in production systems -- reading data, calling APIs, writing code, managing infrastructure -- and there is no standard way to enforce security boundaries around what they can see, do, and say.

SafeAI is the runtime boundary layer that makes AI agent systems safe by default.

---

## Why This Matters Now

The problem is not theoretical. Real incidents are already happening:

- Agents leaking API keys and credentials through model output.
- Autonomous coding tools executing destructive commands without review.
- Multi-agent systems passing sensitive data between agents with no access control.
- PII flowing through agent pipelines with no detection or redaction.

The industry response has been fragmented: each framework builds its own partial safety layer, each organization writes ad-hoc guardrails, and security teams are left to audit systems they cannot inspect.

SafeAI provides a single, framework-agnostic answer to all of these problems.

---

## Core Philosophy

### Security at the boundaries

Every piece of data in an agent system crosses a boundary: input (user to agent), action (agent to tool), or output (agent to user). SafeAI enforces policies at these three boundaries, covering the complete data flow.

### Least privilege by default

Agents start with no permissions and gain access only through explicit policy. Tool contracts, clearance tags, and capability tokens ensure agents can only do what they are authorized to do.

### Deterministic enforcement

Given the same input and policy, SafeAI always produces the same decision. There are no probabilistic filters, no ML-based classifiers in the enforcement path, and no non-deterministic behavior. Security decisions must be predictable.

### Invisible when working

SafeAI adds negligible latency and requires zero changes to agent application code when used through framework adapters. Developers should not feel the safety layer. It should simply be there, working.

### Framework-agnostic

SafeAI works with LangChain, CrewAI, AutoGen, Claude ADK, Google ADK, and any future framework. The core engine has zero framework dependencies. Adding support for a new framework means writing a thin adapter, not rebuilding the system.

### Open source

Security infrastructure must be inspectable. SafeAI is open source so that security teams can audit the enforcement engine, researchers can verify the boundary model, and the community can extend it with new detectors, adapters, and policy templates.

---

## The North Star

We want to reach a point where, when someone asks a team "How do you secure your AI agents?", the answer is:

> "We use SafeAI."

Not because it is the only option, but because it is the obvious one -- the way teams reach for well-established tools in other domains. A single runtime layer that handles detection, enforcement, auditing, and access control across every agent framework, every deployment model, and every compliance requirement.

That is the future we are building toward.
