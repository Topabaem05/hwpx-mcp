# HWPX-MCP Repository Guide

## Purpose

This root file is the top-level execution guide for all coding agents.
Before editing code, confirm this document and related module-level AGENTS files.
Use it as the source of truth for command usage, constraints, and conventions.

## Scope

- Audience: agents and maintainers.
- System type: FastMCP-based MCP backend for HWP/HWPX operations.
- Key surface areas: platform tools, deterministic gateway, templates, tests.
- Primary objective: stability, determinism, and reproducible agent behavior.

## Repository Map

- `hwpx_mcp/server.py`: MCP server initialization and tool registration entrypoint.
- `hwpx_mcp/config.py`: transport/env configuration.
- `hwpx_mcp/gateway_server.py`: gateway stdio runner.
- `hwpx_mcp/tools/`: controller abstraction, unified tool registration.
- `hwpx_mcp/agentic/`: deterministic Tool-RAG gateway and routing.
- `hwpx_mcp/features/`: higher-level helpers (query/smart edit).
- `hwpx_mcp/core/`: XML parsing, validation, security helpers.
- `hwpx_mcp/tests/`: pytest suite.
- `templates/`: built-in template catalog and `.hwpx` files.
- `hwpx_mcp/eval/`: offline eval runner for gateway scoring.
- `electron-ui/`: optional UI bootstrap for streamable HTTP.

## Governance Rule Files

- `.cursor/rules/`: **not present**.
- `.cursorrules`: **not present**.
- `.github/copilot-instructions.md`: **not present**.
- Since these are absent, follow this file plus module AGENTS files as policy.

## Commands

### Packaging entry points

- `hwpx-mcp` -> `hwpx_mcp.server:main`
- `hwpx-mcp-gateway` -> `hwpx_mcp.gateway_server:main`
- `hwpx-mcp-eval` -> `hwpx_mcp.eval.run_eval:main`

### PDM scripts and install

- `pdm run start` -> `python -m hwpx_mcp.server`
- `pdm run test` -> `pytest hwpx_mcp/tests/ -v`
- `uv pip install -e .` or `pip install -e .`

### Runtime commands

- Backend (stdio): `python -m hwpx_mcp.server`
- Gateway (stdio): `hwpx-mcp-gateway`
- Offline eval: `hwpx-mcp-eval --queries hwpx_mcp/eval/queries.jsonl --top-k 5`

Transport variables from config:

- `MCP_TRANSPORT`: `stdio`, `http`, `sse`, `streamable-http`
- `MCP_HOST`, `MCP_PORT`, `MCP_PATH`
- `MCP_STATELESS`, `MCP_JSON_RESPONSE`, `MCP_LOG_LEVEL`

### Test command matrix

- Full suite: `pytest hwpx_mcp/tests/ -v`
- Single module: `pytest hwpx_mcp/tests/test_agentic_gateway.py -v`
- Targeted query: `pytest hwpx_mcp/tests/test_agentic_router.py -k routing -v`
- Single test: `pytest hwpx_mcp/tests/test_controller_factory.py::TestGetPlatformInfo::test_returns_dict -q`

### Build/Lint/Type notes

- Build metadata exists (`[tool.pdm.build]`), but no explicit build script is documented in `pdm` scripts.
- Lint/formatter is **not** configured in root `pyproject.toml`.
- Typecheck command is **not** configured in root `pyproject.toml`.
- Use `pdm run test` / `pytest` as the baseline verification gate until lint/type gates are added.

## AGENTS Hierarchy

If touching a directory, read its AGENTS first:

- `hwpx_mcp/AGENTS.md`
- `hwpx_mcp/tools/AGENTS.md`
- `hwpx_mcp/agentic/AGENTS.md`
- `hwpx_mcp/tests/AGENTS.md`
- `templates/AGENTS.md`

## Code Style and Structure Conventions

- Match module-local patterns instead of inventing new structure.
- Import order: standard library, third-party, local modules.
- Keep function signatures typed and explicit.
- Naming: `snake_case` for functions/modules, `PascalCase` for classes.
- Keep tool registration in `register_*_tools(...)` modules.
- Preserve response shape stability (`success`/`status` + `message` patterns are common).
- Avoid introducing broad `except Exception` handlers without specific error paths.
- If you alter controller behavior, keep capability gating clear and explicit.

## Error and Routing Policy

- Unsupported capabilities should use `NotSupportedError` (capability + current platform).
- Cross-platform controller rule: `open_document()` is not supported for existing document open.
- Cross-platform rule: `save_document()` needs a path at least once.
- Gateway rule: `tool_id = name + schema_hash`; schema changes change tool IDs.
- Keep routing deterministic; do not depend on mutable, nondeterministic state.

## Tool Registration Rules

- Avoid adding tools directly in `server.py` unless unavoidable.
- Add/register new tooling via `hwpx_mcp/tools/` and invoke through `initialize_server()`.
- Update relevant capability enums/matrices and registry tests when changing schema.

## Testing Conventions

- Async tests use `pytest-asyncio` with `asyncio_mode = "auto"`.
- Test files use `hwpx_mcp/tests/test_*.py`.
- Prefer focused unit/regression tests for deterministic gateway outputs and capability behavior.

## Platform Rules

- Windows: COM path has broad features.
- macOS/Linux: HWPX-first behavior and limited cross-feature support.
- Do not add Windows-only assumptions to template flow intended for Docker/Linux.

## Hygiene and Artifacts

- Treat generated paths as non-source and do not commit them:
  `.venv/`, `.pytest_cache/`, `__pycache__/`, `.pdm-build/`, `.ruff_cache/`, `.mypy_cache/`, build artifacts.
- Never commit or hand-edit generated build outputs.

## Common Anti-Patterns

- Changing schemas without updating tool registry/hash tests.
- Routing logic depending on random ordering or mutable global state.
- Calling cross-platform save/open assumptions not valid on Linux/Docker.
- Modifying output shape used by clients without migration.

## Useful Verification

- `pytest hwpx_mcp/tests/test_controller_factory.py::TestGetPlatformInfo::test_returns_dict -q` (single test check)
- `pytest hwpx_mcp/tests/ -v` (suite check)
- `git status --short` and review scope before/after each change.

## Agent Handoff Template (Mandatory)

- Goal: one-line objective.
- Changes: files changed + reason.
- Decisions: why each design choice aligns with constraints.
- Risks: compatibility, platform, determinism.
- Validation: exact commands run and outcomes.
- Next step: what to run next.
