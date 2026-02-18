from __future__ import annotations

import asyncio
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from typing import Mapping
from typing import Protocol
from typing import Sequence

from .grouping import classify_group
from .models import JsonValue
from .models import ToolRecord


class ToolDumpable(Protocol):
    def model_dump(self) -> Mapping[str, object]: ...


class ToolProvider(Protocol):
    async def list_tools(self) -> Sequence[ToolDumpable]: ...


def _stable_hash(payload: Mapping[str, JsonValue]) -> str:
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


def _detect_tags(tool_name: str, description: str) -> tuple[str, ...]:
    lowered = f"{tool_name} {description}".lower()
    tags: list[str] = []
    if "windows" in lowered:
        tags.append("windows-only")
    if any(token in lowered for token in ("xml", "xpath", "hwpx")):
        tags.append("xml")
    if any(token in lowered for token in ("pdf", "html", "convert", "export")):
        tags.append("export")
    if not tags:
        tags.append("generic")
    return tuple(tags)


def _to_json_object(value: object) -> dict[str, JsonValue]:
    if isinstance(value, dict):
        return {str(key): _to_json_value(item) for key, item in value.items()}
    return {}


def _to_json_value(value: object) -> JsonValue:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, list):
        return [_to_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _to_json_value(item) for key, item in value.items()}
    return str(value)


def _convert_tool(tool_dump: Mapping[str, object]) -> ToolRecord:
    name = str(tool_dump.get("name", "")).strip()
    description = str(tool_dump.get("description", "")).strip()
    input_schema = _to_json_object(tool_dump.get("inputSchema", {}))
    output_schema_value = tool_dump.get("outputSchema")
    output_schema = _to_json_object(output_schema_value) if isinstance(output_schema_value, dict) else None
    group = classify_group(name, description)
    tags = _detect_tags(name, description)
    schema_hash = _stable_hash(
        {
            "name": name,
            "inputSchema": input_schema,
            "outputSchema": output_schema,
        }
    )
    tool_id = f"{name}:{schema_hash}"
    return ToolRecord(
        tool_id=tool_id,
        name=name,
        description=description,
        input_schema=input_schema,
        output_schema=output_schema,
        group=group,
        tags=tags,
        schema_hash=schema_hash,
    )


async def build_registry(server: ToolProvider) -> list[ToolRecord]:
    tools = await server.list_tools()
    records = [_convert_tool(tool.model_dump()) for tool in tools]
    return sorted(records, key=lambda record: record.name)


def build_registry_sync(server: ToolProvider) -> list[ToolRecord]:
    return asyncio.run(build_registry(server))


def save_registry_jsonl(records: list[ToolRecord], output_path: str | Path) -> Path:
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as file:
        for record in records:
            _ = file.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")
    return target
