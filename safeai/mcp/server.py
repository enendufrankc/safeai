"""Stdio-based MCP server exposing SafeAI boundary enforcement tools."""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import TextContent, Tool

    MCP_AVAILABLE = True
except ImportError:  # pragma: no cover
    MCP_AVAILABLE = False

from safeai.api import SafeAI


def _serializable(obj: Any) -> dict:
    """Convert a dataclass or dict to a JSON-serializable dict."""
    if hasattr(obj, "__dataclass_fields__"):
        raw = asdict(obj)
    elif isinstance(obj, dict):
        raw = obj
    else:
        raw = {"value": str(obj)}
    return json.loads(json.dumps(raw, default=str))


def create_mcp_server(safeai: SafeAI) -> Any:
    """Create an MCP server wired to the given SafeAI instance.

    Raises ImportError if the ``mcp`` package is not installed.
    """
    if not MCP_AVAILABLE:
        raise ImportError(
            "The 'mcp' package is required for the MCP server. "
            "Install it with: pip install 'safeai[mcp]'"
        )

    server = Server("safeai")

    @server.list_tools()
    async def _list_tools() -> list[Tool]:
        return [
            Tool(
                name="scan_input",
                description="Scan text through SafeAI input boundary",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Text to scan"},
                        "agent_id": {"type": "string", "default": "mcp-client"},
                    },
                    "required": ["text"],
                },
            ),
            Tool(
                name="guard_output",
                description="Guard text through SafeAI output boundary",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Output text to guard"},
                        "agent_id": {"type": "string", "default": "mcp-client"},
                    },
                    "required": ["text"],
                },
            ),
            Tool(
                name="scan_structured",
                description="Scan a JSON payload through SafeAI input boundary",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "payload": {"type": "object", "description": "JSON payload to scan"},
                        "agent_id": {"type": "string", "default": "mcp-client"},
                    },
                    "required": ["payload"],
                },
            ),
            Tool(
                name="query_audit",
                description="Query the SafeAI audit log",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "agent_id": {"type": "string"},
                        "boundary": {"type": "string"},
                        "action": {"type": "string"},
                        "limit": {"type": "integer", "default": 50},
                    },
                },
            ),
            Tool(
                name="list_policies",
                description="List available SafeAI policy templates",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="check_tool",
                description="Check if a tool call would be allowed by SafeAI policies",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "tool_name": {"type": "string", "description": "Tool name to check"},
                        "parameters": {"type": "object", "default": {}},
                        "data_tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "default": [],
                        },
                        "agent_id": {"type": "string", "default": "mcp-client"},
                        "session_id": {"type": "string"},
                    },
                    "required": ["tool_name"],
                },
            ),
        ]

    @server.call_tool()
    async def _call_tool(name: str, arguments: dict) -> list[TextContent]:
        result = _handle_tool(safeai, name, arguments)
        return [TextContent(type="text", text=json.dumps(result, default=str))]

    return server


def _handle_tool(safeai: SafeAI, name: str, arguments: dict) -> dict:
    """Dispatch a tool call to the corresponding SafeAI method."""
    if name == "scan_input":
        res = safeai.scan_input(arguments["text"], agent_id=arguments.get("agent_id", "mcp-client"))
        return _serializable(res)

    if name == "guard_output":
        res = safeai.guard_output(
            arguments["text"], agent_id=arguments.get("agent_id", "mcp-client")
        )
        return _serializable(res)

    if name == "scan_structured":
        res = safeai.scan_structured_input(
            arguments["payload"], agent_id=arguments.get("agent_id", "mcp-client")
        )
        return _serializable(res)

    if name == "query_audit":
        rows = safeai.query_audit(**{k: v for k, v in arguments.items() if v is not None})
        return {"entries": rows}

    if name == "list_policies":
        return {"templates": safeai.list_policy_templates()}

    if name == "check_tool":
        res = safeai.intercept_tool_request(
            tool_name=arguments["tool_name"],
            parameters=arguments.get("parameters", {}),
            data_tags=arguments.get("data_tags", []),
            agent_id=arguments.get("agent_id", "mcp-client"),
            session_id=arguments.get("session_id"),
        )
        return _serializable(res)

    return {"error": f"Unknown tool: {name}"}


async def run_stdio_server(config_path: str) -> None:
    """Run the MCP server over stdio."""
    if not MCP_AVAILABLE:
        raise ImportError(
            "The 'mcp' package is required for the MCP server. "
            "Install it with: pip install 'safeai[mcp]'"
        )

    safeai = SafeAI.from_config(config_path)
    server = create_mcp_server(safeai)

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())
