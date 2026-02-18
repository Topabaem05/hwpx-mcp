# PRD: One-Command Distribution (Windows-first, with cross-platform path)

## 1) Background

- The current distribution has two practical entry points:
  - Python package install (`uv pip install -e .` / `pip install -e .`) for CLI usage.
  - Electron bootstrap scripts (`npm run start-stack`, `start-stack-windows.bat/ps1`) for UI + backend together.
- The Electron bootstrap already provides much of the one-command runtime behavior, but it is still a dev-oriented flow:
  - It expects the repo checkout to exist.
  - It depends on backend environment availability (`uv` or `python`) in PATH.
- Existing packaging configuration in `electron-ui/package.json` already includes `build:win` and `build:dir` with NSIS settings.
- `gateway_server.py` remains `stdio`-only and must be treated separately from UI bootstrap.

## 2) Problem

Users should be able to run HWPX-MCP with minimum manual setup from fresh machines.

- For quick desktop workflow: one-command launch should start MCP backend and Electron UI.
- For frictionless onboarding: ideally `npm install` + one command should be close to zero manual wiring.
- For wider distribution: optional `.exe` installer should reduce setup burden for non-technical users.

## 2.1) Delivery Reality (npm install + exe options)

There are two practical packaging tracks for user onboarding:

- **Track A: npm wrapper + Python runtime**
  - Ship a small Node wrapper package that resolves and runs `python -m hwpx_mcp.server` / `uv run hwpx-mcp`.
  - Pros: small package size, fast releases, easy update path.
  - Cons: requires Python and compatible runtime on target machine.

- **Track B: Python executable backend + Electron wrapper**
  - Ship one or more platform-built backend executables (PyInstaller/Nuitka/cx_Freeze style) and launch from Electron or a lightweight wrapper.
  - Pros: one-command startup without Python install for most users.
  - Cons: bigger package, more build/signing overhead, slower iteration.

This PRD treats Track A as baseline (`start-stack` flow with documented prerequisites) and Track B as phase-3 distribution goal.

## 3) Vision & Scope

### Vision

Deliver two progressively richer user experiences:

1. **Fast UX (today):** one-command local bootstrap from repo checkout using existing Node scripts.
2. **User-ready UX (next):** packaged installer path where end users run a binary and get UI + backend bootstrap experience.

### Scope

- Focus on the Electron shell path first (Windows primary target).
- Preserve existing MCP behavior and transport rules.
- Keep backend logic unchanged unless needed for deterministic launch validation.

## 4) User Outcomes

- Non-technical Windows users can run the tool with no manual terminal juggling.
- Developers can still run reproducible dev bootstrap (`start-stack`) with configurable backend command.
- Product can later add a real bundled backend artifact without rewriting the UI bootstrap layer.

## 5) Non-Goals

- No backend protocol changes in this phase.
- No routing/schema changes to MCP tools for this effort.
- No platform-specific behavior in templates or Linux-only assumptions.

## 6) Requirement Matrix

### R1: Fast One-Command UX (Existing bootstrap hardening)

#### Mandatory behavior

- `npm run start-stack` in `electron-ui/` should start both processes (backend + Electron UI).
- If Electron dependency is missing, auto-install should run once (`HWPX_ELECTRON_AUTO_INSTALL` override remains available).
- Backend must run streamable-http for UI compatibility.
- Startup should fail with clear errors if prerequisites are missing (`uv` and Python alternatives).

#### Acceptance

- Backend starts and becomes reachable at `${MCP_HOST}:${MCP_PORT}${MCP_PATH}`.
- Electron opens after endpoint availability.
- Existing env overrides still work:
  - `HWPX_MCP_BACKEND_COMMAND`
  - `HWPX_MCP_HTTP_URL`
  - `OPEN_WEBUI_URL`
  - `HWPX_MCP_START_BACKEND`

### R2: "npm install to run" UX (near-immediate onboarding)

#### Mandatory behavior

