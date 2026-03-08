# apps/agent-chat/

## Overview
Standalone Bun/Vite/Electron chat client prototype with a renderer UI and Electron main/preload process split.

## Where To Look
| Task | Location | Notes |
|------|----------|-------|
| Dev workflow | `apps/agent-chat/package.json` | concurrent renderer + electron startup, typecheck/build scripts |
| Electron app lifecycle | `apps/agent-chat/electron/main.ts` | packaged vs dev URL loading behavior |
| Renderer app shell | `apps/agent-chat/renderer/src/app.ts` | conversation state, composer actions, streaming UI |
| Tool/agent stub behavior | `apps/agent-chat/renderer/src/agent/stubAgent.ts` | simulated streamed assistant output |

## Conventions
- Keep renderer and electron process concerns separated (`renderer/` vs `electron/`).
- Use Bun-driven scripts from `package.json` for local dev/build/typecheck.
- Preserve strict TS configs split by target (`tsconfig.renderer.json`, `tsconfig.electron.json`).

## Commands
```bash
cd apps/agent-chat
bun install
bun run dev
bun run typecheck
bun run build
```

## Anti-Patterns
- Do not import Node/Electron-only modules directly inside renderer UI files.
- Do not bypass typecheck scripts when changing shared app types.
- Do not duplicate backend transport bootstrap here; coordinate with `electron-ui` stack scripts.
