from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
import math
import re

from .models import GroupName, ToolRecord, ToolScore

TOKEN_PATTERN = re.compile(r"[a-z0-9_]+")


def _tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text.lower())


@dataclass(slots=True)
class LexicalRetriever:
    records: Sequence[ToolRecord]
    k1: float = 1.5
    b: float = 0.75
    _term_frequencies: list[Counter[str]] = field(init=False, repr=False)
    _doc_lengths: list[int] = field(init=False, repr=False)
    _idf: dict[str, float] = field(init=False, repr=False)
    _avg_doc_length: float = field(init=False, repr=False)

    def __post_init__(self) -> None:
        frequencies: list[Counter[str]] = []
        doc_lengths: list[int] = []
        document_frequencies: Counter[str] = Counter()

        for record in self.records:
            tokens = _tokenize(record.search_blob())
            term_frequency = Counter(tokens)
            frequencies.append(term_frequency)
            doc_lengths.append(len(tokens))
            for token in term_frequency:
                document_frequencies[token] += 1

        total_docs = max(len(self.records), 1)
        self._term_frequencies = frequencies
        self._doc_lengths = doc_lengths
        self._avg_doc_length = (sum(doc_lengths) / len(doc_lengths)) if doc_lengths else 1.0
        self._idf = {
            token: math.log(1.0 + (total_docs - count + 0.5) / (count + 0.5))
            for token, count in document_frequencies.items()
        }

    def search(self, query: str, groups: Sequence[GroupName] | None = None, top_k: int = 12) -> list[ToolScore]:
        if top_k <= 0:
            return []
        group_filter = set(groups or [])
        query_terms = set(_tokenize(query))
        scores: list[ToolScore] = []

        for index, record in enumerate(self.records):
            if group_filter and record.group not in group_filter:
                continue
            tf = self._term_frequencies[index]
            doc_length = self._doc_lengths[index] if self._doc_lengths else 0
            score = 0.0
            for term in query_terms:
                term_frequency = tf.get(term, 0)
                if term_frequency <= 0:
                    continue
                idf = self._idf.get(term, 0.0)
                denominator = term_frequency + self.k1 * (
                    1.0 - self.b + self.b * (doc_length / self._avg_doc_length)
                )
                score += idf * ((term_frequency * (self.k1 + 1.0)) / denominator)
            if score > 0:
                scores.append(ToolScore(tool_id=record.tool_id, score=score, reason="lexical"))

        scores.sort(key=lambda item: (-item.score, item.tool_id))
        return scores[:top_k]


@dataclass(slots=True)
class SemanticRetriever:
    records: Sequence[ToolRecord]

    def search(self, query: str, groups: Sequence[GroupName] | None = None, top_k: int = 12) -> list[ToolScore]:
        if top_k <= 0:
            return []
        query_tokens = set(_tokenize(query))
        group_filter = set(groups or [])
        results: list[ToolScore] = []

        for record in self.records:
            if group_filter and record.group not in group_filter:
                continue
            record_tokens = set(_tokenize(record.search_blob()))
            if not record_tokens:
                continue
            intersection = len(query_tokens.intersection(record_tokens))
            union = len(query_tokens.union(record_tokens)) or 1
            score = intersection / union
            if score > 0:
                results.append(ToolScore(tool_id=record.tool_id, score=score, reason="semantic"))

        results.sort(key=lambda item: (-item.score, item.tool_id))
        return results[:top_k]


@dataclass(slots=True)
class HybridRetriever:
    records: Sequence[ToolRecord]
    lexical_weight: float = 0.65
    semantic_weight: float = 0.35
    lexical: LexicalRetriever = field(init=False)
    semantic: SemanticRetriever = field(init=False)

    def __post_init__(self) -> None:
        self.lexical = LexicalRetriever(self.records)
        self.semantic = SemanticRetriever(self.records)

    def search(self, query: str, groups: Sequence[GroupName] | None = None, top_k: int = 12) -> list[ToolScore]:
        pool = max(top_k * 3, top_k)
        lexical_scores = self.lexical.search(query=query, groups=groups, top_k=pool)
        semantic_scores = self.semantic.search(query=query, groups=groups, top_k=pool)

        by_id: dict[str, float] = {}
        lexical_norm = _normalize(lexical_scores)
        semantic_norm = _normalize(semantic_scores)

        for score in lexical_scores:
            by_id[score.tool_id] = by_id.get(score.tool_id, 0.0) + (
                self.lexical_weight * lexical_norm.get(score.tool_id, 0.0)
            )
        for score in semantic_scores:
            by_id[score.tool_id] = by_id.get(score.tool_id, 0.0) + (
                self.semantic_weight * semantic_norm.get(score.tool_id, 0.0)
            )

        merged = [ToolScore(tool_id=tool_id, score=value, reason="hybrid") for tool_id, value in by_id.items()]
        merged.sort(key=lambda item: (-item.score, item.tool_id))
        return merged[:top_k]


def _normalize(scores: Sequence[ToolScore]) -> dict[str, float]:
    max_score = max((item.score for item in scores), default=0.0)
    if max_score <= 0:
        return {item.tool_id: 0.0 for item in scores}
    return {item.tool_id: item.score / max_score for item in scores}
