# hwpx_mcp/tools/

## Overview
Platform abstraction layer + MCP tool registration. Windows uses a COM-backed controller; cross-platform uses an HWPX builder.

## Where To Look
| Task | Location | Notes |
|------|----------|-------|
| Unified MCP tool surface | `hwpx_mcp/tools/unified_tools.py` | registers many `hwp_*` tools; wraps controller API
| Controller contract + types | `hwpx_mcp/tools/hwp_controller_base.py` | `Platform`, `Capability`, `HwpControllerBase`, errors
| Platform selection | `hwpx_mcp/tools/controller_factory.py` | singleton `get_controller()` + capability matrix
| Cross-platform controller | `hwpx_mcp/tools/cross_platform_controller.py` | HWPX-only; uses `HwpxBuilder`
| Windows controller | `hwpx_mcp/tools/windows_hwp_controller_v2.py` | Windows-only; broad feature surface
| HWPX construction | `hwpx_mcp/tools/hwpx_builder.py` | tables/images/charts; saves HWPX

## Conventions
- Capability gating: implement new functionality by adding a `Capability` and advertising it via controller `capabilities`.
- Errors: unsupported ops should raise `NotSupportedError(capability=..., current_platform=...)`.
- Tool registration pattern: `def register_X_tools(mcp, ...) -> None:` then define `@mcp.tool()` functions inside.

## Common Pitfalls
- Cross-platform cannot open existing docs (`open_document` raises); only supports creating/saving HWPX.
- Cross-platform `save_document()` needs a path at least once; otherwise it raises.
- Keep tool wrapper responses stable (dicts with `success`/`status` + `message`) because clients may depend on shapes.
