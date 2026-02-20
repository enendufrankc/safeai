# SafeAI: personas and user journeys

## Persona 1: Alex, the AI product engineer

Role: Senior backend engineer at a mid-stage startup
Team size: 8 engineers
Context: Building an AI-powered customer support agent that reads account data, drafts emails, and escalates issues

### Profile

Alex ships fast. The startup's support agent handles thousands of conversations daily, pulling from customer databases, internal knowledge bases, and billing systems. The agent works well, but Alex keeps getting asked by the VP of Engineering: "What happens if it leaks a customer's payment info?"

Alex has tried adding safety prompts, but they drift with model updates. Manual reviews don't scale. Alex needs something that enforces security without slowing the team down or requiring prompt gymnastics.

### Goals
- Deploy agents safely without rewriting business logic
- Pass security reviews without becoming a security expert
- Keep development velocity high

### Frustrations
- Prompt-based safety is fragile and hard to test
- No standard way to scope agent permissions
- Security concerns slow down feature launches
- Every framework handles safety differently

### Journey with SafeAI

1. Discovery: Alex reads about SafeAI on GitHub after another agent leak hits the news
2. Evaluation: Installs the Python SDK. Wraps the existing tool dispatcher in SafeAI middleware. Takes 30 minutes.
3. First value: Input scanner catches a customer pasting their full credit card number in chat. Redacted before the model sees it.
4. Configuration: Alex writes 5 policies: no personal data in outputs, no raw DB fields passed to the model, email sending requires approval, memory limited to session scope, audit logging enabled.
5. Integration: The security team reviews the policies (readable YAML, not code). They approve without needing to understand the agent internals.
6. Ongoing: Alex adds new tools and capabilities over time. Each one gets a contract. SafeAI enforces the contract automatically.

### Key quote
"I just want to build features. SafeAI lets me do that without worrying about what the agent might accidentally expose."

---

## Persona 2: Maria, the enterprise security lead

Role: Director of Application Security at a financial services company
Team size: 12 security engineers supporting 200+ developers
Context: Multiple teams are deploying AI agents across customer service, internal HR, and financial analysis

### Profile

Maria has spent 15 years building security programs. She understands that AI agents are just software, but software with unusually broad access and unpredictable behavior. Her board asks quarterly about AI risk. Regulators are starting to ask questions about AI data handling.

Maria needs visibility, control, and auditability across every AI deployment in the organization. She does not want to review every prompt or understand every model. She wants deterministic controls she can verify and explain.

### Goals
- Enforce consistent AI security policies across all teams
- Provide audit trails that satisfy regulators
- Prevent cross-user and cross-tenant data leakage
- Avoid becoming a bottleneck for AI feature development

### Frustrations
- Each team handles AI safety differently
- No centralized visibility into what agents access
- Existing DLP tools flag too many false positives for AI interactions
- Compliance reporting for AI is manual and painful

### Journey with SafeAI

1. Discovery: Maria's team evaluates SafeAI after an internal agent accidentally includes another customer's account summary in a response.
2. Pilot: Deploys SafeAI as a gateway for one team's customer service agent. Immediate visibility into data flows.
3. Policy design: Works with compliance to write organization-wide policies covering personal data handling, secret management, and approval requirements for irreversible actions.
4. Rollout: Deploys SafeAI as a centralized gateway. All AI agent traffic routes through it. Teams don't change their code, they change their routing.
5. Audit: Generates compliance reports directly from SafeAI audit logs. Shows regulators exactly what data each agent accessed, what was blocked, and why.
6. Governance: Establishes a policy review cadence. New AI deployments must declare tool contracts before going to production.

### Key quote
"I don't need to understand how the AI thinks. I need to know what it touched, what it sent, and whether it followed the rules."

---

## Persona 3: Jordan, the solo developer

Role: Independent developer building AI-powered tools as a solo founder
Team size: 1
Context: Building a personal AI assistant that manages email, calendar, and cloud deployments

### Profile

Jordan is building an AI assistant that connects to Gmail, Google Calendar, AWS, and Notion. The assistant is powerful: it can draft emails, schedule meetings, and deploy code. Jordan uses it daily.

But Jordan is increasingly uneasy. The assistant has API keys for everything. If the model hallucinates or a prompt injection slips through, it could send an email to the wrong person or deploy to production accidentally. Jordan wants guardrails but doesn't have a security team.

### Goals
- Protect personal and client credentials
- Prevent accidental irreversible actions
- Keep setup simple, no enterprise complexity

### Frustrations
- Giving an AI agent full API access feels dangerous
- No simple way to add approval gates for risky actions
- Secret management for personal projects is tedious
- Hard to know what the agent actually did after the fact

### Journey with SafeAI

1. Discovery: Finds SafeAI while searching for "how to secure AI agent API keys"
2. Setup: Installs the Python package. Wraps tool calls in SafeAI middleware. 20 minutes.
3. First win: Configures production deployments to require approval. The assistant can still suggest deployments but can't execute without Jordan clicking "approve."
4. Secret handling: Moves API keys into SafeAI's ephemeral credential system. The assistant never sees raw keys, it just calls capabilities.
5. Peace of mind: Checks the audit log occasionally. Sees exactly what the assistant did, what tools it called, what data it accessed. No surprises.

### Key quote
"I'm one person. I can't review every action my AI takes. SafeAI is like having a security engineer on autopilot."

---

## Persona 4: Priya, the framework maintainer

Role: Maintainer of an open-source agent framework
Team size: Core team of 5, community of 500+ contributors
Context: Users of the framework keep reporting security concerns about agent data handling

### Profile

Priya maintains a popular open-source agent framework. Every week, someone opens an issue about data leakage, memory persistence, or tool permission concerns. The framework wasn't designed with security as a first-class concern, and bolting it on retroactively is fragile.

Priya needs a solution the framework can recommend or integrate without owning the security surface area.

### Goals
- Give framework users a clear security story
- Avoid building and maintaining security features in-house
- Maintain framework neutrality, not lock into one security vendor
- Reduce security-related issues and complaints

### Frustrations
- Security is not the framework's core competency
- Every custom security solution adds maintenance burden
- Users expect security but don't want to configure it
- No industry standard for agent security

### Journey with SafeAI

1. Discovery: Evaluates SafeAI as a recommended security layer after persistent community feedback
2. Integration: Adds SafeAI as an optional middleware in the framework's tool execution pipeline. A few lines of code.
3. Documentation: Links to SafeAI's docs for security configuration. The framework's own docs stay focused on agent capabilities.
4. Community response: Security-related issues drop significantly. Users who care about security adopt SafeAI. Users who don't are unaffected.
5. Standard: SafeAI's policy format becomes the de facto way the community describes agent security requirements.

### Key quote
"We build the engine. SafeAI builds the seatbelts. Our users get both."

---

## User journey summary

| Stage | Alex (Engineer) | Maria (Security) | Jordan (Indie) | Priya (Maintainer) |
|-------|----------------|------------------|----------------|---------------------|
| Discover | GitHub / news | Internal incident | Search | Community feedback |
| Evaluate | SDK install, 30 min | Gateway pilot, 1 team | pip install, 20 min | Middleware test |
| First value | Input redaction | Data flow visibility | Approval gates | Issue reduction |
| Expand | More policies + tools | Org-wide gateway | Secret management | Community adoption |
| Steady state | Ship features safely | Compliance reporting | Audit log reviews | Recommended stack |

## Common thread

All four personas share the same underlying need: make AI behavior predictable without sacrificing capability. The difference is scale and context, but the enforcement mechanism is identical.
