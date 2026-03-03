# PROJECT KNOWLEDGE BASE

**Generated:** 2026-03-02 18:59:58 KST
**Commit:** 5d03014
**Branch:** wt/oauth

## OVERVIEW
FastMCP-based backend for HWP/HWPX operations with two execution surfaces: full backend tools and a deterministic agentic gateway.
The repository is intentionally mixed: Python backend/runtime, template assets, build/release scripts, and optional Electron UI.

## STRUCTURE
```
hwpx-mcp/
├── hwpx_mcp/              # backend package: server, tools, agentic routing, XML helpers, tests
├── templates/             # built-in .hwpx templates + template_index.json + preview images
├── scripts/               # build/installer/bootstrap/cleanup helpers (.sh/.ps1)
├── electron-ui/           # desktop shell for streamable HTTP MCP backend
├── .github/workflows/     # CI/release pipelines (Windows x64 release build)
├── src/                   # legacy package mirror (small; no active domain split)
└── security_module/       # Windows COM sample DLL asset
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Backend startup/transport | `hwpx_mcp/server.py`, `hwpx_mcp/config.py` | `main()` selects `stdio/http/sse/streamable-http` |
| Gateway startup | `hwpx_mcp/gateway_server.py` | deterministic gateway stdio process |
| Tool registration and controllers | `hwpx_mcp/tools/` | prefer `register_*_tools(...)` modules over `server.py` edits |
| Routing internals | `hwpx_mcp/agentic/` | registry hash + grouping + deterministic routing |
| XML safety/query/edit | `hwpx_mcp/core/`, `hwpx_mcp/features/` | secure parser + validator + smart patch/query |
| Tests and regressions | `hwpx_mcp/tests/`, `pyproject.toml` | pytest + pytest-asyncio (`asyncio_mode=auto`) |
| Template source of truth | `templates/template_index.json` | template IDs/metadata map to `.hwpx` files |
| UI bootstrap | `electron-ui/main.js`, `electron-ui/scripts/start-stack.js` | streamable HTTP bootstrap + readiness polling |
| Release/build automation | `scripts/`, `.github/workflows/windows-x64-release.yml` | backend PyInstaller + Electron packaging |

## CODE MAP
| Symbol | Type | Location | Role |
|--------|------|----------|------|
| `initialize_server` | function | `hwpx_mcp/server.py` | backend FastMCP registration chain |
| `register_windows_tools` | function | `hwpx_mcp/server.py` | Windows-only COM tool surface wiring |
| `main` | function | `hwpx_mcp/server.py` | runtime entrypoint and transport dispatch |
| `main` | function | `hwpx_mcp/gateway_server.py` | gateway runtime entrypoint |
| `main` | function | `hwpx_mcp/eval/run_eval.py` | offline routing eval CLI |

## CONVENTIONS
- Packaging, script entrypoints, and pytest config are centralized in `pyproject.toml`.
- Backend/gateway/eval CLIs are `hwpx-mcp`, `hwpx-mcp-gateway`, `hwpx-mcp-eval`.
- Tool wrappers keep response-shape compatibility (`success`/`status` + `message`).
- Cross-platform behavior is explicit: Windows COM path vs Linux/macOS HWPX-first path.
- Child AGENTS files are deltas; avoid restating root-wide rules.

## ANTI-PATTERNS (THIS PROJECT)
- Adding new tools directly in `hwpx_mcp/server.py` when `register_*_tools()` modules are available.
- Changing tool schema without accounting for deterministic registry/hash expectations.
- Introducing nondeterministic state into agentic routing paths.
- Assuming Windows-only behavior in Docker/Linux or template flows.
- Committing generated artifacts (`.venv/`, caches, `dist/`, installer outputs).

## UNIQUE STYLES
- Dual-surface architecture: broad backend surface plus narrow deterministic gateway surface.
- Deterministic Tool-RAG router focused on testable group routing and schema-sensitive IDs.
- Strong operational docs in README files for desktop/bootstrap/distribution workflows.

## COMMANDS
```bash
# install / run
uv pip install -e .
pdm run start
hwpx-mcp-gateway

# tests / eval
pdm run test
pytest hwpx_mcp/tests/test_agentic_router.py -k routing -v
hwpx-mcp-eval --queries hwpx_mcp/eval/queries.jsonl --top-k 5

# ui / packaging
npm --prefix electron-ui run start-stack
./scripts/build-backend.sh
./scripts/build-installer.sh
```

## AGENTS HIERARCHY
- `hwpx_mcp/AGENTS.md`
- `hwpx_mcp/tools/AGENTS.md`
- `hwpx_mcp/agentic/AGENTS.md`
- `hwpx_mcp/tests/AGENTS.md`
- `templates/AGENTS.md`
- `scripts/AGENTS.md`
- `electron-ui/AGENTS.md`

## NOTES
- Root covers shared invariants only; child files should contain local behavior and exceptions.
- If runtime/build/test workflow changes, update the nearest AGENTS file in the same commit.
- `src/` is currently low-complexity/legacy and is intentionally covered by root guidance.
