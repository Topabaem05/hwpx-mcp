from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import TypedDict

from hwpx_mcp.agentic.gateway import AgenticGateway
from hwpx_mcp.agentic.gateway import BackendServer
from hwpx_mcp.agentic.models import GROUP_NAMES
from hwpx_mcp.agentic.models import GroupName


class QueryRow(TypedDict, total=False):
    query: str
    expected_group: GroupName
    expected_tools: list[str]


def load_queries(path: Path) -> list[QueryRow]:
    rows: list[QueryRow] = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            stripped = line.strip()
            if stripped:
                raw = json.loads(stripped)
                if isinstance(raw, dict):
                    rows.append(_to_query_row(raw))
    return rows


def _to_query_row(raw: dict[object, object]) -> QueryRow:
    row: QueryRow = {}
    query = raw.get("query")
    if isinstance(query, str):
        row["query"] = query

    expected_group = raw.get("expected_group")
    if isinstance(expected_group, str) and expected_group in GROUP_NAMES:
        row["expected_group"] = expected_group

    expected_tools_raw = raw.get("expected_tools")
    if isinstance(expected_tools_raw, list):
        expected_tools = [item for item in expected_tools_raw if isinstance(item, str)]
        row["expected_tools"] = expected_tools
    return row


async def evaluate(queries_path: Path, top_k: int) -> dict[str, float | int]:
    backend_mcp = _load_backend_mcp()
    gateway = AgenticGateway(backend_mcp)
    _ = await gateway.refresh_registry()

    queries = load_queries(queries_path)
    group_hits = 0
    tool_hits = 0

    for row in queries:
        query = row.get("query", "")
        expected_group = row.get("expected_group")
        expected_tools = set(row.get("expected_tools", []))

        routed = await gateway.tool_search(query=query, k=top_k)
        route = routed.get("route")
        routed_group = route.get("group") if isinstance(route, dict) else None
        if expected_group and routed_group == expected_group:
            group_hits += 1

        found_tools: set[str] = set()
        results = routed.get("results")
        if isinstance(results, list):
            for item in results:
                if isinstance(item, dict):
                    name = item.get("name")
                    if isinstance(name, str):
                        found_tools.add(name)
        if expected_tools.intersection(found_tools):
            tool_hits += 1

    total = len(queries) or 1
    return {
        "queries": len(queries),
        "group_accuracy": group_hits / total,
        "tool_recall_at_k": tool_hits / total,
        "top_k": top_k,
    }


def _load_backend_mcp() -> BackendServer:
    try:
        from hwpx_mcp.server import mcp as backend_mcp
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Cannot import hwpx_mcp.server dependencies. Install project extras first (e.g. pip install -e '.[dev]')."
        ) from exc
    return backend_mcp


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queries", default="hwpx_mcp/eval/queries.jsonl")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    metrics = asyncio.run(evaluate(Path(args.queries), int(args.top_k)))
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
