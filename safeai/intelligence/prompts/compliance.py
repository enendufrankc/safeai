"""Prompt templates and built-in compliance requirement mappings."""

SYSTEM_PROMPT = """\
You are a SafeAI compliance policy expert. Your job is to map regulatory \
framework requirements to SafeAI policy rules that enforce them.

You work with:
- Compliance framework requirements (provided below)
- Current SafeAI configuration structure (if available)
- SafeAI policy schema (boundary, priority, condition, action, reason)

Generate comprehensive policy sets that address each compliance requirement. \
Include gap analysis for any requirements that cannot be fully addressed by \
SafeAI policy rules alone.
"""

USER_PROMPT_TEMPLATE = """\
Generate SafeAI policies for {framework} compliance.

## {framework} Requirements
{requirements}

## Current Configuration
{config_summary}

## Output Format
Provide:
1. A gap analysis section explaining coverage
2. Policy YAML using file markers

--- FILE: policies/{framework_lower}-compliance.yaml ---
<yaml content with all compliance policies>
"""

# Built-in compliance requirement mappings
COMPLIANCE_REQUIREMENTS: dict[str, str] = {
    "hipaa": """\
- Access Control (164.312(a)): Unique user/agent identification, emergency access, automatic logoff, encryption
- Audit Controls (164.312(b)): Record and examine activity in systems containing PHI
- Integrity Controls (164.312(c)): Protect PHI from improper alteration or destruction
- Transmission Security (164.312(e)): Guard against unauthorized access to PHI during transmission
- Person/Entity Authentication (164.312(d)): Verify identity of persons/entities seeking access
- Minimum Necessary (164.502(b)): Limit PHI use/disclosure to minimum necessary
- Data Tags: personal.phi, personal.pii, personal.medical""",

    "pci-dss": """\
- Requirement 3: Protect stored cardholder data — mask PAN, encrypt at rest
- Requirement 4: Encrypt transmission of cardholder data across open networks
- Requirement 7: Restrict access by business need-to-know
- Requirement 8: Identify and authenticate access to system components
- Requirement 10: Track and monitor all access to network resources and cardholder data
- Requirement 12: Maintain an information security policy
- Data Tags: personal.financial, secret.credential, personal.pii""",

    "soc2": """\
- CC6.1: Logical and physical access controls — restrict access to authorized users
- CC6.2: Prior to issuing credentials, register and authorize new users
- CC6.3: Manage access to protected information assets
- CC7.1: Monitor system components for anomalies — detect security events
- CC7.2: Monitor for indicators of compromise
- CC7.3: Respond to identified security incidents
- CC8.1: Authorize, design, develop, configure, document, test changes
- Data Tags: secret.credential, secret.token, personal.pii""",

    "gdpr": """\
- Article 5(1)(f): Integrity and confidentiality — protect personal data against unauthorized processing
- Article 25: Data protection by design and by default
- Article 30: Records of processing activities
- Article 32: Security of processing — encryption, pseudonymization, confidentiality
- Article 33: Notification of data breach within 72 hours
- Article 35: Data protection impact assessment for high-risk processing
- Data Tags: personal.pii, personal.phi, personal.financial, personal""",
}