- Provide a documented single path for Windows users where first run is driven by one command after dependency install.
- Clearly separate assumptions:
  - `npm install` in `electron-ui` can satisfy UI binary prerequisites.
  - Python MCP runtime still needs Python/uv and backend package availability, unless bundled in installer.
- Add top-level guidance + optional script scaffold to normalize this gap.

#### Acceptance

- A person can follow one short documented flow from a fresh machine that includes
  both npm and Python setup.
- Documentation must explicitly state what is required to reach true `npm install`-only end-state.

### R3: `.exe` Packaging Path

#### Mandatory behavior

- Keep current `electron-builder` config in place and verify script discoverability.
- Produce a deterministic Windows installer artifact (`NSIS`) as documented output.
- Ship installer entry that launches packaged Electron shell.
- Include explicit notes for backend startup path and first-run prerequisites.

#### Acceptance

- `npm run build:win` succeeds in CI/Windows environments.
- Generated installer exists at expected path.
- Launch flow remains user-guided for backend if backend binary is not bundled.

### R4: Security, Determinism, Compatibility

- No nondeterministic routing or shared mutable state changes.
- Keep transport constraints untouched:
  - UI path uses streamable HTTP.
  - Gateway remains stdio-only for now.
- Preserve Windows-only capability boundaries and non-Windows feature limits.

## 7) Proposed Delivery Plan

### Phase 1 (Now): Hardened one-command repo bootstrap

1. Publish/confirm a short command sequence in docs:
   - install backend deps in Python env (`uv pip install -e .`),
   - install UI deps (`npm install` in `electron-ui`),
   - run `npm run start-stack` from `electron-ui`.
2. Improve failure messaging in bootstrap docs for common errors:
   - missing `uv`/`python`,
   - already-used ports,
   - sandbox failures on Linux/headless.
3. Keep `start-stack-windows.bat` / `.ps1` as compatibility entry points.

### Phase 2 (Next): Installer foundation

1. Keep and validate electron-builder config values:
   - `appId`, `productName`, `directories.output`, `win.target`, `artifactName`.
2. Add release script/docs that describe required host environment and backend mode.
3. Add CI job that runs:
   - `npm ci`
   - `npm run build:win`
   - artifact presence assertion.

### Phase 3 (Target): True one-command non-dev UX

1. Evaluate and decide backend delivery model:
   - bundling Python backend executable,
   - or lightweight local service bootstrap + installer-managed runtime dependency.
2. Add installer UX that checks and auto-wires backend prerequisites.
3. Update all docs for user-level install path.

## 8) Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| `npm install` alone still misses backend deps | Explicitly document and enforce prerequisite check; phase into backend bundling before claiming full npm-only run |
| `uv` absent in Windows labs | Keep fallback to `python3`/`python` and explicit error path |
| Electron package build on non-Windows | Build docs enforce Windows runner or explicit Wine requirement |
| Backend not ready when Electron starts | Keep endpoint probing and clear timeout failure messaging |
| Gateway behavior confusion | Keep docs clear: UI path != gateway path |

## 9) Out-of-Scope Validation Matrix

- Unit/integration tests are unchanged for this PRD deliverable.
- Distribution acceptance is validated by manual smoke run + build artifact checks.
- No change to MCP tool schemas in this phase.

## 10) Success Criteria

- `WINDOWS_DISTRIBUTION_PRD.md` defines both tracks and exact tradeoffs:
  - `npm run start-stack` fast UX,
  - installer path with prerequisites,
  - true npm-only UX as planned roadmap.
- Docs and scripts are aligned with current environment variables and existing bootstrap behavior.
- Release path can start from Windows and be executed by one-command script without manual multi-terminal setup.
- No transport/security/regression behavior changes in existing MCP core.

## 11) References

- `electron-ui/package.json` scripts and build config
- `electron-ui/scripts/start-stack.js`
- `start-stack-windows.bat`
- `start-stack-windows.ps1`
- `README.md` and `README.kr.md` sections for quick start and troubleshooting
- `hwpx_mcp/gateway_server.py` transport limitation: stdio-only
