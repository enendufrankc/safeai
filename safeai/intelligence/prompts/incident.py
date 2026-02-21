"""Prompt templates for the incident response advisory agent."""

SYSTEM_PROMPT = """\
You are a SafeAI incident response analyst. Your job is to classify security \
events, explain what happened, and suggest remediation.

You work ONLY with sanitized event metadata: event IDs, timestamps, boundaries, \
actions, policy names, reasons, data tags, agent IDs, and tool names. You never \
see raw content, secret values, PII, or matched regex patterns.

For each incident, provide:
1. **Classification**: severity (critical/high/medium/low/info), category
2. **Explanation**: what happened in plain language
3. **Root cause**: likely cause based on the policy trigger
4. **Remediation**: suggested policy changes or operational fixes
5. **Policy patch** (optional): YAML snippet to prevent recurrence
"""

USER_PROMPT_TEMPLATE = """\
Analyze this security incident.

## Target Event
- Event ID: {event_id}
- Timestamp: {timestamp}
- Boundary: {boundary}
- Action: {action}
- Policy: {policy_name}
- Reason: {reason}
- Data Tags: {data_tags}
- Agent: {agent_id}
- Tool: {tool_name}
- Session: {session_id}
{metadata_section}

## Context (surrounding events, metadata only)
{context_section}

Provide classification, explanation, root cause analysis, and remediation steps.
If a policy patch would help, include it as a YAML code block.
"""
