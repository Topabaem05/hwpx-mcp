# AGENTS Guide
## Purpose
This repo is a mixed Python backend + Electron UI project for HWP/HWPX automation.
Use this file as the root guide for autonomous coding agents working anywhere in the tree.

## Repo Map
- Backend/runtime: `hwpx_mcp/`, gateway: `hwpx_mcp/agentic/`, tools/controllers: `hwpx_mcp/tools/`
- Tests: `hwpx_mcp/tests/`, templates: `templates/`, scripts: `scripts/`, UI: `electron-ui/`

## Scoped Guides
Read the nearest child guide first when working in these areas:
- `hwpx_mcp/AGENTS.md`
- `hwpx_mcp/tools/AGENTS.md`
- `hwpx_mcp/agentic/AGENTS.md`
- `hwpx_mcp/tests/AGENTS.md`
- `templates/AGENTS.md`
- `scripts/AGENTS.md`
- `electron-ui/AGENTS.md`

## External Rule Files
Checked at repo root:
- No `.cursorrules`
- No `.cursor/rules/`
- No `.github/copilot-instructions.md`
If any of those files are added later, fold them into this guide in the same change.

## Where To Look
| Task | Primary location | Notes |
|------|------------------|-------|
| Backend startup/transport | `hwpx_mcp/server.py`, `hwpx_mcp/config.py` | `main()` selects `stdio`, `http`, `sse`, or `streamable-http` |
| Gateway stdio surface | `hwpx_mcp/gateway_server.py` | Reduced deterministic MCP surface |
| Tool registration | `hwpx_mcp/tools/` | Prefer `register_*_tools(...)` modules over direct edits in `server.py` |
| Controller abstraction | `hwpx_mcp/tools/hwp_controller_base.py`, `hwpx_mcp/tools/controller_factory.py` | Capability gating and platform split live here |
| Routing/retrieval | `hwpx_mcp/agentic/` | Registry hash, grouping, retrieval, route selection |
| Agent HTTP API | `hwpx_mcp/agentic/http_api.py` | FastAPI router for `/agent/*` |
| Tests | `hwpx_mcp/tests/` | Pytest + pytest-asyncio |
| Desktop UI | `electron-ui/` | UI expects `streamable-http` backend |
| Packaging | `scripts/`, `electron-ui/package.json` | PyInstaller + electron-builder workflows |

## Install And Run
Authoritative command sources are `pyproject.toml`, `README.md`, `scripts/`, and `electron-ui/package.json`.

### Python setup
```bash
uv pip install -e .
```
Alternative dev setup: `pdm install`

### Backend and gateway
```bash
pdm run start
hwpx-mcp
hwpx-mcp-gateway
hwpx-mcp-eval --queries hwpx_mcp/eval/queries.jsonl --top-k 5
```
- `pdm run start` maps to `python -m hwpx_mcp.server`
- `hwpx-mcp`, `hwpx-mcp-gateway`, and `hwpx-mcp-eval` come from `pyproject.toml`
- Gateway Phase 1 is stdio-only; Electron uses the backend HTTP surface

### Electron UI
```bash
npm --prefix electron-ui install
npm --prefix electron-ui run start
npm --prefix electron-ui run start-stack
```

### Packaging
```bash
./scripts/build-backend.sh
./scripts/build-installer.sh
npm --prefix electron-ui run build:linux
npm --prefix electron-ui run build:mac
npm --prefix electron-ui run build:win
```
Windows equivalents exist as `.ps1` scripts under `scripts/`.

## Test Commands
Primary test entrypoints:
```bash
pdm run test
pytest hwpx_mcp/tests/ -v
```
Useful focused patterns:
```bash
pytest hwpx_mcp/tests/test_agentic_router.py -v
pytest hwpx_mcp/tests/test_agentic_router.py::test_router_selects_expected_group -v
pytest hwpx_mcp/tests/test_agentic_gateway.py -k ping -v
```
Pytest discovery from `pyproject.toml`:
- `testpaths = ["hwpx_mcp/tests"]`
- `python_files = ["test_*.py"]`
- `python_functions = ["test_*"]`
- `asyncio_mode = "auto"`

