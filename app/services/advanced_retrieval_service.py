from dataclasses import dataclass
from datetime import datetime, timezone
from time import perf_counter
from typing import Optional, Sequence

from sqlalchemy.orm import Session

from app.db_models import Contact, Event, Feedback, FollowUp, Interaction
from app.services.network_graph_service import get_network_graph_insights
from app.services.metrics_service import get_metrics_service
from app.services.personalization_service import get_personalization_profile
from app.services.retrieval_quality_service import rerank_memory_results
from app.services.semantic_memory_service import semantic_search_memories
from app.services.user_data_snapshot import get_user_data_snapshot
from app.services.vector_store import VectorSearchResult


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _split_csv(value: Optional[str]) -> list[str]:
    if not value:
        return []
    return [item.strip().lower() for item in value.split(",") if item.strip()]


def _normalize_datetime(value: object) -> Optional[datetime]:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        parsed = datetime.fromisoformat(value)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    return None


def _tokenize(parts: Sequence[str]) -> set[str]:
    tokens: set[str] = set()
    for part in parts:
        for token in part.lower().replace(",", " ").split():
            cleaned = token.strip(" .!?;:-()[]{}\"'")
            if len(cleaned) >= 3:
                tokens.add(cleaned)
    return tokens


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


@dataclass
class RetrievalScoreComponents:
    semantic_similarity: float
    relationship_weight: float
    personalization_weight: float
    graph_weight: float
    recency_weight: float
    feedback_weight: float


@dataclass
class AdvancedRetrievalResult:
    id: str
    entity_type: str
    record_id: int
    text: str
    retrieval_score: float
    components: RetrievalScoreComponents
    reasons: list[str]
    metadata: dict


def _relationship_strength_multiplier(label: str) -> float:
    return {
        "weak": 0.25,
        "developing": 0.45,
        "healthy": 0.65,
        "strong": 0.85,
        "strategic": 1.0,
    }.get(label, 0.25)


def _infer_relationship_summary(contact: Optional[Contact], interactions: list[Interaction], follow_ups: list[FollowUp]) -> tuple[float, str, str]:
    if contact is None:
        return 10.0, "developing", "medium"

    recent_interactions = [item for item in interactions if item.contact_id == contact.id]
    last_interaction = max((item.created_at for item in recent_interactions), default=None)
    recency_days = 365 if last_interaction is None else max(0, (_utcnow() - _normalize_datetime(last_interaction)).days)
    overdue = any(
        item.contact_id == contact.id
        and item.status.lower() != "done"
        and item.due_date is not None
        and (_utcnow() - _normalize_datetime(item.due_date)).days > 0
        for item in follow_ups
    )
    strength_value = float(contact.relationship_strength or 0)
    interaction_count = len(recent_interactions)
    score = _clamp(strength_value * 12.0 + min(interaction_count, 4) * 7.0 + max(0.0, 18.0 - min(recency_days, 90) / 5.0), 0.0, 100.0)
    if score < 20:
        strength = "weak"
    elif score < 40:
        strength = "developing"
    elif score < 60:
        strength = "healthy"
    elif score < 75:
        strength = "strong"
    else:
        strength = "strategic"
    risk = "high" if overdue or recency_days >= 60 or score < 35 else ("low" if score >= 60 and recency_days <= 21 else "medium")
    return score, strength, risk


