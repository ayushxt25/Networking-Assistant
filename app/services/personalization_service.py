from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.db_models import Contact, Event, Feedback, FollowUp, Interaction, RecommendationImpression, UserProfile

FEEDBACK_WEIGHTS = {
    "accepted": 4.0,
    "helpful": 3.0,
    "like": 1.5,
    "dismissed": -4.0,
    "not_helpful": -3.0,
    "irrelevant": -3.0,
    "too_generic": -2.0,
    "wrong_tone": 0.0,
    "dislike": -1.5,
}
OPPORTUNITY_TYPE_BY_RECOMMENDATION_TYPE = {
    "complete_overdue_follow_up": ["follow_up_overdue", "complete_pending_follow_up"],
    "prepare_for_upcoming_event": ["prepare_for_upcoming_event"],
    "reconnect_with_cold_relationship": ["reconnect_with_cold_contact", "revive_weak_tie"],
    "strengthen_high_value_contact": [
        "strengthen_strategic_contact",
        "nurture_high_score_relationship",
        "activate_bridge_contact",
    ],
    "follow_up_with_contact": ["complete_pending_follow_up", "nurture_high_score_relationship"],
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _split_csv(value: Optional[str]) -> list[str]:
    if not value:
        return []
    return [item.strip().lower() for item in value.split(",") if item.strip()]


def _add_weight(bucket: dict[str, float], key: Optional[str], delta: float) -> None:
    if not key:
        return
    normalized = key.strip().lower()
    if not normalized:
        return
    bucket[normalized] = round(bucket.get(normalized, 0.0) + delta, 3)


def _sorted_positive_keys(bucket: dict[str, float], limit: int = 3) -> list[str]:
    return [
        key
        for key, value in sorted(bucket.items(), key=lambda item: (-item[1], item[0]))
        if value > 0
    ][:limit]


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


@dataclass
class PersonalizationProfile:
    preference_vector: dict[str, float]
    preferred_opportunity_types: list[str]
    preferred_contact_categories: list[str]
    preferred_interaction_styles: list[str]
    preferred_recommendation_categories: list[str]
    top_preferences: list[str]
    confidence_score: float
    profile_completeness: float
    learning_status: str
    created_at: datetime


@dataclass
class PersonalizationAdjustment:
    personalization_boost: float
    reason: list[str]


@dataclass
class _SignalState:
    recommendation_type_weights: dict[str, float]
    opportunity_type_weights: dict[str, float]
    contact_category_weights: dict[str, float]
    interaction_style_weights: dict[str, float]
    goal_terms: set[str]
    follow_up_completion_ratio: float
    confidence_score: float


def _build_signal_state(db: Session, user_id: int) -> _SignalState:
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    contacts = db.query(Contact).filter(Contact.user_id == user_id).all()
    interactions = db.query(Interaction).filter(Interaction.user_id == user_id).all()
    follow_ups = db.query(FollowUp).filter(FollowUp.user_id == user_id).all()
    feedback_entries = (
        db.query(Feedback)
        .filter(Feedback.user_id == user_id, Feedback.target_type == "recommendation")
        .order_by(Feedback.created_at.desc())
        .all()
    )
    impressions = (
        db.query(RecommendationImpression)
        .filter(RecommendationImpression.user_id == user_id)
        .order_by(RecommendationImpression.created_at.desc())
        .all()
    )

    contacts_by_id = {contact.id: contact for contact in contacts}
    impression_by_id = {item.recommendation_id: item for item in impressions}
    impression_by_type: dict[str, RecommendationImpression] = {}
    for impression in impressions:
        impression_by_type.setdefault(impression.recommendation_type, impression)

    recommendation_type_weights: dict[str, float] = {}
    opportunity_type_weights: dict[str, float] = {}
    contact_category_weights: dict[str, float] = {}
    interaction_style_weights: dict[str, float] = {}

    goal_terms = set()
    if profile:
        goal_terms.update(_split_csv(profile.goals))
        goal_terms.update(_split_csv(profile.interests))

    for interaction in interactions:
        _add_weight(interaction_style_weights, interaction.interaction_type, 0.8)
        if interaction.contact_id in contacts_by_id:
            contact = contacts_by_id[interaction.contact_id]
            _add_weight(contact_category_weights, contact.role, 0.35)
            _add_weight(contact_category_weights, contact.company, 0.25)
            for tag in _split_csv(contact.tags):
                _add_weight(contact_category_weights, tag, 0.5)

    completed_follow_ups = 0
    for follow_up in follow_ups:
        if follow_up.status.lower() == "done":
            completed_follow_ups += 1
            _add_weight(opportunity_type_weights, "complete_pending_follow_up", 0.8)
            _add_weight(recommendation_type_weights, "follow_up_with_contact", 0.6)
    follow_up_completion_ratio = completed_follow_ups / len(follow_ups) if follow_ups else 0.0

    for feedback in feedback_entries:
        signal = feedback.category or feedback.action
        delta = FEEDBACK_WEIGHTS.get(signal, 0.0)
        if delta == 0:
            continue
        matched_impression = impression_by_id.get(feedback.target_id or "")
        if matched_impression is None and feedback.target_id:
            matched_impression = impression_by_type.get(feedback.target_id)
        recommendation_type = matched_impression.recommendation_type if matched_impression else feedback.target_id
        _add_weight(recommendation_type_weights, recommendation_type, delta)
        for opportunity_type in OPPORTUNITY_TYPE_BY_RECOMMENDATION_TYPE.get(recommendation_type or "", []):
            _add_weight(opportunity_type_weights, opportunity_type, delta * 0.75)

        if matched_impression and matched_impression.related_contact_id in contacts_by_id:
            contact = contacts_by_id[matched_impression.related_contact_id]
            _add_weight(contact_category_weights, contact.role, delta * 0.7)
            _add_weight(contact_category_weights, contact.company, delta * 0.45)
            for tag in _split_csv(contact.tags):
                _add_weight(contact_category_weights, tag, delta * 0.8)

    evidence_count = len(feedback_entries) + len(interactions) + completed_follow_ups + len(goal_terms)
    confidence_score = round(_clamp(evidence_count / 12.0, 0.0, 1.0), 2)
    return _SignalState(
        recommendation_type_weights=recommendation_type_weights,
        opportunity_type_weights=opportunity_type_weights,
        contact_category_weights=contact_category_weights,
        interaction_style_weights=interaction_style_weights,
        goal_terms=goal_terms,
        follow_up_completion_ratio=follow_up_completion_ratio,
        confidence_score=confidence_score,
    )


def get_personalization_profile(db: Session, user_id: int) -> PersonalizationProfile:
    now = _utcnow()
    state = _build_signal_state(db, user_id)
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()

    completeness_fields = [
        bool(profile and profile.full_name),
        bool(profile and profile.headline),
        bool(profile and profile.goals),
        bool(profile and profile.interests),
        bool(profile and profile.preferred_tone),
    ]
    profile_completeness = round(sum(completeness_fields) / len(completeness_fields), 2)

    preference_vector: dict[str, float] = {}
    for key, value in state.recommendation_type_weights.items():
        preference_vector[f"recommendation:{key}"] = round(value, 2)
    for key, value in state.opportunity_type_weights.items():
        preference_vector[f"opportunity:{key}"] = round(value, 2)
    for key, value in state.contact_category_weights.items():
        preference_vector[f"contact:{key}"] = round(value, 2)
    for key, value in state.interaction_style_weights.items():
        preference_vector[f"interaction:{key}"] = round(value, 2)

    sorted_vector_items = sorted(preference_vector.items(), key=lambda item: (-item[1], item[0]))
    top_preferences = [key for key, value in sorted_vector_items if value > 0][:5]

    if state.confidence_score == 0:
        learning_status = "cold_start"
    elif state.confidence_score < 0.65:
        learning_status = "learning"
    else:
        learning_status = "established"

    return PersonalizationProfile(
        preference_vector=dict(sorted_vector_items[:12]),
        preferred_opportunity_types=_sorted_positive_keys(state.opportunity_type_weights),
        preferred_contact_categories=_sorted_positive_keys(state.contact_category_weights),
        preferred_interaction_styles=_sorted_positive_keys(state.interaction_style_weights),
        preferred_recommendation_categories=_sorted_positive_keys(state.recommendation_type_weights),
        top_preferences=top_preferences,
        confidence_score=state.confidence_score,
        profile_completeness=profile_completeness,
        learning_status=learning_status,
        created_at=now,
    )


def _contact_match_boost(state: _SignalState, contact: Optional[Contact]) -> tuple[float, list[str]]:
    if contact is None:
        return 0.0, []
    reasons: list[str] = []
    boost = 0.0
    role_score = state.contact_category_weights.get((contact.role or "").lower(), 0.0)
    if role_score > 0:
        boost += min(role_score * 0.12, 1.2)
        reasons.append(f"User prefers {contact.role.lower()} contacts")
    elif role_score < 0:
        boost += max(role_score * 0.1, -1.0)

    for tag in _split_csv(contact.tags):
        tag_score = state.contact_category_weights.get(tag, 0.0)
        if tag_score > 0:
            boost += min(tag_score * 0.1, 0.8)
            reasons.append(f"User responds well to {tag} contacts")
            break
        if tag_score < 0:
            boost += max(tag_score * 0.08, -0.6)

    return boost, reasons[:2]


def _goal_alignment_boost(state: _SignalState, text: str) -> tuple[float, list[str]]:
    normalized = (text or "").lower()
    matched_terms = sorted(term for term in state.goal_terms if term and term in normalized)
    if not matched_terms:
        return 0.0, []
    return min(len(matched_terms) * 0.8, 2.0), [f"Matches user goal or interest: {matched_terms[0]}"]


def get_recommendation_personalization_adjustment(
    db: Session,
    user_id: int,
    recommendation_type: str,
    *,
    contact: Optional[Contact] = None,
    event: Optional[Event] = None,
    text: str = "",
) -> PersonalizationAdjustment:
    state = _build_signal_state(db, user_id)
    reasons: list[str] = []
    boost = 0.0

    type_score = state.recommendation_type_weights.get(recommendation_type.lower(), 0.0)
    if type_score > 0:
        boost += min(type_score * 0.15, 2.0)
        reasons.append(f"User frequently accepts {recommendation_type.replace('_', ' ')} recommendations")
    elif type_score < 0:
        boost += max(type_score * 0.12, -2.0)
        reasons.append(f"User often dismisses {recommendation_type.replace('_', ' ')} recommendations")

    contact_boost, contact_reasons = _contact_match_boost(state, contact)
    boost += contact_boost
    reasons.extend(contact_reasons)

    goal_boost, goal_reasons = _goal_alignment_boost(
        state,
        " ".join(
            part
            for part in [
                text,
                event.title if event else "",
                event.description if event else "",
                contact.notes if contact else "",
            ]
            if part
        ),
    )
    boost += goal_boost
    reasons.extend(goal_reasons)

    if "follow_up" in recommendation_type.lower():
        follow_up_delta = (state.follow_up_completion_ratio - 0.5) * 1.5
        if follow_up_delta > 0:
            reasons.append("User historically completes follow-up tasks")
        boost += follow_up_delta

    return PersonalizationAdjustment(
        personalization_boost=round(_clamp(boost, -8.0, 8.0), 1),
        reason=reasons[:3],
    )


def get_opportunity_personalization_adjustment(
    db: Session,
    user_id: int,
    opportunity_type: str,
    *,
    contact: Optional[Contact] = None,
    event: Optional[Event] = None,
    text: str = "",
) -> PersonalizationAdjustment:
    state = _build_signal_state(db, user_id)
    reasons: list[str] = []
    boost = 0.0

    type_score = state.opportunity_type_weights.get(opportunity_type.lower(), 0.0)
    if type_score > 0:
        boost += min(type_score * 0.16, 2.2)
        reasons.append(f"User responds to {opportunity_type.replace('_', ' ')} actions")
    elif type_score < 0:
        boost += max(type_score * 0.12, -2.0)
        reasons.append(f"User deprioritizes {opportunity_type.replace('_', ' ')} actions")

    contact_boost, contact_reasons = _contact_match_boost(state, contact)
    boost += contact_boost
    reasons.extend(contact_reasons)

    goal_boost, goal_reasons = _goal_alignment_boost(
        state,
        " ".join(
            part
            for part in [
                text,
                event.title if event else "",
                event.description if event else "",
                contact.notes if contact else "",
            ]
            if part
        ),
    )
    boost += goal_boost
    reasons.extend(goal_reasons)

    if opportunity_type in {"follow_up_overdue", "complete_pending_follow_up"}:
        boost += (state.follow_up_completion_ratio - 0.5) * 1.2

    return PersonalizationAdjustment(
        personalization_boost=round(_clamp(boost, -8.0, 8.0), 1),
        reason=reasons[:3],
    )


def get_relationship_personalization_boost(
    db: Session,
    user_id: int,
    contact: Contact,
) -> PersonalizationAdjustment:
    state = _build_signal_state(db, user_id)
    boost, reasons = _contact_match_boost(state, contact)
    goal_boost, goal_reasons = _goal_alignment_boost(state, f"{contact.notes or ''} {' '.join(_split_csv(contact.tags))}")
    boost += goal_boost
    reasons.extend(goal_reasons)
    return PersonalizationAdjustment(
        personalization_boost=round(_clamp(boost, -4.0, 4.0), 1),
        reason=reasons[:3],
    )
