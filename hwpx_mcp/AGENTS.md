# hwpx_mcp/

## Overview
Main package: backend MCP server, transport config, agentic gateway, tools, and tests.

## Structure
```
hwpx_mcp/
├── server.py             # backend FastMCP server; registers tool modules
├── config.py             # env-driven transport config
├── gateway_server.py     # gateway stdio entrypoint
├── agentic/              # deterministic routing gateway (Tool-RAG)
├── tools/                # controllers + tool registration modules
├── features/             # higher-level doc/query helpers
├── core/                 # XML security/validation helpers
└── tests/                # pytest suite
```

## Where To Look
| Task | Location | Notes |
|------|----------|-------|
| Register tools | `hwpx_mcp/server.py` | `initialize_server()` imports/registers tool groups
| Transport selection | `hwpx_mcp/config.py` | `ServerConfig.get_run_kwargs()` for FastMCP.run
| Gateway entrypoint | `hwpx_mcp/gateway_server.py` | stdio-only gateway wrapper around backend server
| XML safety/validation | `hwpx_mcp/core/xml_parser.py` + `hwpx_mcp/core/validator.py` | secure parsing + schema checks

## Conventions
- Entry points are defined in `pyproject.toml` under `[project.scripts]`.
- Backend server exposes a large tool surface; gateway reduces this surface to a few meta-tools.

## Anti-Patterns
- Don’t add new tools directly in `server.py` unless unavoidable; prefer adding a `register_*_tools()` in `hwpx_mcp/tools/` and calling it from `initialize_server()`.
