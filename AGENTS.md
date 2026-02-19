# PROJECT KNOWLEDGE BASE

**Generated:** 2026-02-19 20:31:09 KST
**Commit:** 5660768
**Branch:** main

## OVERVIEW
FastMCP-based backend for HWP/HWPX operations with two surfaces: full backend tools and a deterministic agentic gateway.
Priority is deterministic routing, stable tool schemas, and cross-platform behavior (Windows COM vs Linux/macOS HWPX-first).

## STRUCTURE
```
hwpx-mcp/
├── hwpx_mcp/              # backend package: server, config, tools, agentic, tests
├── templates/             # built-in .hwpx templates + catalog + previews
├── scripts/               # build/bootstrap/cleanup/release helpers
├── electron-ui/           # optional desktop UI for streamable HTTP backend
└── AGENTS.md              # root policy and navigation hub
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Server startup/transport | `hwpx_mcp/server.py`, `hwpx_mcp/config.py` | `main()` chooses stdio/http/sse/streamable-http |
| Tool registration | `hwpx_mcp/tools/` | Prefer `register_*_tools(...)` modules over ad-hoc server edits |
| Gateway routing | `hwpx_mcp/agentic/` | Registry hash + deterministic group routing |
| XML safety/query/edit | `hwpx_mcp/core/`, `hwpx_mcp/features/` | Secure parser, validator, smart edit/query helpers |
| Tests and regressions | `hwpx_mcp/tests/` | pytest + pytest-asyncio (`asyncio_mode=auto`) |
| Templates and catalog | `templates/`, `hwpx_mcp/tools/template_tools.py` | `template_index.json` is source of truth |
| UI + local stack bootstrap | `electron-ui/`, `scripts/quick-start-bunx.*` | UI expects streamable HTTP endpoint |

## CODE MAP
LSP document/workspace symbol APIs were unavailable during generation.
Use direct entrypoints as central anchors:
- `hwpx_mcp/server.py`: backend `FastMCP` app and registration chain.
- `hwpx_mcp/gateway_server.py`: gateway `FastMCP` wrapper and stdio run path.
- `hwpx_mcp/eval/run_eval.py`: offline routing eval against backend MCP surface.

## CONVENTIONS
- Packaging/scripts live in `pyproject.toml` (`hwpx-mcp`, `hwpx-mcp-gateway`, `hwpx-mcp-eval`).
- Baseline verification is pytest (`pdm run test`); no repo-wide lint/typecheck command is configured.
- Keep response shape compatibility in tool wrappers (`success`/`status` + `message` style).
- Use capability gating and explicit unsupported errors for platform differences.

## ANTI-PATTERNS (THIS PROJECT)
- Adding new tools directly in `server.py` when a `register_*_tools()` module can be used.
- Changing tool schema without updating deterministic registry/hash expectations.
- Introducing nondeterministic state into gateway routing decisions.
- Assuming Windows-only behavior in Linux/Docker template or cross-platform flows.

## UNIQUE STYLES
- Dual surface architecture: broad backend toolset plus reduced deterministic gateway meta-tools.
- Mixed repository: Python backend + template assets + Electron UI + packaging scripts in one tree.
- Strong command-level operational docs (desktop configs, docker flow, installer flow) in README.

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
- Root governs shared invariants only; child AGENTS must document local deltas.
- Do not commit generated artifacts: `.venv/`, `.pytest_cache/`, `__pycache__/`, `.pdm-build/`, `.ruff_cache/`, `.mypy_cache/`, `dist/`, installer outputs.
- If commands/workflows change, update the nearest AGENTS file in the same commit.
