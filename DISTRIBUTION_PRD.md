# Product Requirements: Cross-Platform Distribution and One-Command Runtime

## 1) Why this PRD exists

The repo already has a strong bootstrap path for UI + backend (`npm run start-stack`, `start-stack-windows.bat/.ps1`) and a Windows-focused shipping plan (`WINDOWS_DISTRIBUTION_PRD.md`).

What is still missing is a clear cross-platform product plan for two onboarding goals:

- **Near-immediate onboarding**: users can run backend + Electron UI with one command after dependency installation.
- **Long-term installation**: users install/use a packaged executable flow with minimal manual setup.

## 2) Delivery tracks

### Track A — Node wrapper + Python runtime (current baseline)

- Run-time model: `npm` command starts Electron flow and spawns backend through `HWPX_MCP_BACKEND_COMMAND` (`uv run hwpx-mcp` by default).
- Requirements: Python/uv present on the target machine, `uv pip install -e .` (or equivalent Python install), and Node dependencies for Electron.
- User friction: lower than raw scripts because one command can orchestrate backend and UI startup, but not fully npm-only.

### Track B — Packaged backend distribution (future phase)

- Run-time model: package backend artifact (e.g., PyInstaller/Nuitka/cx_Freeze output) and launch it from Electron/start-stack launcher.
- Requirements: fewer target dependencies and simpler first run for non-technical users.
- User friction: higher release complexity (build/signing, larger artifacts).

## 3) Scope and constraints

- **In scope**
  - User-facing distribution, installation docs, and launch semantics.
  - Installer and one-command entrypoint strategy.
  - Cross-platform rollout sequencing.

- **Out of scope**
  - Changing MCP tool schemas or transport behavior.
  - Gateway protocol redesign (gateway remains stdio-oriented for phase 1).
  - Feature regressions in backend controllers.

- **Hard constraints**
  - Electron path requires streamable HTTP endpoint.
  - Gateway path remains stdio-only (`hwpx-mcp-gateway`).
  - Windows COM behavior remains Windows-only.

## 4) Required user flows

### F1: Linux/macOS (current bootstrap)

- One-command entry: `cd electron-ui && npm run start-stack`
- Behavior required:
  - Auto-install UI deps when missing (`npm install`) unless disabled.
  - Launch backend and wait for endpoint.
  - Launch Electron with `OPEN_WEBUI_URL` and `HWPX_MCP_HTTP_URL`.
  - Graceful shutdown of backend and UI on exit.

### F2: Windows (current bootstrap)

- One-command entry: `start-stack-windows.bat` or `start-stack-windows.ps1`.
- Behavior required:
  - Backend command resolution (`uv` preferred, Python fallback).
  - Optional gateway terminal start.
  - Backend/UI env wiring without manual terminal juggling.

### F3: Packaged path

- Installer should include Electron shell and a documented launch contract for backend startup.
- If backend not bundled in phase 2, installer explicitly documents prerequisite path.

## 5) Risks and mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| No true npm-only execution without backend bundling | Confuses onboarding expectation | Keep docs explicit: Track A needs Python/uv; Track B removes dependency |
| Non-deterministic launcher behavior across OS | Hard to support users at scale | Enforce single canonical env contract and health-check behavior |
| Streamable transport mismatch for UI | UI fail-to-connect | Keep launch-time validation and explicit `MCP_TRANSPORT=streamable-http` in bootstrap |
| Backend process startup timeout | App appears hung | Keep fixed timeout + clear actionable error with ports/dependency checks |

## 6) Planned rollout

### Phase 1 (docs and launch parity)

- Finalize cross-platform distribution matrix in `README.md` and `README.kr.md`.
- Publish one-command onboarding checklist for Track A on all platforms.
- Keep existing `start-stack` and `start-stack-windows.*` as canonical local flows.

### Phase 2 (installer groundwork)

- Keep Windows NSIS path in `electron-ui/package.json` as canonical target for phase 2.
- Add CI packaging job for Windows artifact generation and artifact assertion.
- Add launch-time contract and first-run backend setup notes in docs.

### Phase 3 (backend packaging)

- Evaluate backend artifacting strategy (Track B).
- Wire launcher to support bundled backend mode.
- Reduce dependency assumptions for end users and publish migration guidance.

## 7) Acceptance criteria

- Track A flows are documented and stable for current entrypoints on Linux/macOS and Windows.
- User docs explicitly separate Track A and Track B assumptions.
- New PRD references (`DISTRIBUTION_PRD.md`) and Windows details (`WINDOWS_DISTRIBUTION_PRD.md`) align and do not contradict transport constraints.
- Packaging work can be validated by:
  - `npm run build:win` (when Windows runner is available),
  - expected artifact path check,
  - launch guidance review.

## 8) References

- `WINDOWS_DISTRIBUTION_PRD.md`
- `electron-ui/package.json`
- `electron-ui/scripts/start-stack.js`
- `start-stack-windows.bat`, `start-stack-windows.ps1`
- `README.md`, `README.kr.md`
- `hwpx_mcp/config.py`, `hwpx_mcp/server.py`, `hwpx_mcp/gateway_server.py`
