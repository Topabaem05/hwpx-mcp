from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Protocol
from typing import cast

from .models import GROUP_NAMES
from .models import GroupName
from .models import JsonValue
from .models import ToolRecord
from .registry import build_registry
from .registry import ToolDumpable
from .registry import ToolProvider
from .router import HierarchicalRouter


class BackendServer(Protocol):
    async def list_tools(self) -> Sequence[ToolDumpable]: ...

    async def call_tool(self, name: str, arguments: dict[str, JsonValue]) -> object: ...


class AgenticGateway:
    def __init__(self, backend_server: BackendServer):
        self.backend_server: BackendServer = backend_server
        self.registry: list[ToolRecord] = []
        self._router: HierarchicalRouter | None = None

    async def refresh_registry(self) -> dict[str, object]:
        self.registry = await build_registry(cast(ToolProvider, self.backend_server))
        self._router = HierarchicalRouter(self.registry)
        return {
            "success": True,
            "count": len(self.registry),
        }

    async def tool_search(self, query: str, k: int = 8, group: str | None = None) -> dict[str, object]:
        await self._ensure_registry()
        assert self._router is not None

        selected_group = self._parse_group(group)
        if group and selected_group is None:
            return {"success": False, "message": f"invalid group: {group}"}

        if selected_group is not None:
            scores = self._router.select_tools(query=query, group=selected_group, top_k=k)
            group_route: dict[str, object] = {
                "group": selected_group,
                "reason": "user_selected",
                "confidence": 1.0,
            }
        else:
            route = self._router.route_group(query)
            scores = self._router.select_tools(query=query, group=route.group, top_k=k)
            group_route = {
                "group": route.group,
                "reason": route.reason,
                "confidence": route.confidence,
            }

        records = [self._record_from_id(score.tool_id) for score in scores]
        results = [
            {
                "tool_id": record.tool_id,
                "name": record.name,
                "description": record.description,
                "group": record.group,
                "score": score.score,
                "reason": score.reason,
            }
            for score, record in zip(scores, records, strict=True)
            if record is not None
        ]
        return {"success": True, "query": query, "route": group_route, "results": results}

    async def tool_describe(self, tool_id: str) -> dict[str, object]:
        await self._ensure_registry()
        record = self._record_from_id(tool_id)
        if record is None:
            return {"success": False, "message": f"tool_id not found: {tool_id}"}

        return {
            "success": True,
            "tool": {
                "tool_id": record.tool_id,
                "name": record.name,
                "description": record.description,
                "group": record.group,
                "tags": list(record.tags),
                "input_schema": record.input_schema,
                "output_schema": record.output_schema,
                "schema_hash": record.schema_hash,
            },
        }

    async def tool_call(self, tool_id: str, arguments: dict[str, JsonValue]) -> dict[str, object]:
        await self._ensure_registry()
        record = self._record_from_id(tool_id)
        if record is None:
            return {"success": False, "message": f"tool_id not found: {tool_id}"}

        raw = await self.backend_server.call_tool(record.name, arguments)
        return {
            "success": True,
            "tool_id": tool_id,
            "tool_name": record.name,
            "result": self._normalize_tool_result(raw),
        }

    async def route_and_call(
        self,
        query: str,
        arguments: dict[str, JsonValue] | None = None,
        top_k: int = 1,
    ) -> dict[str, object]:
        await self._ensure_registry()
        assert self._router is not None

        arguments = arguments or {}
        route = self._router.route_group(query)
        candidates = self._router.select_tools(query=query, group=route.group, top_k=max(top_k, 1))
        if not candidates:
            return {
                "success": False,
                "route": {"group": route.group, "reason": route.reason, "confidence": route.confidence},
                "message": "no candidate tools found",
            }

        selected = candidates[0]
        record = self._record_from_id(selected.tool_id)
        if record is None:
            return {"success": False, "message": "selected tool missing from registry"}

        raw = await self.backend_server.call_tool(record.name, arguments)
        return {
            "success": True,
            "route": {"group": route.group, "reason": route.reason, "confidence": route.confidence},
            "selected": {
                "tool_id": record.tool_id,
                "name": record.name,
                "score": selected.score,
            },
            "result": self._normalize_tool_result(raw),
        }

    async def _ensure_registry(self) -> None:
        if not self.registry:
            _ = await self.refresh_registry()

    def _record_from_id(self, tool_id: str) -> ToolRecord | None:
        for record in self.registry:
            if record.tool_id == tool_id:
                return record
        return None

    @staticmethod
    def _parse_group(group: str | None) -> GroupName | None:
        if group is None:
            return None
        if group in GROUP_NAMES:
            return group
        return None

    @staticmethod
    def _normalize_tool_result(result: object) -> object:
        if isinstance(result, list):
            normalized: list[object] = []
            for item in result:
                text = getattr(item, "text", None)
                if isinstance(text, str):
                    try:
                        normalized.append(json.loads(text))
                    except json.JSONDecodeError:
                        normalized.append(text)
                elif hasattr(item, "model_dump"):
                    normalized.append(item.model_dump())
                else:
                    normalized.append(item)
            return normalized
        return result
