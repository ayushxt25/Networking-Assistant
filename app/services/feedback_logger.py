from collections import Counter
from dataclasses import dataclass
from typing import List, Optional

from sqlalchemy.orm import Session

from app.db_models import Feedback

VALID_ACTIONS = {"like", "dislike"}
VALID_CATEGORIES = {
    "helpful",
    "not_helpful",
    "irrelevant",
    "too_generic",
    "wrong_tone",
    "accepted",
    "dismissed",
}
VALID_TARGET_TYPES = {
    "generation_suggestion",
    "recommendation",
    "opportunity",
    "fact_check",
    "app_experience",
    "contact",
    "interaction",
}
NEGATIVE_CATEGORIES = {"not_helpful", "irrelevant", "too_generic", "wrong_tone", "dismissed"}


@dataclass
class FeedbackBucket:
    total: int
    category_counts: dict[str, int]


@dataclass
class FeedbackPreferenceSignals:
    preferred_feedback_categories: List[str]
    tone_adjustment_signals: int
    specificity_adjustment_signals: int


@dataclass
class FeedbackSummary:
    generation_quality: FeedbackBucket
    recommendation_quality: FeedbackBucket
    user_preferences: FeedbackPreferenceSignals


def _normalize_action(action: Optional[str], category: Optional[str]) -> str:
    if action is not None:
        if action not in VALID_ACTIONS:
            raise ValueError(f"action must be one of {VALID_ACTIONS}, got '{action}'")
        return action

    if category is None:
        raise ValueError("either action or category is required")

    if category not in VALID_CATEGORIES:
        raise ValueError(f"category must be one of {VALID_CATEGORIES}, got '{category}'")

    return "dislike" if category in NEGATIVE_CATEGORIES else "like"


def _validate_category(category: Optional[str]) -> Optional[str]:
    if category is None:
        return None
    if category not in VALID_CATEGORIES:
        raise ValueError(f"category must be one of {VALID_CATEGORIES}, got '{category}'")
    return category


def _validate_target_type(target_type: Optional[str]) -> Optional[str]:
    if target_type is None:
        return None
    if target_type not in VALID_TARGET_TYPES:
        raise ValueError(f"target_type must be one of {VALID_TARGET_TYPES}, got '{target_type}'")
    return target_type


def log_feedback(
    db: Session,
    user_id: int,
    suggestion: str,
    action: Optional[str] = None,
    category: Optional[str] = None,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    notes: Optional[str] = None,
) -> Feedback:
    normalized_category = _validate_category(category)
    normalized_target_type = _validate_target_type(target_type)
    normalized_action = _normalize_action(action, normalized_category)

    entry = Feedback(
        user_id=user_id,
        suggestion=suggestion,
        action=normalized_action,
        category=normalized_category,
        target_type=normalized_target_type,
        target_id=target_id,
        notes=notes,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def load_feedback(db: Session, user_id: int, limit: int = 10) -> List[Feedback]:
    return (
        db.query(Feedback)
        .filter(Feedback.user_id == user_id)
        .order_by(Feedback.created_at.desc())
        .limit(limit)
        .all()
    )


def summarize_feedback(db: Session, user_id: int) -> FeedbackSummary:
    entries = db.query(Feedback).filter(Feedback.user_id == user_id).all()

    generation_entries = [entry for entry in entries if entry.target_type == "generation_suggestion"]
    recommendation_entries = [entry for entry in entries if entry.target_type == "recommendation"]

    generation_counts = Counter(entry.category or entry.action for entry in generation_entries)
    recommendation_counts = Counter(entry.category or entry.action for entry in recommendation_entries)
    all_counts = Counter(entry.category or entry.action for entry in entries)

    preferred_feedback_categories = [
        name for name, _count in sorted(all_counts.items(), key=lambda item: (-item[1], item[0]))[:3]
    ]

    return FeedbackSummary(
        generation_quality=FeedbackBucket(
            total=len(generation_entries),
            category_counts=dict(sorted(generation_counts.items())),
        ),
        recommendation_quality=FeedbackBucket(
            total=len(recommendation_entries),
            category_counts=dict(sorted(recommendation_counts.items())),
        ),
        user_preferences=FeedbackPreferenceSignals(
            preferred_feedback_categories=preferred_feedback_categories,
            tone_adjustment_signals=sum(1 for entry in entries if entry.category == "wrong_tone"),
            specificity_adjustment_signals=sum(1 for entry in entries if entry.category == "too_generic"),
        ),
    )
