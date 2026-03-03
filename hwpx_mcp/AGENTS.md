# hwpx_mcp/

## Overview
Python package containing backend runtime, deterministic gateway, tool modules, XML helpers, and test suite.

Inherits root conventions; this file records `hwpx_mcp/`-local boundaries only.

## Where To Look
| Task | Location | Notes |
|------|----------|-------|
| Backend bootstrap | `server.py`, `config.py` | Runtime transport selection and server run path |
| Gateway bootstrap | `gateway_server.py` | stdio-only gateway process for deterministic surface |
| Tool APIs | `tools/` | Registration modules + platform controllers |
| Routing internals | `agentic/` | Registry, grouping, retrieval, routing, gateway wrappers |
| XML helpers | `core/`, `features/` | Secure parser/validator + smart query/edit |
| Eval and tests | `eval/`, `tests/` | Offline routing eval + pytest regression suite |

## Conventions
- `server.py` remains composition root; feature/tool logic should live outside it.
- Prefer module registration (`register_*_tools`) and keep `server.py` wiring-focused.
- Keep gateway paths deterministic; no request-time randomization/stateful routing shortcuts.
- XML parse/edit flows must route through `core/xml_parser.py` + `core/validator.py`.

## Local Boundaries
- `tools/` owns capability-specific business logic and platform branching.
- `agentic/` owns deterministic retrieval and route scoring; keep state-free and reproducible.
- `core/` + `features/` own XML-level safety/transform/query utilities.

## Anti-Patterns
- Registering/implementing new tool logic directly in `server.py`.
- Adding nondeterministic behavior to routing/retrieval paths.
- Bypassing `core/xml_parser.py` for XML parse/edit operations.

## Related
- Root shared rules: `AGENTS.md`
- Tool-layer specifics: `hwpx_mcp/tools/AGENTS.md`
- Routing/gateway specifics: `hwpx_mcp/agentic/AGENTS.md`
