# SafeAI: compliance and governance

## 1. Regulatory context

AI agent deployments touch multiple regulatory frameworks. SafeAI's boundary enforcement model supports compliance with these regulations by providing verifiable controls over data handling.

### Relevant regulations

| Regulation | Region | Relevance to SafeAI |
|-----------|--------|---------------------|
| GDPR | EU/EEA | Personal data processing, right to erasure, data minimization |
| CCPA/CPRA | California | Consumer data rights, disclosure requirements |
| HIPAA | US | Protected health information in AI interactions |
| SOC 2 | Global | Security controls, audit trails, access management |
| ISO 27001 | Global | Information security management |
| EU AI Act | EU | AI system transparency, risk management |
| PCI DSS | Global | Payment card data protection |
| NIST AI RMF | US | AI risk management framework |

## 2. How SafeAI supports compliance

### 2.1 Data minimization (GDPR Art. 5(1)(c), CCPA)

Requirement: Collect and process only the data necessary for the stated purpose.

SafeAI controls:
- Input scanner redacts unnecessary personal data before AI processing
- Tool contracts declare exactly what data each tool needs. Nothing more is passed.
- Memory schemas enforce allow-listed fields only. Agents cannot hoard data.
- Default-deny policies ensure agents only access what is explicitly permitted

Evidence provided: Audit logs show exactly what data was allowed, redacted, or blocked at every boundary crossing.

### 2.2 Right to erasure (GDPR Art. 17, CCPA)

Requirement: Delete personal data on request.

SafeAI controls:
- Memory controller enforces retention periods. Data expires automatically.
- Sensitive data is stored as handles, not raw values. Deletion is handle invalidation.
- Session-scoped memory is cleared when sessions end
- Audit logs record what was stored and when it was purged

Evidence provided: Memory purge logs demonstrate data lifecycle compliance.

### 2.3 Data protection by design (GDPR Art. 25)

Requirement: Build data protection into system architecture, not as an afterthought.

SafeAI controls:
- Boundary enforcement is architectural, not prompt-based or behavioral
- Least privilege is the default posture
- Classification and tagging happen before processing, not after
- Policies are declarative and reviewable

Evidence provided: System architecture documentation and policy files demonstrate protection-by-design.

### 2.4 Access controls and audit trail (SOC 2, ISO 27001)

Requirement: Control who and what can access data, and maintain verifiable records.

SafeAI controls:
- Capability-based access replaces static credentials
- Every boundary decision is logged with policy justification
- Agent identity and permissions are explicitly managed
- Tool contracts declare and enforce data access boundaries

Evidence provided: Audit logs with timestamp, agent ID, policy name, action, and data tags for every decision.

### 2.5 Protected health information (HIPAA)

Requirement: Safeguard PHI from unauthorized access and disclosure.

SafeAI controls:
- PHI classification via `personal.phi` data tag
- Policies can block PHI from crossing specific boundaries
- Memory schemas prevent PHI storage unless explicitly required and encrypted
- Output guard prevents PHI leakage in AI responses

Evidence provided: Audit trail demonstrates PHI handling at every step.

### 2.6 AI transparency (EU AI Act)

Requirement: AI systems must be transparent in their operation and decision-making.

SafeAI controls:
- Every enforcement decision has an explicit reason field
- Policies are human-readable YAML, reviewable by non-technical stakeholders
- Audit logs provide complete decision chains
- Open-source codebase allows full inspection of enforcement logic

Evidence provided: Policy files, audit logs, and open-source code.

## 3. Governance model

### 3.1 Policy lifecycle

```
Draft ──▶ Review ──▶ Approve ──▶ Deploy ──▶ Monitor ──▶ Update/Retire
```

Draft: Engineering or security team writes policy in YAML.
Review: Security and compliance review policy against requirements.
Approve: Authorized person approves via code review. Policies are version-controlled.
Deploy: Policy file deployed via standard CI/CD pipeline. Hot-reload takes effect within seconds.
Monitor: Audit logs and alerts track policy effectiveness and false positive rates.
Update/Retire: Policies are updated or removed through the same review process.

