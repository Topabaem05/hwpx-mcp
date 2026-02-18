# hwpx_mcp/tests/

## Overview
Pytest suite covering controllers/tools and the agentic gateway.

## Where To Look
| Area | Location | Notes |
|------|----------|-------|
| Tool/controller tests | `hwpx_mcp/tests/test_controller_factory.py` + `hwpx_mcp/tests/test_cross_platform_controller.py` | capability matrix + cross-platform behavior
| Agentic gateway tests | `hwpx_mcp/tests/test_agentic_*.py` | registry/hash stability + router behavior

## Commands
```bash
pytest hwpx_mcp/tests/ -v
```

## Notes
- Async tests use pytest-asyncio (see `pyproject.toml` pytest config).
