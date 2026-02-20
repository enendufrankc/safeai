# SafeAI business plan and pitch

## Executive summary

SafeAI is the open-source privacy and security control layer for AI agents. It sits underneath any AI framework and enforces data protection policies at the three boundary points where every agent interaction flows: input, action, and output.

AI agents are moving into production across industries, but they handle sensitive data with insufficient controls. Public incidents have shown agents leaking credentials, exposing personal data, and operating with excessive privileges. Existing solutions are either fragile (prompt-based safety), framework-locked (vendor guardrails), or heavy and expensive (enterprise platforms).

SafeAI solves this with a lightweight, framework-agnostic, deterministic enforcement layer. Open-source core for universal adoption. Commercial tiers for enterprise operations.

Business model: open-core. Free SDK and engine. Paid dashboard, managed gateway, and enterprise support.

Target market: AI product engineers (immediate) and enterprise security teams (expansion).

Traction target (Year 1): 5,000 GitHub stars, 1,000 active users, 10 enterprise pilots, $300K ARR from commercial tiers.

---

## The problem

AI agents are powerful but unsafe by default.

Data leakage is operational, not theoretical. Public incidents: agents exposing user data, infostealer malware extracting agent tokens, platforms leaking millions of API keys through misconfigurations.

Current solutions don't work. Prompt-based safety drifts with model updates. Framework-specific guardrails don't transfer. Manual reviews don't scale. Enterprise platforms are heavy, expensive, and opaque.

The gap is growing. Agent deployments are accelerating. Regulation is tightening (EU AI Act, GDPR enforcement). The number of tools and data sources agents access is expanding. Security controls are falling further behind.

Market pain indicator: major tech companies have banned specific agent platforms over security concerns. This is the clearest signal that the problem demands an industry-level solution.

---

## The solution

SafeAI is a runtime control layer that enforces privacy and security policies at the boundaries where AI agent data flows.

How it works:
- Input boundary: classify and filter data before the AI processes it
- Action boundary: validate tool calls against contracts, inject scoped credentials, gate risky actions
- Output boundary: scan responses, redact sensitive data, block policy violations

Properties:
- Framework-agnostic (LangChain, Claude ADK, Google ADK, custom stacks)
- Deterministic (rules-based, not heuristic)
- Lightweight (< 50ms overhead, no extra LLM calls)
- Open source (transparent, inspectable, community-driven)

The core insight: you don't need to make agents think safely. You need to make agents unable to access, store, or share data outside defined policies. The agent cannot leak what it never received.

---

## Market opportunity

### Total addressable market (TAM)

The AI infrastructure security market is projected to exceed $10B by 2028, driven by enterprise AI adoption, regulatory requirements, and agent proliferation.

### Serviceable addressable market (SAM)

AI agent security specifically — the intersection of agent frameworks, enterprise AI deployments, and AI-specific security tooling — represents an estimated $2-3B market by 2028.

### Serviceable obtainable market (SOM)

Year 1 target: $300K ARR from 10-20 enterprise customers using SafeAI Pro/Enterprise alongside a growing open-source user base.

Year 3 target: $5M ARR from 100+ enterprise customers, with the open-source engine as the de facto standard for AI agent security policies.

### Why now

1. Incidents are creating urgency. Companies can no longer defer AI agent security.
2. No open standard exists. The market is fragmented. First mover establishes the standard.
3. Agent adoption is accelerating. Every new agent deployment needs security controls.
4. Regulation is arriving. EU AI Act and GDPR enforcement create compliance requirements that SafeAI directly addresses.

---

## Business model

### Open-core model

| Tier | Price | Includes |
|------|-------|----------|
| Open source | Free | Core engine, SDK, CLI, policy engine, audit logging, framework adapters |
| SafeAI Pro | $500-2,000/month | Web dashboard, approval workflow UI, compliance reports, multi-tenant policies, priority support |
| SafeAI Enterprise | Custom ($5K-25K/month) | Managed gateway, SSO/RBAC, dedicated support, custom classifiers, on-premise, SLA |

### Revenue model
- Primary: subscription revenue from Pro and Enterprise tiers
- Secondary: professional services (custom classifier development, deployment support)
- Future: marketplace revenue share from community-contributed policy templates and plugins

### Why open-core works for this market
- Security teams trust what they can inspect, so open source drives adoption
- Developers adopt tools that are free and easy, so open source reduces CAC
- Enterprises pay for operational convenience, not features, so commercial tiers deliver value without gating security
- Community contributions improve detection quality, which reduces R&D burden

---

## Competitive advantage

### Competitive position

