# pyright: reportMissingImports=false
import pytest
from typing import cast

from hwpx_mcp.agentic.gateway import AgenticGateway
from hwpx_mcp.server import mcp


@pytest.mark.asyncio
async def test_gateway_search_returns_ranked_results():
    gateway = AgenticGateway(mcp)
    result = await gateway.tool_search(query="export to pdf", k=3)
    assert result["success"] is True
    assert result["results"]


@pytest.mark.asyncio
async def test_gateway_tool_describe_and_call_ping():
    gateway = AgenticGateway(mcp)
    search = await gateway.tool_search(query="hwp_ping", k=5)
    results = cast(list[dict[str, object]], search["results"])
    ping_candidate = next((item for item in results if item.get("name") == "hwp_ping"), None)
    assert ping_candidate is not None
    ping_tool_id = ping_candidate.get("tool_id")
    assert isinstance(ping_tool_id, str)

    description = await gateway.tool_describe(ping_tool_id)
    assert description["success"] is True
    tool_payload = cast(dict[str, object], description["tool"])
    assert tool_payload["name"] == "hwp_ping"

    called = await gateway.tool_call(ping_tool_id, {})
    assert called["success"] is True
    assert called["tool_name"] == "hwp_ping"