### 3.2 Policy ownership

| Policy type | Owner | Reviewer |
|-------------|-------|----------|
| Data classification rules | Security team | Compliance team |
| Tool access policies | Engineering team | Security team |
| Memory retention rules | Compliance team | Legal team |
| Approval workflows | Security team | Engineering team |
| Output filtering rules | Security team | Product team |

### 3.3 Incident response

When SafeAI detects or blocks a policy violation:

1. Immediate: Block or redact the violating data (automatic)
2. Log: Record full audit event with context hash (automatic)
3. Alert: Notify configured channels if alert rules match (automatic)
4. Investigate: Security team queries audit logs to assess scope
5. Remediate: Update policies, contracts, or configurations as needed
6. Report: Generate compliance report from audit data

SafeAI's audit trail provides the forensic data needed for incident response without requiring separate logging infrastructure.

### 3.4 Compliance reporting

SafeAI supports generating compliance evidence:

```bash
# Generate compliance report for a time period
safeai audit report --from 2026-01-01 --to 2026-02-19 --format pdf

# Report includes:
# - Total boundary crossings by type
# - Policy violation summary
# - Data access patterns by agent
# - Approval workflow statistics
# - Memory retention compliance
# - Anomaly flags
```

## 4. Open source governance

### 4.1 License

SafeAI uses the Apache 2.0 license:
- Permissive: allows commercial use, modification, distribution
- Patent grant: protects users from patent claims
- Attribution required: maintains project visibility
- Compatible with enterprise adoption policies

### 4.2 Contribution guidelines

- All contributions require signed Developer Certificate of Origin (DCO)
- Security-sensitive changes require review by core maintainers
- Policy engine and classifier changes require additional review
- No contributor can merge their own security-related PRs

### 4.3 Vulnerability disclosure

- Private disclosure: security@safeai.dev (or equivalent)
- Response SLA: Acknowledge within 48 hours, patch within 7 days for critical issues
- Public disclosure: After patch is available, not before
- CVE assignment: For verified vulnerabilities affecting released versions

### 4.4 Security audits

- Annual third-party security audit of core components
- Continuous fuzzing of classifiers and policy engine
- Dependency scanning via automated tools (Dependabot, Snyk)
- Community-driven security review encouraged

## 5. Data handling by SafeAI itself

SafeAI processes sensitive data transiently but must not become a liability itself.

What SafeAI stores:
- Policy files (no sensitive data)
- Audit events (tags, hashes, and decisions, never raw sensitive content)
- Memory handles (encrypted references, not raw values)
- Configuration (no secrets in config files; use environment variables or secret backends)

What SafeAI never stores:
- Raw user input
- Agent responses
- Credentials or API keys
- Unencrypted personal data

Data residency:
- SafeAI runs where you deploy it. No data is sent to external services.
- No telemetry, analytics, or phone-home behavior
- Cloud logging backends are user-configured and user-controlled

## 6. Known compliance limitations

| Limitation | Mitigation |
|-----------|------------|
| Semantic leakage may bypass pattern classification | Human approval for high-risk domains; custom classifiers for specialized data |
| Audit logs require secure storage (not SafeAI's responsibility) | Document storage requirements; provide integration guides for secure backends |
| Policy correctness depends on human authors | Validation tooling; policy testing commands; review processes |
| SafeAI cannot control third-party AI model behavior | Document scope clearly; position SafeAI as boundary defense, not model control |

## 7. Compliance readiness checklist

For organizations deploying SafeAI:

- [ ] Define data classification taxonomy for your organization
- [ ] Write policies covering all regulated data types
- [ ] Configure memory retention periods to match legal requirements
- [ ] Set up secure audit log storage with appropriate retention
- [ ] Establish policy review and approval workflows
- [ ] Configure alerts for policy violations
- [ ] Document SafeAI deployment in your data protection impact assessment
- [ ] Test incident response procedures using SafeAI audit data
- [ ] Schedule periodic policy review cycles