def advanced_retrieve_relationship_intelligence(
    db: Session,
    user_id: int,
    query_text: str,
    *,
    interests: Sequence[str] | None = None,
    themes: Sequence[str] | None = None,
    preferred_opportunity_type: Optional[str] = None,
    preferred_recommendation_type: Optional[str] = None,
    top_k: int = 3,
) -> list[AdvancedRetrievalResult]:
    started = perf_counter()
    interests = interests or []
    themes = themes or []
    expanded_top_k = max(top_k * 3, 6)

    try:
        raw_results = semantic_search_memories(db=db, query_text=query_text, user_id=user_id, top_k=expanded_top_k)
        if not raw_results:
            return []
        reranked = rerank_memory_results(
            results=raw_results,
            user_id=user_id,
            query_text=query_text,
            interests=interests,
            themes=themes,
            top_k=expanded_top_k,
        )
        rerank_by_id = {item.result.id: item for item in reranked}
    except Exception:
        try:
            raw_results = semantic_search_memories(db=db, query_text=query_text, user_id=user_id, top_k=top_k)
        except Exception:
            try:
                get_metrics_service().record_retrieval((perf_counter() - started) * 1000.0, failed=True)
            except Exception:
                pass
            return []
        rerank_by_id = {}

    snapshot = get_user_data_snapshot(db, user_id)
    contacts = snapshot.contacts
    events = snapshot.events
    interactions = snapshot.interactions
    follow_ups = snapshot.follow_ups
    feedback_entries = snapshot.recommendation_feedback
    graph = get_network_graph_insights(db, user_id)
    personalization = get_personalization_profile(db, user_id, snapshot=snapshot)

    contacts_by_id = {contact.id: contact for contact in contacts}
    events_by_id = {event.id: event for event in events}
    centrality_by_contact = {item.contact_id: item.centrality_score for item in graph.centrality_scores}
    bridge_ids = {item.contact_id for item in graph.bridge_contacts}
    cluster_map = {
        contact_id: cluster.cluster_id
        for cluster in graph.clusters
        for contact_id in cluster.contact_ids
    }
    positive_feedback = sum(
        1 for entry in feedback_entries if (entry.category or entry.action) in {"accepted", "helpful", "like"}
    )
    negative_feedback = sum(
        1
        for entry in feedback_entries
        if (entry.category or entry.action) in {"dismissed", "not_helpful", "irrelevant", "too_generic", "dislike"}
    )
    query_tokens = _tokenize([query_text, *interests, *themes])

    ranked: list[AdvancedRetrievalResult] = []
    for raw in raw_results:
        if raw.metadata.get("user_id") != user_id:
            continue
        entity_type = str(raw.metadata.get("entity_type") or "memory")
        record_id = int(raw.metadata.get("record_id") or 0)
        contact: Optional[Contact] = None
        event: Optional[Event] = None
        follow_up: Optional[FollowUp] = None
        if entity_type == "contact":
            contact = contacts_by_id.get(record_id)
        elif entity_type == "event":
            event = events_by_id.get(record_id)
        elif entity_type == "interaction":
            contact = contacts_by_id.get(raw.metadata.get("contact_id"))
            event = events_by_id.get(raw.metadata.get("event_id"))
        elif entity_type == "follow_up":
            follow_up = next((item for item in follow_ups if item.id == record_id), None)
            contact = contacts_by_id.get(raw.metadata.get("contact_id"))
            event = events_by_id.get(raw.metadata.get("event_id"))

        reranked_item = rerank_by_id.get(raw.id)
        rerank_score = reranked_item.rerank_score if reranked_item else raw.score
        reasons = list(reranked_item.reasons) if reranked_item else [f"vector={raw.score:.2f}"]

        semantic_similarity = _clamp(raw.score * 24.0 + rerank_score * 18.0, 0.0, 42.0)

        relationship_score, relationship_strength, relationship_risk = _infer_relationship_summary(
            contact,
            interactions,
            follow_ups,
        )
        relationship_weight = _clamp(
            relationship_score * 0.12
            + _relationship_strength_multiplier(relationship_strength) * 4.0
            - (3.0 if relationship_risk == "high" else 0.0),
            0.0,
            18.0,
        )

        graph_base = 0.0
        if contact is not None:
            graph_base += min(centrality_by_contact.get(contact.id, 0.0) / 4.0, 7.0)
            if contact.id in bridge_ids:
                graph_base += 3.0
                reasons.append("bridge_contact_signal")
            cluster_id = cluster_map.get(contact.id)
            if cluster_id:
                graph_base += 2.0
                if any(token in raw.text.lower() for token in query_tokens):
                    reasons.append(f"cluster_match={cluster_id}")
        graph_weight = _clamp(graph_base, 0.0, 12.0)

        personalization_weight = 0.0
        preferred_categories = set(personalization.preferred_contact_categories)
        if contact is not None:
            if (contact.role or "").lower() in preferred_categories:
                personalization_weight += 4.0
                reasons.append(f"preferred_role={contact.role.lower()}")
            if any(tag in preferred_categories for tag in _split_csv(contact.tags)):
                personalization_weight += 2.5
                reasons.append("preferred_tag_match")
        if preferred_opportunity_type and preferred_opportunity_type in personalization.preferred_opportunity_types:
            personalization_weight += 2.5
            reasons.append(f"preferred_opportunity={preferred_opportunity_type}")
        if preferred_recommendation_type and preferred_recommendation_type in personalization.preferred_recommendation_categories:
            personalization_weight += 2.5
            reasons.append(f"preferred_recommendation={preferred_recommendation_type}")
        personalization_weight = _clamp(personalization_weight + personalization.confidence_score * 1.5, 0.0, 12.0)

        recency_weight = 0.0
        timestamp = _normalize_datetime(raw.metadata.get("updated_at")) or _normalize_datetime(raw.metadata.get("created_at"))
        if timestamp is not None:
            age_days = max(0.0, (_utcnow() - timestamp).total_seconds() / 86400)
            recency_weight += max(0.0, 5.0 - min(age_days, 45.0) / 9.0)
        if event is not None and event.event_date is not None:
            days_until = (_normalize_datetime(event.event_date) - _utcnow()).days
            if 0 <= days_until <= 14:
                recency_weight += max(0.0, 4.0 - days_until / 4.0)
                reasons.append("upcoming_event_relevance")
        if follow_up is not None and follow_up.due_date is not None and follow_up.status.lower() != "done":
            overdue_days = (_utcnow() - _normalize_datetime(follow_up.due_date)).days
            if overdue_days > 0:
                recency_weight += min(4.0, 1.0 + overdue_days / 5.0)
                reasons.append("overdue_follow_up_relevance")
        recency_weight = _clamp(recency_weight, 0.0, 10.0)

        positive_sentiment = sum(
            1
            for item in interactions
            if contact is not None and item.contact_id == contact.id and (item.sentiment or "").lower() in {"positive", "great", "good"}
        )
        negative_sentiment = sum(
            1
            for item in interactions
            if contact is not None and item.contact_id == contact.id and (item.sentiment or "").lower() in {"negative", "bad"}
        )
        feedback_weight = _clamp(
            positive_feedback * 0.5
            - negative_feedback * 0.35
            + positive_sentiment * 1.2
            - negative_sentiment * 1.2,
            0.0,
            8.0,
        )

        retrieval_score = round(
            _clamp(
                semantic_similarity
                + relationship_weight
                + personalization_weight
                + graph_weight
                + recency_weight
                + feedback_weight,
                0.0,
                100.0,
            ),
            1,
        )
        ranked.append(
            AdvancedRetrievalResult(
                id=raw.id,
                entity_type=entity_type,
                record_id=record_id,
                text=raw.text,
                retrieval_score=retrieval_score,
                components=RetrievalScoreComponents(
                    semantic_similarity=round(semantic_similarity, 1),
                    relationship_weight=round(relationship_weight, 1),
                    personalization_weight=round(personalization_weight, 1),
                    graph_weight=round(graph_weight, 1),
                    recency_weight=round(recency_weight, 1),
                    feedback_weight=round(feedback_weight, 1),
                ),
                reasons=reasons[:6],
                metadata=raw.metadata,
            )
        )

    ranked.sort(key=lambda item: (-item.retrieval_score, item.entity_type, item.id))
    try:
        get_metrics_service().record_retrieval((perf_counter() - started) * 1000.0, failed=False)
    except Exception:
        pass
    return ranked[:top_k]
