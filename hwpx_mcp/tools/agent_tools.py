from __future__ import annotations

from typing import Any

from hwpx_mcp.agentic.tool_only_agent import ToolOnlyAgent


def register_agent_tools(mcp) -> None:
    agent = ToolOnlyAgent(mcp)

    @mcp.tool()
    async def hwp_agent_chat(message: str, session_id: str = "") -> dict[str, Any]:
        return await agent.run(message=message, session_id=session_id)
