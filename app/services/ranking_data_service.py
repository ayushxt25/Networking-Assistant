from dataclasses import dataclass
from typing import List, Optional

from sqlalchemy.orm import Session

from app.db_models import Feedback, RecommendationImpression

LABEL_BY_CATEGORY = {
    "helpful": 1,
    "accepted": 1,
    "dismissed": 0,
    "not_helpful": 0,
    "irrelevant": 0,
    "too_generic": 0,
}


@dataclass
class RankingTrainingRow:
    recommendation_id: str
    recommendation_type: str
    priority_score: float
    has_contact: bool
    has_event: bool
    has_follow_up: bool
    reason: str
    label: Optional[int]
    feedback_category: Optional[str]
    created_at: object


def build_recommendation_training_data(db: Session, user_id: int) -> List[RankingTrainingRow]:
    impressions = (
        db.query(RecommendationImpression)
        .filter(RecommendationImpression.user_id == user_id)
        .order_by(RecommendationImpression.created_at.desc())
        .all()
    )
    feedback_entries = (
        db.query(Feedback)
        .filter(Feedback.user_id == user_id, Feedback.target_type == "recommendation")
        .all()
    )

    feedback_by_target_id = {}
    for entry in feedback_entries:
        if not entry.target_id:
            continue
        feedback_by_target_id.setdefault(entry.target_id, []).append(entry)

    rows: List[RankingTrainingRow] = []
    for impression in impressions:
        matching_feedback = feedback_by_target_id.get(impression.recommendation_id, [])
        if not matching_feedback:
            matching_feedback = feedback_by_target_id.get(impression.recommendation_type, [])
        latest_feedback = sorted(matching_feedback, key=lambda entry: entry.created_at, reverse=True)
        feedback = latest_feedback[0] if latest_feedback else None
        feedback_category = (feedback.category or feedback.action) if feedback else None
        rows.append(
            RankingTrainingRow(
                recommendation_id=impression.recommendation_id,
                recommendation_type=impression.recommendation_type,
                priority_score=impression.priority_score,
                has_contact=impression.related_contact_id is not None,
                has_event=impression.related_event_id is not None,
                has_follow_up=impression.related_follow_up_id is not None,
                reason=impression.reason,
                label=LABEL_BY_CATEGORY.get(feedback_category),
                feedback_category=feedback_category,
                created_at=impression.created_at,
            )
        )

    return rows
