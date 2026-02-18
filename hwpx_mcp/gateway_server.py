#!/usr/bin/env python

from __future__ import annotations

import logging
import os
import sys
from collections.abc import Awaitable
from collections.abc import Callable
from importlib import import_module
from typing import Any
from typing import Protocol

from hwpx_mcp.agentic.gateway import AgenticGateway
from hwpx_mcp.agentic.gateway import BackendServer

logger = logging.getLogger("hwpx-mcp-agentic-gateway")

class MCPApp(Protocol):
    def tool(self) -> Callable[[Callable[..., Awaitable[dict[str, object]]]], Callable[..., Awaitable[dict[str, object]]]]: ...

    def run(self, *, transport: str) -> None: ...


def _create_gateway_mcp() -> MCPApp:
    module = import_module("mcp.server.fastmcp")
    fastmcp_cls = getattr(module, "FastMCP")
    return fastmcp_cls(name="HWPX-Agentic-Gateway")


gateway_mcp = _create_gateway_mcp()


def _backend_server() -> BackendServer:
    from hwpx_mcp.server import mcp as backend_mcp

    return backend_mcp


gateway = AgenticGateway(_backend_server())


@gateway_mcp.tool()
async def tool_registry_refresh() -> dict[str, object]:
    return await gateway.refresh_registry()


@gateway_mcp.tool()
async def tool_search(query: str, k: int = 8, group: str | None = None) -> dict[str, object]:
    return await gateway.tool_search(query=query, k=k, group=group)


@gateway_mcp.tool()
async def tool_describe(tool_id: str) -> dict[str, object]:
    return await gateway.tool_describe(tool_id=tool_id)


@gateway_mcp.tool()
async def tool_call(tool_id: str, arguments: dict[str, Any] | None = None) -> dict[str, object]:
    return await gateway.tool_call(tool_id=tool_id, arguments=arguments or {})


@gateway_mcp.tool()
async def route_and_call(
    query: str,
    arguments: dict[str, Any] | None = None,
    top_k: int = 1,
) -> dict[str, object]:
    return await gateway.route_and_call(query=query, arguments=arguments or {}, top_k=top_k)


def main() -> None:
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    if transport != "stdio":
        logger.error("Gateway Phase 1 supports stdio transport only.")
        sys.exit(1)

    gateway_mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
