# AGENTS Guide

## Purpose
- This root file is the shared guide for coding agents working anywhere in this repository.
- Prefer the nearest nested `AGENTS.md` when working inside `hwpx_mcp/`, `hwpx_mcp/tools/`, `hwpx_mcp/agentic/`, `hwpx_mcp/tests/`, `scripts/`, `templates/`, `electron-ui/`, or `apps/agent-chat/`.
- Preserve deterministic routing behavior, stable MCP tool schemas, and cross-platform behavior.

## Repository Shape
- `hwpx_mcp/`: Python backend package, server entrypoints, agentic gateway, XML helpers, and tests.
- `hwpx_mcp/tools/`, `hwpx_mcp/agentic/`, `hwpx_mcp/tests/`: tool registration, deterministic routing, and pytest coverage.
- `templates/`, `scripts/`, `electron-ui/`: built-in assets, build/bootstrap helpers, and the optional desktop shell.
- `apps/agent-chat/`: standalone Bun/Vite/Electron chat client prototype.
- `.github/workflows/windows-x64-release.yml`: Windows packaging reference.

## Scoped Guides
Read the nearest child guide first when working in these areas:
- `hwpx_mcp/AGENTS.md`
- `hwpx_mcp/tools/AGENTS.md`
- `hwpx_mcp/agentic/AGENTS.md`
- `hwpx_mcp/tests/AGENTS.md`
- `templates/AGENTS.md`
- `scripts/AGENTS.md`
- `electron-ui/AGENTS.md`
- `apps/agent-chat/AGENTS.md`

## Rule Files Present
- Root guidance file exists: `AGENTS.md`.
- Nested guidance exists in `hwpx_mcp/`, `hwpx_mcp/tools/`, `hwpx_mcp/agentic/`, `hwpx_mcp/tests/`, `scripts/`, `templates/`, `electron-ui/`, and `apps/agent-chat/`.
- No Cursor rules were found in `.cursor/rules/`.
- No `.cursorrules` file was found.
- No Copilot instruction file was found at `.github/copilot-instructions.md`.

## Core Architecture Notes
- `hwpx_mcp/server.py` is the backend composition root; keep it focused on wiring and registration.
- `hwpx_mcp/gateway_server.py` exposes the reduced deterministic stdio gateway surface.
- Add tool logic in `hwpx_mcp/tools/` registration modules instead of expanding server glue.
- Controller capability checks live around `hwpx_mcp/tools/hwp_controller_base.py` and `hwpx_mcp/tools/controller_factory.py`.
- The gateway is intentionally deterministic; routing and retrieval in `hwpx_mcp/agentic/` must stay reproducible.
- The FastAPI agent surface lives in `hwpx_mcp/agentic/http_api.py`.
- XML parsing and validation should go through the secure helpers under `hwpx_mcp/core/` and `hwpx_mcp/features/`.
- Cross-platform behavior matters: Windows COM features must remain gated, while Linux/macOS flows stay HWPX-first.

## Install And Run Commands
- Authoritative command sources are `pyproject.toml`, `README.md`, `scripts/`, and `electron-ui/package.json`.
```bash
# install editable package
uv pip install -e .
# alternative dependency setup
pdm install
# alternative dev install with test extras
pip install -e ".[dev]"
# start backend via pdm script
pdm run start
# start backend directly
python -m hwpx_mcp.server
# start backend through project CLI
hwpx-mcp
# run deterministic gateway
hwpx-mcp-gateway
# run offline routing eval
hwpx-mcp-eval --queries hwpx_mcp/eval/queries.jsonl --top-k 5
```

## Test Commands
```bash
# canonical full test run from pyproject
pdm run test
# equivalent direct pytest run
pytest hwpx_mcp/tests/ -v
# run one test file
pytest hwpx_mcp/tests/test_agentic_router.py -v
# run one filtered subset from a file
pytest hwpx_mcp/tests/test_agentic_router.py -k routing -v
# run one specific test function
pytest hwpx_mcp/tests/test_agentic_router.py::test_router_selects_expected_group -v
# run one filtered gateway test
pytest hwpx_mcp/tests/test_agentic_gateway.py -k ping -v
```

## Build And Packaging Commands
```bash
# install electron dependencies
npm --prefix electron-ui install
# backend bundle
./scripts/build-backend.sh
# full installer pipeline
./scripts/build-installer.sh
# electron + backend local bootstrap
npm --prefix electron-ui run start-stack
# direct electron startup
npm --prefix electron-ui run start
# platform package builds
npm --prefix electron-ui run build:linux
npm --prefix electron-ui run build:mac
npm --prefix electron-ui run build:win
# bun-based local bootstrap
./scripts/quick-start-bunx.sh
```

## Windows-Oriented Build References
- PowerShell variants exist for the build helpers: `./scripts/build-backend.ps1`, `./scripts/build-installer.ps1`, `./scripts/quick-start-bunx.ps1`, and `./scripts/build-windows-codex-proxy.ps1`.
- The Windows release workflow installs `python -m pip install -e . pyinstaller`, then runs `npm install` and `npm run build:win:bundle -- --x64` in `electron-ui/`; artifacts land under `dist/hwpx-mcp-backend/` and `dist/electron-installer/`.

