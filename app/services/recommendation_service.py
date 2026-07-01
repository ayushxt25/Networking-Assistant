from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy.orm import Session

from app.db_models import Contact, Event, Feedback, FollowUp, Interaction, UserProfile


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _split_csv(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass
class RecommendationItem:
    id: str
    recommendation_id: str
    recommendation_type: str
    title: str
    description: str
    priority_score: float
    reason: str
    related_contact_id: Optional[int]
    related_event_id: Optional[int]
    related_follow_up_id: Optional[int]
    created_at: datetime


FEEDBACK_SCORE_WEIGHTS = {
    "helpful": 3.0,
    "accepted": 4.0,
    "dismissed": -4.0,
    "not_helpful": -3.0,
    "irrelevant": -3.0,
    "too_generic": -2.0,
    "wrong_tone": 0.0,
    "like": 1.0,
    "dislike": -1.0,
}
MAX_FEEDBACK_ADJUSTMENT = 8.0


def _days_since(dt: Optional[datetime], now: datetime) -> Optional[int]:
    if dt is None:
        return None
    dt_utc = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    return max(0, (now - dt_utc).days)


def _days_until(dt: Optional[datetime], now: datetime) -> Optional[int]:
    if dt is None:
        return None
    dt_utc = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    return (dt_utc - now).days


def _clamp_feedback_adjustment(value: float) -> float:
    return max(-MAX_FEEDBACK_ADJUSTMENT, min(MAX_FEEDBACK_ADJUSTMENT, value))


def build_recommendation_id(
    user_id: int,
    recommendation_type: str,
    related_contact_id: Optional[int],
    related_event_id: Optional[int],
    related_follow_up_id: Optional[int],
) -> str:
    raw_key = (
        f"user:{user_id}|type:{recommendation_type}|contact:{related_contact_id}|"
        f"event:{related_event_id}|follow_up:{related_follow_up_id}"
    )
    return str(uuid5(NAMESPACE_URL, raw_key))


def _feedback_adjustment_for_recommendation(
    feedback_entries: List[Feedback],
    recommendation: RecommendationItem,
) -> tuple[float, Optional[str]]:
    matched_entries = [
        entry
        for entry in feedback_entries
        if entry.target_id in {recommendation.recommendation_id, recommendation.recommendation_type}
    ]
    if not matched_entries:
        return 0.0, None

    raw_delta = 0.0
    helpful_count = 0
    negative_count = 0
    for entry in matched_entries:
        signal = entry.category or entry.action
        weight = FEEDBACK_SCORE_WEIGHTS.get(signal, 0.0)
        raw_delta += weight
        if signal in {"helpful", "accepted"}:
            helpful_count += 1
        if signal in {"dismissed", "not_helpful", "irrelevant", "too_generic"}:
            negative_count += 1

    delta = _clamp_feedback_adjustment(raw_delta)
    if delta == 0:
        return 0.0, None

    if delta > 0:
        return (
            delta,
            f"Prior feedback signaled this recommendation was helpful ({helpful_count} signal(s)).",
        )
    return (
        delta,
        f"Prior feedback reduced this recommendation after {negative_count} negative signal(s).",
    )


def generate_recommendations(db: Session, user_id: int) -> List[RecommendationItem]:
    now = _utcnow()
    recommendations: List[RecommendationItem] = []
    feedback_entries = (
        db.query(Feedback)
        .filter(Feedback.user_id == user_id, Feedback.target_type == "recommendation")
        .all()
    )

    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    goal_terms = set(_split_csv(profile.goals) + _split_csv(profile.interests)) if profile else set()

    contacts = db.query(Contact).filter(Contact.user_id == user_id).all()
    events = db.query(Event).filter(Event.user_id == user_id).all()
    follow_ups = db.query(FollowUp).filter(FollowUp.user_id == user_id).all()
    interactions = db.query(Interaction).filter(Interaction.user_id == user_id).all()

    interactions_by_contact: dict[int, List[Interaction]] = {}
    for interaction in interactions:
        if interaction.contact_id is not None:
            interactions_by_contact.setdefault(interaction.contact_id, []).append(interaction)

    for follow_up in follow_ups:
        due_in_days = _days_until(follow_up.due_date, now)
        if follow_up.status.lower() != "done" and due_in_days is not None and due_in_days < 0:
            recommendation_id = build_recommendation_id(
                user_id,
                "complete_overdue_follow_up",
                follow_up.contact_id,
                follow_up.event_id,
                follow_up.id,
            )
            recommendations.append(
                RecommendationItem(
                    id=recommendation_id,
                    recommendation_id=recommendation_id,
                    recommendation_type="complete_overdue_follow_up",
                    title=f"Complete overdue follow-up: {follow_up.title}",
                    description=follow_up.description or "This follow-up is past due and needs attention.",
                    priority_score=100 + abs(due_in_days),
                    reason=f"Follow-up is overdue by {abs(due_in_days)} day(s).",
                    related_contact_id=follow_up.contact_id,
                    related_event_id=follow_up.event_id,
                    related_follow_up_id=follow_up.id,
                    created_at=now,
                )
            )

    for event in events:
        days_until = _days_until(event.event_date, now)
        if days_until is not None and 0 <= days_until <= 7:
            goal_match = 10 if any(term.lower() in (event.goals or "").lower() for term in goal_terms) else 0
            recommendation_id = build_recommendation_id(
                user_id,
                "prepare_for_upcoming_event",
                None,
                event.id,
                None,
            )
            recommendations.append(
                RecommendationItem(
                    id=recommendation_id,
                    recommendation_id=recommendation_id,
                    recommendation_type="prepare_for_upcoming_event",
                    title=f"Prepare for upcoming event: {event.title}",
                    description=event.description or "Review goals and outreach targets before this event.",
                    priority_score=70 - days_until + goal_match,
                    reason=f"Event is coming up in {days_until} day(s).",
                    related_contact_id=None,
                    related_event_id=event.id,
                    related_follow_up_id=None,
                    created_at=now,
                )
            )

    for contact in contacts:
        contact_interactions = sorted(
            interactions_by_contact.get(contact.id, []),
            key=lambda interaction: interaction.created_at,
            reverse=True,
        )
        last_interaction = contact_interactions[0].created_at if contact_interactions else None
        days_since_last = _days_since(last_interaction, now)
        interaction_frequency = len(contact_interactions)
        strength = contact.relationship_strength or 0
        tag_blob = " ".join(_split_csv(contact.tags))
        note_blob = contact.notes or ""
        profile_match = any(term.lower() in f"{tag_blob} {note_blob}".lower() for term in goal_terms)

        if days_since_last is None or days_since_last >= 30:
            recommendation_id = build_recommendation_id(
                user_id,
                "reconnect_with_cold_relationship",
                contact.id,
                None,
                None,
            )
            recommendations.append(
                RecommendationItem(
                    id=recommendation_id,
                    recommendation_id=recommendation_id,
                    recommendation_type="reconnect_with_cold_relationship",
                    title=f"Reconnect with {contact.name}",
                    description=f"{contact.name} at {contact.company} has gone quiet. Re-open the conversation.",
                    priority_score=40 + min(days_since_last or 45, 90) / 2 + strength * 5,
                    reason="No recent interaction recorded for this relationship.",
                    related_contact_id=contact.id,
                    related_event_id=None,
                    related_follow_up_id=None,
                    created_at=now,
                )
            )

        if strength >= 4 or profile_match:
            recommendation_id = build_recommendation_id(
                user_id,
                "strengthen_high_value_contact",
                contact.id,
                None,
                None,
            )
            recommendations.append(
                RecommendationItem(
                    id=recommendation_id,
                    recommendation_id=recommendation_id,
                    recommendation_type="strengthen_high_value_contact",
                    title=f"Strengthen relationship with {contact.name}",
                    description=f"Prioritize a thoughtful touchpoint with {contact.name}.",
                    priority_score=55 + strength * 6 + interaction_frequency * 2 + (8 if profile_match else 0),
                    reason="High relationship strength or strong alignment with profile goals/interests.",
                    related_contact_id=contact.id,
                    related_event_id=None,
                    related_follow_up_id=None,
                    created_at=now,
                )
            )

        open_follow_up = next(
            (
                follow_up
                for follow_up in follow_ups
                if follow_up.contact_id == contact.id and follow_up.status.lower() != "done"
            ),
            None,
        )
        if open_follow_up is None and interaction_frequency > 0 and strength >= 3:
            recommendation_id = build_recommendation_id(
                user_id,
                "follow_up_with_contact",
                contact.id,
                None,
                None,
            )
            recommendations.append(
                RecommendationItem(
                    id=recommendation_id,
                    recommendation_id=recommendation_id,
                    recommendation_type="follow_up_with_contact",
                    title=f"Follow up with {contact.name}",
                    description=f"Keep momentum going with {contact.name} from {contact.company}.",
                    priority_score=45 + strength * 4 + interaction_frequency,
                    reason="Engaged contact has momentum but no active follow-up tracked.",
                    related_contact_id=contact.id,
                    related_event_id=None,
                    related_follow_up_id=None,
                    created_at=now,
                )
            )

    for recommendation in recommendations:
        delta, feedback_reason = _feedback_adjustment_for_recommendation(feedback_entries, recommendation)
        if feedback_reason is None:
            continue
        recommendation.priority_score += delta
        recommendation.reason = f"{recommendation.reason} {feedback_reason}"

    recommendations.sort(key=lambda item: item.priority_score, reverse=True)
    return recommendations
