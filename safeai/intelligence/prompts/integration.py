"""Prompt templates and built-in framework integration templates."""

SYSTEM_PROMPT = """\
You are a SafeAI integration expert. Your job is to generate framework-specific \
integration code that connects a target AI framework to SafeAI's security \
boundaries.

You work with:
- Target framework name and its API patterns
- Project structure (file paths, dependencies)
- SafeAI's public API (scan_input, guard_output, intercept_tool_request, etc.)

Generate clean, production-ready Python code with proper imports and error handling.
"""

USER_PROMPT_TEMPLATE = """\
Generate SafeAI integration code for the {target} framework.

## Project Structure
File paths: {file_paths}
Dependencies: {dependencies}
Detected frameworks: {framework_hints}

## SafeAI API
Available methods on the SafeAI instance:
- scan_input(text, agent_id) -> ScanResult
- guard_output(text, agent_id) -> GuardResult
- intercept_tool_request(tool_name, params, data_tags, agent_id=...) -> InterceptResult
- intercept_tool_response(tool_name, response, agent_id=...) -> ResponseInterceptResult
- intercept_agent_message(message=..., source_agent_id=..., destination_agent_id=...) -> dict
- validate_agent_identity(agent_id, tool_name=...) -> AgentIdentityValidationResult

## Target Framework
{framework_description}

## Output Format
Generate integration code using file markers:

--- FILE: safeai_{target_lower}_integration.py ---
<python code>

--- FILE: safeai_{target_lower}_config.yaml ---
<optional yaml config>
"""

# Built-in framework descriptions
FRAMEWORK_DESCRIPTIONS: dict[str, str] = {
    "langchain": """\
LangChain uses chains, agents, and tools. Integration points:
- BaseCallbackHandler for intercepting LLM calls and tool invocations
- Tool wrapper to scan inputs/outputs through SafeAI
- Agent executor hooks for identity validation
- Memory wrapper for SafeAI memory boundaries""",

    "crewai": """\
CrewAI uses crews, agents, and tasks. Integration points:
- Agent step_callback for intercepting agent actions
- Tool decorator wrapper for SafeAI boundary enforcement
- Task callback for output guarding
- Crew-level hooks for agent-to-agent message interception""",

    "autogen": """\
AutoGen uses agents, group chat, and function calls. Integration points:
- ConversableAgent hooks for message interception
- FunctionMap wrapper for tool boundary enforcement
- GroupChat speaker selection hooks for identity validation
- Message filter for input/output scanning""",

    "openclaw": """\
OpenClaw is a legal AI framework. Integration points:
- Document processing pipeline hooks for PII scanning
- LLM call wrapper for input/output guarding
- Tool execution hooks for boundary enforcement
- Multi-agent workflow hooks for agent-to-agent security""",

    "fastapi": """\
FastAPI middleware integration. Integration points:
- ASGI middleware for request/response scanning
- Dependency injection for SafeAI instance
- Exception handlers for policy violations
- Background task hooks for audit logging""",

    "generic": """\
Generic Python integration. Integration points:
- Function decorators for input/output scanning
- Context manager for scoped security boundaries
- Wrapper functions for tool call interception
- Logging integration for audit events""",
}
