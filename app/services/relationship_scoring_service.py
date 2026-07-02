from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.db_models import Contact, Feedback, FollowUp, Interaction, UserProfile
from app.services.network_graph_service import get_network_graph_insights
from app.services.personalization_service import get_relationship_personalization_boost
from app.services.recommendation_service import generate_recommendations


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _split_csv(value: Optional[str]) -> list[str]:
    if not value:
        return []
    return [item.strip().lower() for item in value.split(",") if item.strip()]


def _days_since(value: Optional[datetime], now: datetime) -> int:
    if value is None:
        return 365
    dt = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return max(0, (now - dt).days)


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


@dataclass
class RelationshipScoreFactors:
    interaction_score: float
    recency_score: float
    graph_score: float
    recommendation_score: float
    interest_overlap_score: float


@dataclass
class RelationshipScoreItem:
    contact_id: int
    name: str
    score: float
    relationship_strength: str
    relationship_risk: str
    factors: RelationshipScoreFactors


@dataclass
class RelationshipScoreList:
    scores: list[RelationshipScoreItem]
    created_at: datetime


def _strength_label(score: float) -> str:
    if score < 20:
        return "weak"
    if score < 40:
        return "developing"
    if score < 60:
        return "healthy"
    if score < 75:
        return "strong"
    return "strategic"


def _risk_label(score: float, recency_days: int, has_overdue_follow_up: bool) -> str:
    if score >= 60 and recency_days <= 21 and not has_overdue_follow_up:
        return "low"
    if score < 35 or recency_days >= 60 or has_overdue_follow_up:
        return "high"
    return "medium"


