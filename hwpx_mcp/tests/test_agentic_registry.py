# pyright: reportMissingImports=false
import pytest

from hwpx_mcp.agentic.registry import build_registry
from hwpx_mcp.server import mcp


@pytest.mark.asyncio
async def test_build_registry_collects_tools():
    records = await build_registry(mcp)
    assert len(records) > 100
    assert all(record.tool_id for record in records)
    assert all(record.name for record in records)


@pytest.mark.asyncio
async def test_registry_contains_ping_tool():
    records = await build_registry(mcp)
    names = {record.name for record in records}
    assert "hwp_ping" in names
