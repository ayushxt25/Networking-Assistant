from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy.orm import Session

from app.services.advanced_retrieval_service import advanced_retrieve_relationship_intelligence
from app.db_models import Contact, Event, FollowUp, Interaction
from app.services.analytics_service import get_analytics_summary
from app.services.metrics_service import get_metrics_service
from app.services.network_graph_service import get_network_graph_insights
from app.services.personalization_service import get_opportunity_personalization_adjustment
from app.services.recommendation_service import generate_recommendations
from app.services.relationship_scoring_service import get_relationship_scores


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _days_since(value: Optional[datetime], now: datetime) -> int:
    if value is None:
        return 365
    dt = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return max(0, (now - dt).days)


def _days_until(value: Optional[datetime], now: datetime) -> Optional[int]:
    if value is None:
        return None
    dt = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return (dt - now).days


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _opportunity_id(
    user_id: int,
    opportunity_type: str,
    related_contact_id: Optional[int],
    related_event_id: Optional[int],
    related_follow_up_id: Optional[int],
) -> str:
    raw = (
        f"user:{user_id}|type:{opportunity_type}|contact:{related_contact_id}|"
        f"event:{related_event_id}|follow_up:{related_follow_up_id}"
    )
    return str(uuid5(NAMESPACE_URL, raw))


@dataclass
class OpportunityItem:
    opportunity_id: str
    opportunity_type: str
    title: str
    description: str
    priority_score: float
    urgency: str
    confidence: float
    reason: str
    related_contact_id: Optional[int]
    related_event_id: Optional[int]
    related_follow_up_id: Optional[int]
    recommended_action: str
    supporting_signals: list[str]
    created_at: datetime