def get_relationship_scores(
    db: Session,
    user_id: int,
    contact_id: Optional[int] = None,
) -> RelationshipScoreList:
    now = _utcnow()
    contacts_query = db.query(Contact).filter(Contact.user_id == user_id)
    if contact_id is not None:
        contacts_query = contacts_query.filter(Contact.id == contact_id)
    contacts = contacts_query.all()

    if not contacts:
        return RelationshipScoreList(scores=[], created_at=now)

    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    profile_terms = set(_split_csv(profile.interests) + _split_csv(profile.goals)) if profile else set()
    interactions = db.query(Interaction).filter(Interaction.user_id == user_id).all()
    follow_ups = db.query(FollowUp).filter(FollowUp.user_id == user_id).all()
    feedback_entries = (
        db.query(Feedback)
        .filter(Feedback.user_id == user_id, Feedback.target_type == "recommendation")
        .all()
    )
    recommendations = generate_recommendations(db, user_id)
    graph = get_network_graph_insights(db, user_id)

    graph_scores = {item.contact_id: item.centrality_score for item in graph.centrality_scores}
    bridge_ids = {item.contact_id for item in graph.bridge_contacts}
    strong_ids = {item.contact_id for item in graph.strong_tie_contacts}
    weak_ids = {item.contact_id for item in graph.weak_tie_candidates}
    clustered_ids = {contact for cluster in graph.clusters for contact in cluster.contact_ids}

    interactions_by_contact: dict[int, list[Interaction]] = {contact.id: [] for contact in contacts}
    for interaction in interactions:
        if interaction.contact_id in interactions_by_contact:
            interactions_by_contact[interaction.contact_id].append(interaction)

    follow_ups_by_contact: dict[int, list[FollowUp]] = {contact.id: [] for contact in contacts}
    for follow_up in follow_ups:
        if follow_up.contact_id in follow_ups_by_contact:
            follow_ups_by_contact[follow_up.contact_id].append(follow_up)

    recommendation_feedback_by_contact: dict[int, list[Feedback]] = {contact.id: [] for contact in contacts}
    recommendation_types_by_contact: dict[int, set[str]] = {contact.id: set() for contact in contacts}
    for recommendation in recommendations:
        if recommendation.related_contact_id in recommendation_types_by_contact:
            recommendation_types_by_contact[recommendation.related_contact_id].add(recommendation.recommendation_type)
    for feedback in feedback_entries:
        for candidate_contact_id, recommendation_types in recommendation_types_by_contact.items():
            if feedback.target_id in recommendation_types:
                recommendation_feedback_by_contact[candidate_contact_id].append(feedback)

    results: list[RelationshipScoreItem] = []
    for contact in contacts:
        contact_interactions = sorted(
            interactions_by_contact[contact.id],
            key=lambda item: item.created_at,
            reverse=True,
        )
        contact_follow_ups = follow_ups_by_contact[contact.id]
        contact_feedback = recommendation_feedback_by_contact[contact.id]
        interaction_count = len(contact_interactions)
        recency_days = _days_since(contact_interactions[0].created_at if contact_interactions else None, now)
        relationship_days = _days_since(contact.created_at, now)
        completed_follow_ups = sum(1 for item in contact_follow_ups if item.status.lower() == "done")
        follow_up_ratio = completed_follow_ups / len(contact_follow_ups) if contact_follow_ups else 0.0
        interaction_frequency = interaction_count / max(1.0, relationship_days / 30.0)

        interaction_score = _clamp(
            min(interaction_count, 5) * 5 + min(interaction_frequency, 4) * 2.5 + follow_up_ratio * 5,
            0,
            25,
        )
        recency_score = _clamp(20 - min(recency_days, 120) / 6, 0, 20)

        shared_terms = set(_split_csv(contact.tags))
        note_blob = (contact.notes or "").lower()
        profile_matches = sum(1 for term in profile_terms if term in shared_terms or term in note_blob)
        event_goal_matches = sum(
            1
            for interaction in contact_interactions
            if interaction.event is not None
            for goal in _split_csv(interaction.event.goals)
            if goal in profile_terms
        )
        duration_bonus = min(relationship_days / 120, 4)
        interest_overlap_score = _clamp(profile_matches * 3 + event_goal_matches * 2 + duration_bonus, 0, 15)

        centrality_component = min(graph_scores.get(contact.id, 0.0) / 2.5, 12)
        bridge_component = 4 if contact.id in bridge_ids else 0
        cluster_component = 2 if contact.id in clustered_ids else 0
        tie_component = 2 if contact.id in strong_ids else (-2 if contact.id in weak_ids else 0)
        graph_score = _clamp(centrality_component + bridge_component + cluster_component + tie_component, 0, 20)

        accepted_count = sum(1 for entry in contact_feedback if entry.category == "accepted")
        positive_count = sum(
            1 for entry in contact_feedback if (entry.category or entry.action) in {"accepted", "helpful", "like"}
        )
        negative_count = sum(
            1
            for entry in contact_feedback
            if (entry.category or entry.action) in {"dismissed", "not_helpful", "irrelevant", "dislike"}
        )
        recommendation_score = _clamp(accepted_count * 4 + positive_count * 2 - negative_count * 2, 0, 20)

        raw_score = (
            interaction_score
            + recency_score
            + graph_score
            + recommendation_score
            + interest_overlap_score
            + (contact.relationship_strength or 0) * 2.5
        )
        score = round(_clamp(raw_score, 0, 100), 1)
        has_overdue_follow_up = any(
            item.status.lower() != "done" and item.due_date is not None and _days_since(item.due_date, now) > 0
            for item in contact_follow_ups
        )

        results.append(
            RelationshipScoreItem(
                contact_id=contact.id,
                name=contact.name,
                score=score,
                relationship_strength=_strength_label(score),
                relationship_risk=_risk_label(score, recency_days, has_overdue_follow_up),
                factors=RelationshipScoreFactors(
                    interaction_score=round(interaction_score, 1),
                    recency_score=round(recency_score, 1),
                    graph_score=round(graph_score, 1),
                    recommendation_score=round(recommendation_score, 1),
                    interest_overlap_score=round(interest_overlap_score, 1),
                ),
            )
        )

    personalization_boosts = {
        contact.id: get_relationship_personalization_boost(db, user_id, contact).personalization_boost
        for contact in contacts
    }
    results.sort(
        key=lambda item: (
            -(item.score + personalization_boosts.get(item.contact_id, 0.0)),
            -item.score,
            item.name.lower(),
            item.contact_id,
        )
    )
    return RelationshipScoreList(scores=results, created_at=now)
