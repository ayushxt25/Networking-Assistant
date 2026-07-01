from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from app.db_models import Contact, Event, FollowUp, Interaction


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _split_csv(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _normalize_datetime(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _is_done(status: str) -> bool:
    return status.strip().lower() == "done"


@dataclass
class AnalyticsSummary:
    total_contacts: int
    total_events: int
    total_interactions: int
    total_follow_ups: int
    overdue_follow_ups_count: int
    completed_follow_ups_count: int
    upcoming_follow_ups_count: int
    cold_contacts_count: int
    average_relationship_strength: float
    interaction_frequency: float
    top_relationship_tags: List[str]
    network_health_score: float
    created_at: datetime


def get_analytics_summary(db: Session, user_id: int) -> AnalyticsSummary:
    now = _utcnow()
    contacts = db.query(Contact).filter(Contact.user_id == user_id).all()
    events = db.query(Event).filter(Event.user_id == user_id).all()
    interactions = db.query(Interaction).filter(Interaction.user_id == user_id).all()
    follow_ups = db.query(FollowUp).filter(FollowUp.user_id == user_id).all()

    interactions_by_contact: dict[int, List[Interaction]] = {}
    for interaction in interactions:
        if interaction.contact_id is not None:
            interactions_by_contact.setdefault(interaction.contact_id, []).append(interaction)

    overdue_follow_ups_count = 0
    completed_follow_ups_count = 0
    upcoming_follow_ups_count = 0
    for follow_up in follow_ups:
        due_date = _normalize_datetime(follow_up.due_date)
        if _is_done(follow_up.status):
            completed_follow_ups_count += 1
            continue
        if due_date is not None and due_date < now:
            overdue_follow_ups_count += 1
        else:
            upcoming_follow_ups_count += 1

    cold_contacts_count = 0
    strengths = [contact.relationship_strength for contact in contacts if contact.relationship_strength is not None]
    tag_counter: Counter[str] = Counter()
    interaction_counts: List[int] = []
    recent_contact_count = 0

    for contact in contacts:
        contact_interactions = sorted(
            interactions_by_contact.get(contact.id, []),
            key=lambda item: item.created_at,
            reverse=True,
        )
        interaction_counts.append(len(contact_interactions))
        if not contact_interactions:
            cold_contacts_count += 1
        else:
            last_interaction = _normalize_datetime(contact_interactions[0].created_at)
            if last_interaction is None or (now - last_interaction).days >= 30:
                cold_contacts_count += 1
            else:
                recent_contact_count += 1

        for tag in _split_csv(contact.tags):
            tag_counter[tag.lower()] += 1

    average_relationship_strength = round(sum(strengths) / len(strengths), 2) if strengths else 0.0
    interaction_frequency = round(sum(interaction_counts) / len(contacts), 2) if contacts else 0.0
    top_relationship_tags = [
        tag for tag, _count in sorted(tag_counter.items(), key=lambda item: (-item[1], item[0]))[:5]
    ]

    total_contacts = len(contacts)
    total_events = len(events)
    total_interactions = len(interactions)
    total_follow_ups = len(follow_ups)
    recent_contact_ratio = (recent_contact_count / total_contacts) if total_contacts else 0.0
    follow_up_completion_ratio = (
        completed_follow_ups_count / total_follow_ups if total_follow_ups else 0.0
    )
    overdue_penalty_ratio = (
        overdue_follow_ups_count / total_follow_ups if total_follow_ups else 0.0
    )
    health_score = (
        (average_relationship_strength / 5.0) * 45
        + min(interaction_frequency, 5.0) / 5.0 * 25
        + recent_contact_ratio * 20
        + follow_up_completion_ratio * 15
        - overdue_penalty_ratio * 20
    )
    network_health_score = round(max(0.0, min(100.0, health_score)), 2)

    return AnalyticsSummary(
        total_contacts=total_contacts,
        total_events=total_events,
        total_interactions=total_interactions,
        total_follow_ups=total_follow_ups,
        overdue_follow_ups_count=overdue_follow_ups_count,
        completed_follow_ups_count=completed_follow_ups_count,
        upcoming_follow_ups_count=upcoming_follow_ups_count,
        cold_contacts_count=cold_contacts_count,
        average_relationship_strength=average_relationship_strength,
        interaction_frequency=interaction_frequency,
        top_relationship_tags=top_relationship_tags,
        network_health_score=network_health_score,
        created_at=now,
    )
