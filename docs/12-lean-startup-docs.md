# SafeAI lean startup documents

## Part 1: Problem validation

### Problem statement

AI agents are being deployed in production with insufficient security controls. Teams face a choice between slowing down to manually manage safety or accepting unquantified risk of data leakage, credential exposure, and compliance violations.

### Problem evidence

Market signals:
- Public incidents: agent platforms exposing user data, leaked API keys, credential theft through agent config files
- Industry bans: major tech companies banning specific agent platforms over security concerns
- Regulatory pressure: EU AI Act, GDPR enforcement actions increasingly touching AI data handling
- Community discussions: active threads on Reddit, X, and security forums about AI agent risks

User research signals (to validate):
- Engineers spend time writing ad-hoc safety prompts that don't scale
- Security teams have no visibility into what agents access
- Companies delay AI agent deployments due to security uncertainty
- No standard exists for AI agent security policies

### Assumptions to validate

| # | Assumption | Validation method | Status |
|---|-----------|-------------------|--------|
| A1 | Engineers want security controls they can integrate in < 1 hour | Landing page + sign-up conversion rate | To validate |
| A2 | Teams currently rely on prompt-based safety that they know is fragile | User interviews (5-10 AI product engineers) | To validate |
| A3 | Security teams need audit trails for AI agent activity | User interviews (3-5 security leads) | To validate |
| A4 | Developers prefer open-source security tools they can inspect | GitHub adoption metrics + survey | To validate |
| A5 | Boundary-based enforcement is sufficient to prevent most common leaks | Technical testing with real-world leak scenarios | To validate |

### Problem validation plan

Week 1-2: interviews
- Talk to 10 people building AI agents in production
- Ask: What is your current approach to agent security? What breaks?
- Ask: If I could add security to your agent in 30 minutes, what would it need to do?
- Ask: What would make you trust an agent enough to give it access to customer data?

Week 3: landing page test
- Simple landing page: problem statement + solution summary + "Get early access" signup
- Drive traffic from relevant communities (Reddit, HN, Twitter/X)
- Measure: signup rate, comments, questions asked

Week 4: technical validation
- Build a minimal prototype (input scanner + output guard + policy engine)
- Test against 10 common AI agent data leak patterns
- Measure: detection rate, false positive rate, latency overhead

### Pivot triggers
- If < 5% of landing page visitors sign up, the problem framing needs work
- If interviews reveal teams already have satisfactory solutions, pivot to a different pain point
- If detection rate < 80% for common patterns, rethink the classification approach

---

## Part 2: MVP definition

### MVP scope

The minimum viable product is a Python SDK that a developer can install, configure in under 30 minutes, and immediately get protection against the most common data leakage patterns.

### What's in the MVP

| Component | Included | Rationale |
|-----------|----------|-----------|
| Input scanner with PII detectors | Yes | Catches the most common leakage source |
| Output guard with redaction | Yes | Prevents data from reaching users |
| YAML policy engine | Yes | Enables customization without code changes |
| Memory schema enforcement | Yes | Prevents unbounded data accumulation |
| Audit logging (stdout/file) | Yes | Basic accountability |
| CLI: init, scan, validate | Yes | Developer experience essentials |
| Default policy starter set | Yes | Reduces time to first value |

### What's not in the MVP

| Component | Excluded | Why |
|-----------|----------|-----|
| Tool call interception | Phase 2 | Requires framework-specific adapters |
| Secret/credential management | Phase 3 | Separate concern, adds complexity |
| Human approval workflows | Phase 3 | Requires UI/notification infrastructure |
| HTTP proxy/gateway mode | Phase 4 | SDK mode is sufficient for initial users |
| Web dashboard | Phase 5 | Premature for developer-first adoption |
| Framework-specific adapters | Phase 2 | Generic wrapping works first |

### MVP user flow

```
1. pip install safeai
2. cd my-agent-project
3. safeai init  →  generates config files
4. Edit policies/default.yaml (or use defaults)
5. Add 3 lines of code to wrap agent I/O
6. Run agent  →  SafeAI silently protects
7. safeai logs  →  see what happened
```

### MVP success metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Time to integrate | < 30 minutes | Timed user tests |
| Detection accuracy | > 90% for built-in patterns | Test suite against known PII patterns |
| False positive rate | < 5% | User-reported issues |
| Latency overhead | < 20ms per check | Benchmark suite |
| User satisfaction | "Would recommend" > 70% | Post-install survey |

### MVP build plan

| Week | Focus | Deliverable |
|------|-------|-------------|
| 1 | Core engine | Classifier, policy engine, scanner skeleton |
| 2 | Detectors + output guard | Built-in PII detectors, output scanning |
| 3 | Memory + CLI + config | Memory controller, CLI tools, YAML config |
| 4 | Testing + docs + release | Test suite, quick start guide, PyPI publish |

---

## Part 3: Learning log

### Template for ongoing learning

Each validated or invalidated assumption gets an entry:

```
Date: YYYY-MM-DD
Assumption: [A#] [description]
Experiment: [what we did]
Result: [what we observed]
Conclusion: [validated / invalidated / needs more data]
Action: [what we changed based on this learning]
```

### Pre-launch learnings

```
Date: 2026-02-19
Assumption: The AI agent security problem is real and urgent
Experiment: Market research — public incidents, community discussions, regulatory trends
Result: Multiple public incidents in past 30 days. Active community concern. Regulatory attention increasing.
Conclusion: Validated (strong signal)
Action: Proceed with product development. Problem is real and timely.
```

```
Date: 2026-02-19
Assumption: Boundary-based enforcement is architecturally sound
Experiment: Analysis of successful infrastructure security products (Envoy, OPA, Vault, OAuth)
Result: All use boundary enforcement successfully. Pattern is well-established in infra security.
Conclusion: Validated (by analogy)
Action: Model SafeAI after these proven patterns. Treat as infrastructure, not AI product.
```

```
Date: 2026-02-19
Assumption: Open source is the right distribution strategy
Experiment: Analysis of the competitive field and target user preferences
Result: Enterprise vendors exist but are heavy and opaque. No open standard. Developer tools win through adoption, not sales.
Conclusion: Validated (strong fit for category)
Action: Build open-source first. Commercial tiers for operational features, not core security.
```

### Learning cadence
- Weekly: review metrics and user feedback
- Bi-weekly: update assumption status
- Monthly: review pivot triggers and strategic direction
- Quarterly: full learning retrospective

### Questions to answer in the first 90 days
1. Do developers actually integrate SafeAI, or just star the repo?
2. Which detectors catch the most real issues? Which are noise?
3. Is SDK mode sufficient, or do users immediately ask for proxy mode?
4. What policies do users write first? (Tells us what they fear most.)
5. Are security teams or engineering teams the primary champion?
