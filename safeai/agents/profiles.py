"""Agent profile registry mapping agent-specific tool names to SafeAI categories."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class AgentProfile:
    """Maps an agent's tool names to generic SafeAI tool categories."""

    name: str
    description: str
    tool_map: dict[str, str] = field(default_factory=dict)
    hook_installer: str | None = None


_BUILTIN_PROFILES: dict[str, AgentProfile] = {
    "claude-code": AgentProfile(
        name="claude-code",
        description="Anthropic Claude Code CLI",
        tool_map={
            "Bash": "shell",
            "Write": "file_write",
            "Edit": "file_edit",
            "Read": "file_read",
            "Glob": "search",
            "Grep": "search",
            "WebFetch": "web",
            "WebSearch": "web",
            "Task": "agent_dispatch",
        },
        hook_installer="safeai.agents.installers.claude_code",
    ),
    "cursor": AgentProfile(
        name="cursor",
        description="Cursor AI code editor",
        tool_map={
            "run_command": "shell",
            "write_file": "file_write",
            "edit_file": "file_edit",
            "read_file": "file_read",
            "search_files": "search",
            "web_search": "web",
        },
        hook_installer="safeai.agents.installers.cursor",
    ),
    "generic": AgentProfile(
        name="generic",
        description="Generic agent (pass-through tool names)",
        tool_map={},
        hook_installer="safeai.agents.installers.generic",
    ),
}

_custom_profiles: dict[str, AgentProfile] = {}


def register_profile(profile: AgentProfile) -> None:
    """Register a custom agent profile."""
    _custom_profiles[profile.name] = profile


def get_profile(name: str) -> AgentProfile | None:
    """Look up a profile by name. Returns None if not found."""
    return _custom_profiles.get(name) or _BUILTIN_PROFILES.get(name)


def list_profiles() -> list[AgentProfile]:
    """Return all registered profiles (built-in + custom)."""
    merged = {**_BUILTIN_PROFILES, **_custom_profiles}
    return list(merged.values())


def resolve_tool_category(tool_name: str, profile: AgentProfile | None = None) -> str:
    """Map an agent-specific tool name to a SafeAI category.

    If the profile has a mapping, return it. Otherwise return the tool name as-is.
    """
    if profile and tool_name in profile.tool_map:
        return profile.tool_map[tool_name]
    return tool_name
