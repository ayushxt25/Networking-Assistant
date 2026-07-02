from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.db_models import Contact, Event, Feedback, FollowUp, Interaction, RecommendationImpression, UserProfile


@dataclass
class UserDataSnapshot:
    profile: UserProfile | None
    contacts: list[Contact]
    events: list[Event]
    interactions: list[Interaction]
    follow_ups: list[FollowUp]
    recommendation_feedback: list[Feedback]
    recommendation_impressions: list[RecommendationImpression]

    @property
    def contacts_by_id(self) -> dict[int, Contact]:
        return {contact.id: contact for contact in self.contacts}

    @property
    def events_by_id(self) -> dict[int, Event]:
        return {event.id: event for event in self.events}


def get_user_data_snapshot(db: Session, user_id: int) -> UserDataSnapshot:
    cache = db.info.setdefault("user_data_snapshots", {})
    snapshot = cache.get(user_id)
    if snapshot is not None:
        return snapshot

    snapshot = UserDataSnapshot(
        profile=db.query(UserProfile).filter(UserProfile.user_id == user_id).first(),
        contacts=db.query(Contact).filter(Contact.user_id == user_id).all(),
        events=db.query(Event).filter(Event.user_id == user_id).all(),
        interactions=db.query(Interaction).filter(Interaction.user_id == user_id).all(),
        follow_ups=db.query(FollowUp).filter(FollowUp.user_id == user_id).all(),
        recommendation_feedback=(
            db.query(Feedback)
            .filter(Feedback.user_id == user_id, Feedback.target_type == "recommendation")
            .order_by(Feedback.created_at.desc())
            .all()
        ),
        recommendation_impressions=(
            db.query(RecommendationImpression)
            .filter(RecommendationImpression.user_id == user_id)
            .order_by(RecommendationImpression.created_at.desc())
            .all()
        ),
    )
    cache[user_id] = snapshot
    return snapshot