## Lint And Typecheck Reality
- No repo-wide `ruff`, `black`, `isort`, `mypy`, or `pyright` command is configured in `pyproject.toml`.
- Do not invent formatting-only churn or add new tooling config unless the task requires it.
- Rely on targeted pytest runs and local diagnostics instead.

## Python Version And Test Discovery
- Target Python `>=3.10`.
- `asyncio_mode = auto` is enabled.
- Test discovery is rooted at `hwpx_mcp/tests`.
- Test files follow `test_*.py`.
- Test functions follow `test_*`.

## Import Style
- Follow the surrounding file instead of forcing a repo-wide import rewrite.
- Newer `agentic/` modules often use compact relative imports and modern typing.
- Older tool modules often use absolute package imports like `from hwpx_mcp.tools...`.
- Keep imports grouped as standard library, third-party, then local package imports.
- Avoid unused imports; this repo has many large modules, so import noise becomes expensive quickly.

## Formatting Style
- Use 4-space indentation.
- Match existing line wrapping in the touched file; many files are Black-like, but no formatter is enforced.
- Prefer trailing commas in multi-line literals and call sites when the file already uses them.
- Use short docstrings for public functions, classes, and MCP tools when the file already follows that pattern.
- Avoid drive-by reformatting in legacy files.

## Typing Style
- Prefer modern Python 3.10+ syntax in new code: `list[str]`, `dict[str, object]`, `str | None`, `Literal`, and `TypeAlias`.
- Match legacy `typing` imports such as `Optional`, `Dict`, and `Any` when editing older modules that already use that style.
- Do not mix old and new typing styles in the same small edit unless there is a clear payoff.
- Dataclasses are common in `agentic/`; Pydantic models appear in schema-facing modules.
- Keep tool return payloads JSON-friendly.

## Naming Conventions
- Tool registration helpers use `register_*_tools`.
- MCP tool functions are named `hwp_*`.
- Private helpers use a leading underscore.
- Types use `PascalCase`, regular names use `snake_case`, and constants use `UPPER_SNAKE_CASE`.
- Keep terminology aligned with existing capability names such as `Capability`, `GroupName`, `ToolRecord`, and `ServerConfig`.

## Error Handling Conventions
- In controller and core layers, prefer explicit exceptions for invalid state.
- Reuse existing domain errors such as `NotSupportedError`, `ConnectionError`, `DocumentNotOpenError`, and `HwpError`.
- Gate unsupported platform behavior explicitly instead of silently no-oping.
- In MCP tool wrappers, catch exceptions at the boundary, log them, and return stable error payloads.
- Preserve existing response shapes like `{"success": bool, "message": str}`, `{"status": "success" | "error", ...}`, `{"error": str}`, and additive payloads using keys like `count`, `path`, and `result`.
- Do not change response keys casually; gateway registry hashes and clients may depend on them.

## Logging Conventions
- Use module loggers from `logging.getLogger(...)`.
- Log `info` for startup, registration, or major state changes.
- Log `warning` for recoverable fallbacks, optional dependency gaps, or degraded platform behavior.
- Keep log messages specific and actionable.

## Testing Conventions
- Write tests with pytest, not unittest test cases.
- Async tests use `@pytest.mark.asyncio`.
- Mocking is commonly done with `unittest.mock` (`Mock`, `MagicMock`, `patch`).
- Keep assertions direct and specific; existing tests favor simple value checks over elaborate helpers.
- For routing and registry work, verify determinism, schema stability, and exact group/tool selection.

## Platform And Capability Rules
- Windows-only features must stay behind capability checks or platform guards.
- Cross-platform controllers should fail clearly for unsupported actions.
- Do not assume Hancom Office or COM exists outside Windows.
- HWPX creation and XML flows must remain usable on Linux/macOS.
- When adding features, update capability advertisement and error messages together.

## Working Rules For Agents
- Read the nearest nested `AGENTS.md` before making non-trivial changes in a subdirectory.
- Prefer surgical edits over broad rewrites.
- Preserve deterministic gateway behavior and schema hashes when touching `hwpx_mcp/agentic/`.
- Prefer extending existing registration modules over wiring new tools directly in `hwpx_mcp/server.py`.
- Do not commit generated outputs such as `.pytest_cache/`, `__pycache__/`, `.pdm-build/`, `dist/`, or installer artifacts.
- If you change commands or workflows, update the nearest relevant `AGENTS.md` in the same change.
- Keep shell and PowerShell script pairs behaviorally aligned, and preserve the Electron assumption that UI bootstrap talks to a `streamable-http` backend.

## Verification Checklist For Agents
- Run the narrowest useful pytest command first, then expand if needed.
- If you touch shared runtime wiring, run `pdm run test` unless the change is clearly isolated.
- Confirm new or changed tool wrappers still return the expected payload shape.
- For build-script or packaging changes, verify the corresponding script or workflow path you edited.

## Known Rough Edges To Respect
- The repository mixes older broad modules and newer typed modules; consistency within a file matters more than global purity.
- Some files use modern built-in generics, while older tool modules still use `typing.Dict` and `typing.Any`.
- `server.py` is large and contains legacy wiring; avoid making it even more central unless a task truly requires it.
- Build outputs and dependency directories such as `build/`, `dist/`, installer artifacts, and Electron installs should stay out of normal source changes unless the task explicitly targets them.
