import pytest

from hwpx_mcp.server import mcp


@pytest.mark.asyncio
async def test_agent_chat_tool_is_registered():
    tools = await mcp.list_tools()
    names = {str(tool.model_dump().get("name", "")) for tool in tools}
    assert "hwp_agent_chat" in names
