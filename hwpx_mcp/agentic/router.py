from __future__ import annotations

from dataclasses import dataclass, field
from .models import GroupName, GroupRoute, ToolRecord, ToolScore
from .retrieval import HybridRetriever


@dataclass(slots=True)
class HierarchicalRouter:
    records: list[ToolRecord]
    group_top_k: int = 1
    tool_top_k: int = 8
    _retriever: HybridRetriever = field(init=False)

    def __post_init__(self) -> None:
        self._retriever = HybridRetriever(self.records)

    def route_group(self, query: str) -> GroupRoute:
        candidates = self._retriever.search(query=query, groups=None, top_k=max(self.tool_top_k, 12))
        if not candidates:
            return GroupRoute(group="other", reason="no matching tools", confidence=0.0)

        score_by_group: dict[GroupName, float] = {}
        for candidate in candidates:
            record = self._get_record(candidate.tool_id)
            if record:
                score_by_group[record.group] = score_by_group.get(record.group, 0.0) + candidate.score

        if not score_by_group:
            return GroupRoute(group="other", reason="empty score map", confidence=0.0)

        selected_group = max(score_by_group.items(), key=lambda item: item[1])[0]
        total_score = score_by_group[selected_group]
        confidence = total_score / (sum(score_by_group.values()) or 1.0)
        return GroupRoute(
            group=selected_group,
            reason=f"top aggregated score from {len(candidates)} candidates",
            confidence=confidence,
        )

    def select_tools(self, query: str, group: GroupName | None = None, top_k: int | None = None) -> list[ToolScore]:
        selected_group = group
        if selected_group is None:
            selected_group = self.route_group(query).group
        limit = top_k if top_k is not None else self.tool_top_k
        return self._retriever.search(query=query, groups=[selected_group], top_k=limit)

    def _get_record(self, tool_id: str) -> ToolRecord | None:
        for record in self.records:
            if record.tool_id == tool_id:
                return record
        return None
