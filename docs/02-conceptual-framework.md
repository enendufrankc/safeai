# SafeAI: conceptual framework

## The mental model

SafeAI is to AI agents what API gateways and service meshes are to microservices: a control plane that enforces policy at runtime without modifying the services it protects.

Every AI interaction, whether a chatbot conversation, an agent calling a tool, or two agents communicating, involves data crossing a boundary. SafeAI intercepts those boundary crossings and enforces rules before data passes through.

The agent keeps its intelligence. SafeAI keeps its boundaries.

## The three boundaries

All AI systems, regardless of framework, model, or architecture, have exactly three boundary points where data can leak or be misused.

### Boundary 1: Input

Data entering the AI system, including user messages, uploaded files, voice input, images, and context from other systems.

Risk: Users accidentally share credentials, personal data, or confidential documents. Upstream systems inject more context than the agent needs.

SafeAI classifies, tags, and filters data before the AI processes it. Sensitive content that violates policy is redacted or blocked. The agent never sees what it should not have.

### Boundary 2: Action

The AI system calling tools, accessing data stores, communicating with other agents, or performing real-world actions.

Risk: Agents access data beyond their scope, call tools with excessive permissions, share context between users or sessions, or trigger irreversible actions without authorization.

SafeAI validates every tool call against capability policies. Unauthorized fields are stripped from tool responses. Scoped, temporary credential access is enforced. Irreversible actions are gated behind human approval.

### Boundary 3: Output

Data leaving the AI system, including responses to users, emails, API calls, file writes, and messages to other agents.

Risk: Responses contain personal data, internal metadata, secrets, or information from other users. Actions affect the wrong recipient or exceed intended scope.

SafeAI scans outputs for policy violations. Responses containing unauthorized data are redacted, blocked, or replaced. Every output decision is logged for audit.

## Core concepts

### Data tags

Every piece of data flowing through SafeAI receives a classification tag:

| Tag | Description | Example |
|-----|-------------|---------|
| `public` | Safe for any audience | Marketing copy, public docs |
| `internal` | Safe within the organization | Internal KB articles, team notes |
| `confidential` | Restricted by role or policy | Financial reports, strategy docs |
| `personal` | Subject to privacy regulation | Names, emails, addresses, health data |
| `secret` | Never exposed to agents | API keys, passwords, tokens |

Tags travel with data across boundaries. Policies reference tags, not raw content. This decouples security logic from business logic.

### Policies

Policies are declarative rules that define what is allowed at each boundary. They are external to agent code and apply consistently across all agents.

A policy answers three questions:
1. What data type is involved? (tag-based)
2. What boundary is being crossed? (input, action, output)
3. What should happen? (allow, redact, block, require approval)

Example policy (conceptual):

```yaml
- boundary: output
  data_tag: personal
  action: redact
  reason: "Personal data must not appear in agent responses"

- boundary: action
  tool: send_email
  data_tag: confidential
  action: require_approval
  reason: "Confidential data in emails requires human sign-off"
```

Policies are simple enough for security teams to write and review without understanding agent internals.

### Capabilities

Agents do not own secrets or permissions. They are granted temporary, scoped capabilities.

A capability defines:
- What the agent can do (which tool, which action)
- With what data (which tags are allowed)
- For how long (time-limited access)
- Under what conditions (approval required, intent binding)

This is the principle of least privilege applied to AI. Instead of giving an agent an AWS key, you grant it a "deploy to staging" capability that expires in 10 minutes and only works for a specific service.

### Tool contracts

Every tool integrated with SafeAI declares a contract:

- Accepts: what data types it receives
- Emits: what data types it returns
- Stores: what it persists, and for how long
- Side effects: what irreversible actions it can trigger

SafeAI enforces these contracts at runtime. If a tool returns data outside its declared contract, the extra data is stripped. If a tool tries to accept restricted data, the call is blocked.

### Memory schema

Agent memory is not free-form. SafeAI replaces uncontrolled memory with schema-based storage:

- Only fields in the allow-list can be written
- Retention rules define how long data persists
- Sensitive data is stored as references (handles), not values
- Raw conversation logs are never persisted by default

This prevents the "memory hoarding" problem where agents accumulate sensitive data indefinitely.

### Trust boundaries

Every interaction between different principals is a trust boundary:

- User to agent
- Agent to tool
- Agent to agent
- Agent to memory
- Agent to external service

SafeAI treats each boundary independently. Data flowing from Agent A to Agent B passes through the same enforcement as data flowing from a user to an agent. This prevents cascading leaks in multi-agent systems.

## How SafeAI differs from existing approaches

| Approach | How it works | Limitation |
|----------|-------------|------------|
| Prompt-based safety | Safety rules injected into prompts | Drift, jailbreaks, model-dependent |
| Framework guardrails | Built into specific agent frameworks | Framework lock-in, inconsistent |
| Enterprise DLP | Scans text for sensitive patterns | Not AI-aware, high false positives |
| AI security platforms | Vendor-managed safety layers | Heavy, expensive, opaque |
| SafeAI | Boundary enforcement via policies | Does not control agent reasoning |

SafeAI's limitation is also its strength: it deliberately does not try to control how agents think. It controls what they can access and what they can do.

## The layered defense model

SafeAI is one layer in a defense-in-depth strategy:

```
Layer 1: Network security       (firewall, VPN, network policies)
Layer 2: Identity and access    (auth, RBAC, identity providers)
Layer 3: SafeAI                 (AI boundary enforcement)
Layer 4: Application logic      (agent code, business rules)
Layer 5: Model behavior         (RLHF, system prompts, fine-tuning)
```

SafeAI occupies Layer 3, between infrastructure security and application logic. It does not replace network security or identity management. It adds the AI-specific enforcement layer that traditional security stacks lack.

## The core insight

The agent cannot leak what it never received.
The agent cannot misuse what it was never granted.
The agent cannot hide what was always logged.

That is the conceptual core of SafeAI.
