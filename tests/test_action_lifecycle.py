from app.db_models import ActionLifecycleState, User
from app.services.action_lifecycle_service import get_lifecycle_state, upsert_lifecycle_state
from app.services.feedback_logger import log_feedback
from app.services.recommendation_service import build_recommendation_id


def test_lifecycle_row_creation_for_recommendation(db_session):
    user = User(username="lifecycle_rec", hashed_password="hashed")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    recommendation_id = build_recommendation_id(
        user.id,
        "strengthen_high_value_contact",
        11,
        None,
        None,
    )
    state = upsert_lifecycle_state(
        db_session,
        user.id,
        "recommendation",
        recommendation_id,
        entity_type="strengthen_high_value_contact",
        status="accepted",
    )

    assert state.entity_kind == "recommendation"
    assert state.entity_id == recommendation_id
    assert state.status == "accepted"
    assert state.accepted_at is not None


def test_lifecycle_row_creation_for_opportunity(db_session):
    user = User(username="lifecycle_opp", hashed_password="hashed")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    state = upsert_lifecycle_state(
        db_session,
        user.id,
        "opportunity",
        "opp-123",
        entity_type="prepare_for_upcoming_event",
        status="dismissed",
    )

    assert state.entity_kind == "opportunity"
    assert state.entity_id == "opp-123"
    assert state.status == "dismissed"
    assert state.dismissed_at is not None


def test_repeated_accept_dismiss_updates_are_idempotent(db_session):
    user = User(username="lifecycle_idempotent", hashed_password="hashed")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    state = upsert_lifecycle_state(
        db_session,
        user.id,
        "recommendation",
        "rec-1",
        entity_type="follow_up_with_contact",
        status="accepted",
    )
    accepted_at = state.accepted_at

    state = upsert_lifecycle_state(
        db_session,
        user.id,
        "recommendation",
        "rec-1",
        entity_type="follow_up_with_contact",
        status="accepted",
    )
    assert state.accepted_at == accepted_at

    state = upsert_lifecycle_state(
        db_session,
        user.id,
        "recommendation",
        "rec-1",
        entity_type="follow_up_with_contact",
        status="dismissed",
    )
    dismissed_at = state.dismissed_at

    state = upsert_lifecycle_state(
        db_session,
        user.id,
        "recommendation",
        "rec-1",
        entity_type="follow_up_with_contact",
        status="dismissed",
    )
    assert state.dismissed_at == dismissed_at

    rows = (
        db_session.query(ActionLifecycleState)
        .filter(ActionLifecycleState.user_id == user.id, ActionLifecycleState.entity_id == "rec-1")
        .all()
    )
    assert len(rows) == 1


def test_lifecycle_state_is_user_isolated(db_session):
    user_a = User(username="lifecycle_a", hashed_password="hashed")
    user_b = User(username="lifecycle_b", hashed_password="hashed")
    db_session.add_all([user_a, user_b])
    db_session.commit()
    db_session.refresh(user_a)
    db_session.refresh(user_b)

    upsert_lifecycle_state(
        db_session,
        user_a.id,
        "recommendation",
        "shared-id",
        entity_type="strengthen_high_value_contact",
        status="accepted",
    )

    assert get_lifecycle_state(db_session, user_b.id, "recommendation", "shared-id") is None


def test_feedback_based_tuning_remains_independent_of_lifecycle_state(db_session):
    user = User(username="lifecycle_feedback", hashed_password="hashed")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    recommendation_id = build_recommendation_id(
        user.id,
        "strengthen_high_value_contact",
        7,
        None,
        None,
    )
    upsert_lifecycle_state(
        db_session,
        user.id,
        "recommendation",
        recommendation_id,
        entity_type="strengthen_high_value_contact",
        status="accepted",
    )
    log_feedback(
        db_session,
        user_id=user.id,
        suggestion="Helpful signal",
        category="helpful",
        target_type="recommendation",
        target_id=recommendation_id,
    )

    state = get_lifecycle_state(db_session, user.id, "recommendation", recommendation_id)
    feedback = db_session.query(ActionLifecycleState).filter(ActionLifecycleState.id == state.id).one()

    assert feedback.status == "accepted"
