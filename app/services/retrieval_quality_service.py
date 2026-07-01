from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, List, Sequence

from app.services.vector_store import VectorSearchResult


def _normalize_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _tokenize(parts: Iterable[str]) -> set[str]:
    tokens = set()
    for part in parts:
        for token in part.lower().replace(",", " ").split():
            cleaned = token.strip(" .!?;:-()[]{}\"'")
            if len(cleaned) >= 3:
                tokens.add(cleaned)
    return tokens


def _normalized_text(text: str) -> str:
    return " ".join(text.lower().split())


@dataclass
class RankedMemoryResult:
    result: VectorSearchResult
    rerank_score: float
    reasons: List[str]


def rerank_memory_results(
    results: Sequence[VectorSearchResult],
    user_id: int,
    query_text: str,
    interests: Sequence[str] | None = None,
    themes: Sequence[str] | None = None,
    top_k: int = 3,
) -> List[RankedMemoryResult]:
    interests = interests or []
    themes = themes or []
    keywords = _tokenize([query_text, *interests, *themes])
    ranked: List[RankedMemoryResult] = []

    for result in results:
        if result.metadata.get("user_id") != user_id:
            continue

        text = result.text or ""
        normalized = _normalized_text(text)
        if not normalized:
            continue

        reasons: List[str] = [f"vector={result.score:.2f}"]
        score = result.score

        overlap = sum(1 for keyword in keywords if keyword in normalized)
        if overlap:
            score += overlap * 0.3
            reasons.append(f"keyword_overlap={overlap}")

        if interests or themes:
            context_overlap = sum(1 for keyword in _tokenize([*interests, *themes]) if keyword in normalized)
            if context_overlap:
                score += context_overlap * 0.2
                reasons.append(f"context_overlap={context_overlap}")

        if len(normalized) < 25:
            score -= 0.35
            reasons.append("short_snippet_penalty")

        timestamp = _normalize_datetime(result.metadata.get("updated_at")) or _normalize_datetime(
            result.metadata.get("created_at")
        )
        if timestamp is not None:
            age_days = max(0.0, (datetime.now(timezone.utc) - timestamp).total_seconds() / 86400)
            freshness_bonus = max(0.0, 0.25 - min(age_days, 30) / 120)
            if freshness_bonus > 0:
                score += freshness_bonus
                reasons.append("freshness_bonus")

        ranked.append(RankedMemoryResult(result=result, rerank_score=score, reasons=reasons))

    ranked.sort(
        key=lambda item: (
            item.rerank_score,
            len(_normalized_text(item.result.text)),
        ),
        reverse=True,
    )

    deduped: List[RankedMemoryResult] = []
    seen_texts: set[str] = set()
    for item in ranked:
        normalized = _normalized_text(item.result.text)
        if normalized in seen_texts:
            continue
        seen_texts.add(normalized)
        deduped.append(item)

    return deduped[:top_k]
