from typing import List

from sqlalchemy.orm import Session

from app.db_models import RecommendationImpression
from app.services.recommendation_service import RecommendationItem


def log_recommendation_impressions(
    db: Session,
    user_id: int,
    recommendations: List[RecommendationItem],
    *,
    commit: bool = True,
) -> None:
    if not recommendations:
        return

    db.add_all(
        [
            RecommendationImpression(
                user_id=user_id,
                recommendation_id=recommendation.recommendation_id,
                recommendation_type=recommendation.recommendation_type,
                title=recommendation.title,
                priority_score=recommendation.priority_score,
                related_contact_id=recommendation.related_contact_id,
                related_event_id=recommendation.related_event_id,
                related_follow_up_id=recommendation.related_follow_up_id,
                reason=recommendation.reason,
            )
            for recommendation in recommendations
        ]
    )
    if commit:
        db.commit()
    else:
        db.flush()
