# scripts/

## Overview
Automation scripts for build, installer packaging, workspace cleanup, and local UI/backend bootstrap.

## Structure
```
scripts/
├── build-backend.sh/.ps1         # PyInstaller backend build
├── build-installer.sh/.ps1       # full backend+Electron installer pipeline
├── build-windows-backend.sh      # self-contained Windows backend bundle
├── quick-start-bunx.sh/.ps1      # one-command local bootstrap
├── cleanup-workspace.sh/.ps1     # remove generated artifacts and caches
└── commit-push.sh/.ps1           # local git commit+push helper
```

## Where To Look
| Task | Location | Notes |
|------|----------|-------|
| Build backend binary | `build-backend.sh`, `build-backend.ps1` | Uses PyInstaller and writes `dist/hwpx-mcp-backend/` |
| Build installers | `build-installer.sh`, `build-installer.ps1` | Orchestrates backend build + Electron package build |
| Build Windows backend bundle | `build-windows-backend.sh` | Produces `dist/hwpx-mcp-backend-win/` with launcher scripts |
| Local bootstrap | `quick-start-bunx.sh`, `quick-start-bunx.ps1` | Installs deps and launches Electron stack |
| Cleanup artifacts | `cleanup-workspace.sh`, `cleanup-workspace.ps1` | Removes caches/build outputs and UI deps |

## Conventions
- Bash scripts use `set -euo pipefail`; PowerShell scripts use strict stop-on-error behavior.
- Keep POSIX and PowerShell script pairs behaviorally aligned when updating flows.
- Scripts assume repo-root-relative paths; preserve `REPO_ROOT` resolution patterns.
- Prefer explicit prerequisite checks (`uv`, `python`, `npm`, `bunx`, `wine`) with actionable error messages.

## Boundaries
- Scripts are local dev/build automation, not production deployment orchestration.
- Do not put business logic in scripts; keep logic in Python/Node code and use scripts as wrappers.
- Avoid adding interactive prompts in scripts used by CI/bootstrap paths.

## Anti-Patterns
- Changing output directories (`dist/...`) without updating Electron packaging references.
- Adding platform-specific behavior to only one of `.sh`/`.ps1` variants.
- Allowing partial-success behavior in build scripts after required step failures.