## Lint And Typecheck Reality
There is no repo-wide lint command or dedicated typecheck command configured in `pyproject.toml`.
For agent work:
- Do not invent `ruff`, `mypy`, or `pyright` as official workflows
- Verify with targeted pytest runs, focused runtime checks, and LSP diagnostics where supported
- If you add lint/typecheck tooling, document it here and in the nearest child guide

## Python Style Conventions
The codebase is mixed quality, but newer controller/gateway code is the best reference.
Follow the strongest local pattern instead of forcing uniformity onto older files.

### Imports
- Prefer standard library, then third-party, then local imports
- In newer files, one imported symbol per line is common when readability improves
- Use relative imports inside tightly-coupled package modules when nearby files already do
- Avoid adding unused imports

### Formatting
- Follow existing four-space indentation and blank-line spacing
- Use short docstrings for public classes/functions and MCP tools
- Prefer readable multi-line dict literals/calls and use f-strings for messages/logs

### Typing
- Prefer modern built-in generics like `list[str]` and `dict[str, object]` in newer files
- Use `Protocol`, `TypedDict`, `Literal`, and dataclasses for structured boundaries where helpful
- Keep API-boundary types specific and match the local file if it still uses older `Optional`, `List`, `Dict`, or `Any` style

### Naming
- `snake_case` for functions, variables, and modules
- `PascalCase` for classes, dataclasses, enums, Pydantic models, and exceptions
- MCP tool names follow the `hwp_*` pattern
- Registration helpers should follow `register_*_tools` and return `None`

### Error Handling
- Prefer explicit domain errors already present in the repo: `NotSupportedError`, `HwpError`, `ConnectionError`, `DocumentNotOpenError`
- Capability mismatches should use capability checks or `NotSupportedError`
- Tool wrappers should convert failures into stable result dicts instead of leaking raw exceptions
- FastAPI surfaces should translate failures into `HTTPException` with meaningful status codes and logs should stay actionable

### Response Shapes
- Preserve stable wrapper keys such as `success`, `status`, `message`, `error`, `count`, `path`, and `result`
- Do not casually rename response keys; extend responses compatibly instead

### Platform Behavior
- This repo is intentionally cross-platform with Windows-only capability branches
- Windows COM features must be explicitly gated
- Cross-platform flows should prefer HWPX-safe behavior with clear unsupported messages

## Architecture Rules
- Keep `hwpx_mcp/server.py` as the composition root; do not pile business logic into it
- Add new MCP tools through `register_*_tools(...)` modules when possible
- Keep deterministic routing in `hwpx_mcp/agentic/` reproducible and state-light
- Tool schema changes can affect registry hashes and `tool_id` stability; update tests accordingly

## Test Style
- Use direct pytest assertions; keep tests behavior-focused
- Async tests use `@pytest.mark.asyncio`
- Prefer helper builders for repeated fixtures/records inside a test file
- Match the repo style of descriptive names like `test_gateway_tool_describe_and_call_ping`

## Scripts And UI
- Shell and PowerShell script pairs should stay behaviorally aligned
- Scripts assume repo-root-relative paths and fail fast
- Electron bootstrap code must continue to assume `streamable-http`; keep UI as orchestration/transport glue

## Generated Artifacts
Do not commit local/generated outputs such as:
- `.venv/`, `.pytest_cache/`, `__pycache__/`
- `.pdm-build/`, `.ruff_cache/`, `.mypy_cache/`, `build/`, `dist/`, installer outputs
- Electron dependency artifacts unless explicitly intended

## Agent Checklist
Before finishing a change:
1. Read the nearest child `AGENTS.md` if working outside repo root
2. Run the smallest relevant pytest command, preferably at file scope or node-id level
3. If no official lint/typecheck command exists, use diagnostics plus runtime/test validation
4. Preserve response-shape compatibility and platform gating
5. Update this file or the nearest child guide when workflows or conventions change
