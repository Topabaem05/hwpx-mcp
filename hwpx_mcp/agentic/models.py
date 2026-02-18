from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from typing import TypeAlias

GroupName = Literal[
    "document_lifecycle",
    "text_insertion",
    "table_chart",
    "field_meta",
    "find_replace",
    "xml_direct",
    "export_convert",
    "util_debug",
    "other",
]

GROUP_NAMES: tuple[GroupName, ...] = (
    "document_lifecycle",
    "text_insertion",
    "table_chart",
    "field_meta",
    "find_replace",
    "xml_direct",
    "export_convert",
    "util_debug",
    "other",
)

JsonPrimitive: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonPrimitive | list["JsonValue"] | dict[str, "JsonValue"]


@dataclass(frozen=True, slots=True)
class ToolRecord:
    tool_id: str
    name: str
    description: str
    input_schema: dict[str, JsonValue]
    output_schema: dict[str, JsonValue] | None
    group: GroupName
    tags: tuple[str, ...]
    schema_hash: str

    def search_blob(self) -> str:
        return f"{self.name} {self.description} {' '.join(self.tags)}"


@dataclass(frozen=True, slots=True)
class GroupRoute:
    group: GroupName
    reason: str
    confidence: float


@dataclass(frozen=True, slots=True)
class ToolScore:
    tool_id: str
    score: float
    reason: str
