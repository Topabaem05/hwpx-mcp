# electron-ui/

## Overview
Electron desktop shell for interacting with the backend MCP server over streamable HTTP.

## Where To Look
| Task | Location | Notes |
|------|----------|-------|
| App lifecycle and backend process | `main.js` | Finds backend executable/command, starts/stops process, IPC handlers |
| Stack bootstrap (backend + UI) | `scripts/start-stack.js` | Enforces streamable HTTP flow and endpoint readiness polling |
| Renderer/backend bridge | `preload.js` | Exposes safe IPC APIs and MCP URL config to renderer |
| Chat and MCP client loop | `src/renderer.js` | MCP initialize/tools/call flow + LLM/tool orchestration |
| Packaging and build targets | `package.json` | `start-stack`, `build:*`, bundled backend resources |

## Local Commands
```bash
npm --prefix electron-ui run start
npm --prefix electron-ui run start-stack
npm --prefix electron-ui run build:linux
```

## Conventions
- UI stack assumes backend transport `streamable-http`; keep this consistent across bootstrap code.
- Respect environment contract: `MCP_HOST`, `MCP_PORT`, `MCP_PATH`, `HWPX_MCP_HTTP_URL`, `HWPX_MCP_BACKEND_COMMAND`, `HWPX_MCP_START_BACKEND`.
- Keep backend bootstrap behavior aligned between `main.js` and `scripts/start-stack.js`.
- Renderer should call backend through MCP JSON-RPC methods (`initialize`, `tools/list`, `tools/call`) only.

## Boundaries
- `electron-ui/` owns desktop UX and process orchestration only.
- Backend tool semantics belong to `hwpx_mcp/`; do not duplicate backend logic in renderer/main.
- If backend endpoint contract changes, update both preload and renderer connection handling.

## Anti-Patterns
- Treating non-streamable transports as supported in Electron bootstrap paths.
- Hardcoding machine-specific backend paths in committed code.
- Diverging defaults between `preload.js`, `renderer.js`, and `start-stack.js` MCP URL behavior.