| Competitor | Approach | Weakness SafeAI exploits |
|-----------|----------|--------------------------|
| LangChain Guardrails | Framework-specific middleware | Only works with LangChain |
| NeMo Guardrails | NVIDIA's rail framework | Tied to NVIDIA ecosystem, prompt-based |
| HiddenLayer | Enterprise AI security platform | Heavy, expensive, closed source |
| Protect AI | ML model security | Focused on model attacks, not agent data flows |
| Generic DLP | Text pattern scanning | Not AI-aware, high false positives |

### SafeAI's moat

Open-source trust. Enterprise security teams prefer inspectable infrastructure. This is not a marketing claim — it's how the category works (Linux, Envoy, OPA).

Framework agnosticism. Multi-framework environments are the norm. Vendor-locked solutions cannot serve them.

Community-driven detection quality. More users bring more classifiers, which produces better detection, which attracts more users. Network effect on security quality.

Standard-setting potential. If SafeAI's policy format becomes the industry standard for AI agent security, switching costs rise naturally.

---

## Go-to-market

### Phase 1 (months 1-3): developer adoption
- GitHub launch, blog posts, community engagement
- Target: 500 stars, 50 active users

### Phase 2 (months 4-6): ecosystem
- Framework partnerships, integration guides, case studies
- Target: 2,000 stars, 200 active users

### Phase 3 (months 7-12): enterprise pipeline
- Launch Pro tier, enterprise pilots, security conference presence
- Target: 5,000 stars, 1,000 active users, 10 pilots, $300K ARR

### Customer acquisition cost (CAC) strategy
- Open source dramatically reduces CAC for the developer tier
- Enterprise CAC is funded by high contract values ($60K-300K/year)
- Content marketing and community presence replace expensive paid channels

---

## Team requirements

### Founding team (phases 1-2)
| Role | Focus |
|------|-------|
| Founder / lead engineer | Core engine, architecture, SDK |
| Security engineer | Classifiers, threat modeling, policy design |

### Expansion (phases 3-4)
| Role | Focus |
|------|-------|
| Backend engineer | Proxy mode, gateway, scaling |
| Frontend engineer | Dashboard, approval UI |
| Developer advocate | Community, docs, integrations |

### Phase 5+
| Role | Focus |
|------|-------|
| Sales engineer | Enterprise pilots and onboarding |
| Additional engineers | Platform features, enterprise requirements |

---

## Financial projections

### Year 1

| Quarter | Open-source users | Pro customers | Enterprise customers | MRR |
|---------|------------------|---------------|---------------------|-----|
| Q1 | 200 | 0 | 0 | $0 |
| Q2 | 500 | 5 | 0 | $5K |
| Q3 | 800 | 15 | 3 | $20K |
| Q4 | 1,200 | 25 | 7 | $50K |

Year 1 total: ~$300K ARR run rate by end of year

### Year 2-3

| Metric | Year 2 | Year 3 |
|--------|--------|--------|
| Open-source users | 5,000 | 15,000 |
| Pro customers | 100 | 300 |
| Enterprise customers | 25 | 75 |
| ARR | $1.5M | $5M |

### Cost structure (Year 1)

| Category | Annual | Notes |
|----------|--------|-------|
| Team (2 people) | $400K | Founder + security engineer |
| Infrastructure | $24K | CI/CD, hosting, cloud services |
| Marketing | $12K | Minimal, community-driven |
| Legal/Compliance | $10K | Open source licensing, security audit |
| Total | $446K | |

### Funding requirements
- Pre-seed/Seed: $500K-1M to reach $300K ARR and validate enterprise demand
- Series A trigger: $1M+ ARR, 25+ enterprise customers, proven open-source adoption flywheel

---

## Risk analysis

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Large vendor builds this in | Medium | High | Framework-agnostic position; multi-framework users always need us |
| Slow enterprise sales | Medium | Medium | Developer adoption first; enterprises follow developers |
| Open-source sustainability | Low | High | Commercial tiers fund development; lean team |
| Technical: classification accuracy | Medium | Medium | Community-contributed detectors; continuous improvement |
| Market timing too early | Low | Medium | Public incidents are creating demand now |

---

## The ask

### For investors
$500K-1M seed round to:
- Build and launch the open-source core (phases 1-2)
- Hire founding security engineer
- Reach 1,000 active users and 10 enterprise pilots within 12 months

### For early customers
- Free access to the open-source engine immediately
- Design partnership: shape the product to your needs
- Priority access to commercial features when they launch

### For contributors
- Open-source project with clear contribution guidelines
- Real impact: every improvement protects more AI deployments
- Community recognition and maintainer paths

---

## Closing statement

Every generation of computing infrastructure eventually gets its security layer. Networking got firewalls. APIs got gateways. Microservices got service meshes. Authentication got identity providers.

AI agents are next. SafeAI is that layer.

The question is not whether AI agents need boundary-based security. The question is whether we build the open standard before someone else ships the closed one.