def detect_opportunities(db: Session, user_id: int) -> list[OpportunityItem]:
    now = _utcnow()
    contacts = db.query(Contact).filter(Contact.user_id == user_id).all()
    events = db.query(Event).filter(Event.user_id == user_id).all()
    interactions = db.query(Interaction).filter(Interaction.user_id == user_id).all()
    follow_ups = db.query(FollowUp).filter(FollowUp.user_id == user_id).all()

    if not contacts and not events and not follow_ups:
        return []

    analytics = get_analytics_summary(db, user_id)
    graph = get_network_graph_insights(db, user_id)
    relationship_scores = get_relationship_scores(db, user_id)
    recommendations = generate_recommendations(db, user_id)

    score_by_contact = {item.contact_id: item for item in relationship_scores.scores}
    contacts_by_id = {contact.id: contact for contact in contacts}
    events_by_id = {event.id: event for event in events}
    bridge_ids = {item.contact_id for item in graph.bridge_contacts}
    weak_ids = {item.contact_id for item in graph.weak_tie_candidates}
    strategic_ids = {
        item.contact_id
        for item in relationship_scores.scores
        if item.relationship_strength in {"strong", "strategic"}
    }
    recommendation_priority_by_key: dict[tuple[str, Optional[int], Optional[int], Optional[int]], float] = {}
    for recommendation in recommendations:
        recommendation_priority_by_key[
            (
                recommendation.recommendation_type,
                recommendation.related_contact_id,
                recommendation.related_event_id,
                recommendation.related_follow_up_id,
            )
        ] = recommendation.priority_score

    interactions_by_contact: dict[int, list[Interaction]] = {contact.id: [] for contact in contacts}
    for interaction in interactions:
        if interaction.contact_id in interactions_by_contact:
            interactions_by_contact[interaction.contact_id].append(interaction)

    seen: set[tuple[str, Optional[int], Optional[int], Optional[int]]] = set()
    opportunities: list[OpportunityItem] = []

    def add_opportunity(
        opportunity_type: str,
        title: str,
        description: str,
        base_priority: float,
        urgency: str,
        confidence: float,
        reason: str,
        recommended_action: str,
        supporting_signals: list[str],
        *,
        related_contact_id: Optional[int] = None,
        related_event_id: Optional[int] = None,
        related_follow_up_id: Optional[int] = None,
    ) -> None:
        dedupe_key = (opportunity_type, related_contact_id, related_event_id, related_follow_up_id)
        if dedupe_key in seen:
            return
        seen.add(dedupe_key)
        personalization = get_opportunity_personalization_adjustment(
            db,
            user_id,
            opportunity_type,
            contact=contacts_by_id.get(related_contact_id) if related_contact_id is not None else None,
            event=events_by_id.get(related_event_id) if related_event_id is not None else None,
            text=f"{title} {description}",
        )
        adjusted_priority = round(
            _clamp(base_priority + personalization.personalization_boost, 0, 100),
            1,
        )
        combined_reason = reason
        if personalization.reason:
            combined_reason = (
                f"{reason} Personalization adjusted score by "
                f"{personalization.personalization_boost:+.1f}: {'; '.join(personalization.reason)}."
            )
            supporting_signals = supporting_signals + [
                f"personalization_boost:{personalization.personalization_boost:+.1f}"
            ]
        opportunities.append(
            OpportunityItem(
                opportunity_id=_opportunity_id(
                    user_id,
                    opportunity_type,
                    related_contact_id,
                    related_event_id,
                    related_follow_up_id,
                ),
                opportunity_type=opportunity_type,
                title=title,
                description=description,
                priority_score=adjusted_priority,
                urgency=urgency,
                confidence=round(_clamp(confidence, 0.0, 1.0), 2),
                reason=combined_reason,
                related_contact_id=related_contact_id,
                related_event_id=related_event_id,
                related_follow_up_id=related_follow_up_id,
                recommended_action=recommended_action,
                supporting_signals=supporting_signals,
                created_at=now,
            )
        )

    for follow_up in follow_ups:
        due_in_days = _days_until(follow_up.due_date, now)
        related_score = score_by_contact.get(follow_up.contact_id) if follow_up.contact_id is not None else None
        score_boost = related_score.score / 6 if related_score else 0
        if follow_up.status.lower() != "done" and due_in_days is not None and due_in_days < 0:
            add_opportunity(
                "follow_up_overdue",
                f"Resolve overdue follow-up: {follow_up.title}",
                follow_up.description or "A follow-up has slipped past its due date.",
                82 + min(abs(due_in_days), 10) + score_boost,
                "high",
                0.95,
                f"Follow-up is overdue by {abs(due_in_days)} day(s).",
                "Send the follow-up or close the task today.",
                [f"overdue_by_days:{abs(due_in_days)}", f"contact_score:{related_score.score if related_score else 0}"],
                related_contact_id=follow_up.contact_id,
                related_event_id=follow_up.event_id,
                related_follow_up_id=follow_up.id,
            )
        elif follow_up.status.lower() != "done":
            add_opportunity(
                "complete_pending_follow_up",
                f"Complete pending follow-up: {follow_up.title}",
                follow_up.description or "A pending follow-up could keep this relationship moving.",
                58 + score_boost + (8 if due_in_days is not None and due_in_days <= 7 else 0),
                "medium" if due_in_days is None or due_in_days > 2 else "high",
                0.8,
                "Pending follow-up is still open.",
                "Review the next step and complete the follow-up.",
                [f"pending_status:{follow_up.status}", f"due_in_days:{due_in_days if due_in_days is not None else 'none'}"],
                related_contact_id=follow_up.contact_id,
                related_event_id=follow_up.event_id,
                related_follow_up_id=follow_up.id,
            )

    for event in events:
        days_until = _days_until(event.event_date, now)
        if days_until is not None and 0 <= days_until <= 7:
            memory_hits = advanced_retrieve_relationship_intelligence(
                db,
                user_id,
                event.title,
                preferred_opportunity_type="prepare_for_upcoming_event",
                top_k=2,
            )
            add_opportunity(
                "prepare_for_upcoming_event",
                f"Prepare for upcoming event: {event.title}",
                event.description or "An upcoming event is close enough to prepare intentional outreach.",
                72 - days_until + len(memory_hits) * 2,
                "high" if days_until <= 2 else "medium",
                0.88,
                f"Event is in {days_until} day(s).",
                "Set outreach goals and identify people to meet before the event.",
                [f"days_until_event:{days_until}", f"advanced_memory_hits:{len(memory_hits)}"],
                related_event_id=event.id,
            )

    for contact in contacts:
        score_item = score_by_contact.get(contact.id)
        if score_item is None:
            continue
        contact_interactions = sorted(
            interactions_by_contact[contact.id],
            key=lambda item: item.created_at,
            reverse=True,
        )
        recency_days = _days_since(contact_interactions[0].created_at if contact_interactions else None, now)
        recommendation_priority = max(
            (
                priority
                for (rtype, contact_id, _event_id, _follow_up_id), priority in recommendation_priority_by_key.items()
                if contact_id == contact.id
            ),
            default=0,
        )
        memory_hits = advanced_retrieve_relationship_intelligence(
            db,
            user_id,
            contact.name,
            preferred_opportunity_type="activate_bridge_contact" if contact.id in bridge_ids else None,
            top_k=2,
        )

        if recency_days >= 30:
            add_opportunity(
                "reconnect_with_cold_contact",
                f"Reconnect with {contact.name}",
                f"{contact.name} has gone cold and may benefit from a fresh touchpoint.",
                52 + min(recency_days, 90) / 2 + recommendation_priority / 5,
                "medium" if recency_days < 60 else "high",
                0.84,
                f"No recent interaction for {recency_days} day(s).",
                "Send a concise check-in that references previous context.",
                [f"recency_days:{recency_days}", f"relationship_risk:{score_item.relationship_risk}"],
                related_contact_id=contact.id,
            )

        if contact.id in strategic_ids:
            add_opportunity(
                "strengthen_strategic_contact",
                f"Strengthen strategic relationship with {contact.name}",
                f"{contact.name} is a high-value relationship worth proactive momentum.",
                68 + score_item.score / 4 + recommendation_priority / 8,
                "medium",
                0.86,
                f"Relationship score is {score_item.score} with {score_item.relationship_strength} strength.",
                "Plan a thoughtful follow-up or high-value introduction.",
                [f"relationship_score:{score_item.score}", f"strength:{score_item.relationship_strength}"],
                related_contact_id=contact.id,
            )

        if contact.id in bridge_ids:
            add_opportunity(
                "activate_bridge_contact",
                f"Activate bridge contact: {contact.name}",
                f"{contact.name} connects different parts of your network and can unlock cross-network value.",
                64 + score_item.score / 5 + len(memory_hits),
                "medium",
                0.82,
                "This contact bridges multiple companies, tags, roles, or events.",
                "Reach out with a context-rich update or cross-network introduction idea.",
                [f"bridge_contact:true", f"advanced_memory_hits:{len(memory_hits)}"],
                related_contact_id=contact.id,
            )

        if contact.id in weak_ids:
            add_opportunity(
                "revive_weak_tie",
                f"Revive weak tie: {contact.name}",
                f"{contact.name} is lightly connected but may offer new surface area if re-engaged.",
                46 + max(0, recency_days - 20) / 3 + recommendation_priority / 10,
                "medium",
                0.76,
                "Weak-tie graph signal plus limited recent interaction suggests a revival opportunity.",
                "Send a low-friction message that reopens the relationship.",
                [f"weak_tie:true", f"recency_days:{recency_days}"],
                related_contact_id=contact.id,
            )

        if score_item.relationship_strength in {"strong", "strategic"}:
            add_opportunity(
                "nurture_high_score_relationship",
                f"Nurture high-score relationship with {contact.name}",
                f"{contact.name} is already strong and worth maintaining with deliberate consistency.",
                60 + score_item.score / 4,
                "low" if score_item.relationship_risk == "low" else "medium",
                0.79,
                f"Relationship score is {score_item.score} with low decay risk if maintained.",
                "Keep momentum with a useful update, intro, or appreciation note.",
                [f"high_score:{score_item.score}", f"risk:{score_item.relationship_risk}"],
                related_contact_id=contact.id,
            )

    for contact in contacts:
        score_item = score_by_contact.get(contact.id)
        if score_item and score_item.relationship_strength in {"strong", "strategic"} and score_item.relationship_risk == "high":
            add_opportunity(
                "nurture_high_score_relationship",
                f"Protect at-risk strong relationship: {contact.name}",
                f"{contact.name} is important but showing risk signals that justify action now.",
                74 + score_item.score / 6,
                "high",
                0.83,
                f"High-value relationship currently has {score_item.relationship_risk} risk.",
                "Re-engage before the relationship cools further.",
                [f"relationship_score:{score_item.score}", f"risk:{score_item.relationship_risk}"],
                related_contact_id=contact.id,
            )

    opportunities.sort(
        key=lambda item: (-item.priority_score, item.opportunity_type, item.title.lower(), item.opportunity_id)
    )
    try:
        get_metrics_service().record_opportunity_generation(len(opportunities))
    except Exception:
        pass
    return opportunities
