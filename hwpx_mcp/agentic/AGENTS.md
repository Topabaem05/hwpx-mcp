# hwpx_mcp/agentic/

## Overview
Deterministic Tool-RAG gateway: builds a registry of backend tools, retrieves candidates, routes by group, and calls a selected tool.

## Where To Look
| Task | Location | Notes |
|------|----------|-------|
| Public gateway behavior | `hwpx_mcp/agentic/gateway.py` | `tool_search`, `tool_describe`, `tool_call`, `route_and_call`
| Registry build + IDs | `hwpx_mcp/agentic/registry.py` | tool_id = `name:schema_hash`; JSON schema normalization
| Grouping rules | `hwpx_mcp/agentic/grouping.py` | maps tool name/description -> group
| Routing logic | `hwpx_mcp/agentic/router.py` | aggregates retriever scores per group; selects candidates
| Retrieval implementation | `hwpx_mcp/agentic/retrieval.py` | hybrid retrieval over tool records

## Conventions
- Tool identity is schema-sensitive: changes to input/output schema change `schema_hash` and thus `tool_id`.
- Gateway expects a backend server implementing `list_tools()` + `call_tool()` (see `BackendServer` protocol).

## Anti-Patterns
- Don’t make routing depend on nondeterministic state; Phase 1 is intended to be deterministic and testable.
