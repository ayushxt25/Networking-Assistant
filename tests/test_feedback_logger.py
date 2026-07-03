"""
Tests for app.services.feedback_logger (database-backed).
"""

import pytest

from app.db_models import User
from app.services.feedback_logger import load_feedback, log_feedback, summarize_feedback


def _create_test_user(db_session) -> User:
    user = User(username="testuser", hashed_password="not-a-real-hash")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_load_feedback_returns_empty_list_for_new_user(db_session):
    user = _create_test_user(db_session)
    assert load_feedback(db_session, user_id=user.id) == []


def test_log_feedback_persists_entry(db_session):
    user = _create_test_user(db_session)

    log_feedback(db_session, user_id=user.id, suggestion="Ask about their AI work", action="like")

    feedback = load_feedback(db_session, user_id=user.id)
    assert len(feedback) == 1
    assert feedback[0].suggestion == "Ask about their AI work"
    assert feedback[0].action == "like"
    assert feedback[0].created_at is not None


def test_log_feedback_rejects_invalid_action(db_session):
    user = _create_test_user(db_session)

    with pytest.raises(ValueError):
        log_feedback(db_session, user_id=user.id, suggestion="Some suggestion", action="maybe")


def test_load_feedback_respects_limit(db_session):
    user = _create_test_user(db_session)

    for i in range(15):
        log_feedback(db_session, user_id=user.id, suggestion=f"Suggestion {i}", action="like")

    feedback = load_feedback(db_session, user_id=user.id, limit=10)
    assert len(feedback) == 10


def test_log_feedback_supports_structured_category_and_target(db_session):
    user = _create_test_user(db_session)

    entry = log_feedback(
        db_session,
        user_id=user.id,
        suggestion="Mention their latest launch",
        category="helpful",
        target_type="recommendation",
        target_id="rec-1",
        notes="Useful and specific",
    )

    assert entry.action == "like"
    assert entry.category == "helpful"
    assert entry.target_type == "recommendation"
    assert entry.target_id == "rec-1"
    assert entry.notes == "Useful and specific"


def test_log_feedback_supports_opportunity_target_type(db_session):
    user = _create_test_user(db_session)

    entry = log_feedback(
        db_session,
        user_id=user.id,
        suggestion="Prioritize this intro",
        category="helpful",
        target_type="opportunity",
        target_id="opp-1",
        notes="Strong timing",
    )

    assert entry.action == "like"
    assert entry.category == "helpful"
    assert entry.target_type == "opportunity"
    assert entry.target_id == "opp-1"


def test_log_feedback_supports_fact_check_target_type(db_session):
    user = _create_test_user(db_session)

    entry = log_feedback(
        db_session,
        user_id=user.id,
        suggestion="AI infrastructure market",
        category="helpful",
        target_type="fact_check",
        target_id="fact-check:ai-infrastructure-market",
        notes="Useful verification summary",
    )

    assert entry.action == "like"
    assert entry.category == "helpful"
    assert entry.target_type == "fact_check"
    assert entry.target_id == "fact-check:ai-infrastructure-market"


def test_log_feedback_supports_app_experience_target_type(db_session):
    user = _create_test_user(db_session)

    entry = log_feedback(
        db_session,
        user_id=user.id,
        suggestion="App feedback: feature request",
        category="helpful",
        target_type="app_experience",
        target_id="global",
        notes="Would like better shortcut support",
    )

    assert entry.action == "like"
    assert entry.category == "helpful"
    assert entry.target_type == "app_experience"
    assert entry.target_id == "global"


def test_log_feedback_rejects_invalid_target_type(db_session):
    user = _create_test_user(db_session)

    with pytest.raises(ValueError):
        log_feedback(
            db_session,
            user_id=user.id,
            suggestion="Unsupported target",
            category="helpful",
            target_type="unsupported_target",
        )


def test_summarize_feedback_returns_generation_and_recommendation_signals(db_session):
    user = _create_test_user(db_session)
    log_feedback(
        db_session,
        user_id=user.id,
        suggestion="Ask about their product roadmap",
        category="too_generic",
        target_type="generation_suggestion",
    )
    log_feedback(
        db_session,
        user_id=user.id,
        suggestion="Reconnect with Mina",
        category="accepted",
        target_type="recommendation",
    )

    summary = summarize_feedback(db_session, user_id=user.id)
    assert summary.generation_quality.total == 1
    assert summary.generation_quality.category_counts["too_generic"] == 1
    assert summary.recommendation_quality.total == 1
    assert summary.recommendation_quality.category_counts["accepted"] == 1
    assert summary.user_preferences.specificity_adjustment_signals == 1
