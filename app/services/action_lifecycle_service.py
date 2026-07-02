from datetime import datetime, timezone
from typing import Iterable, Optional

from sqlalchemy.orm import Session

from app.db_models import ActionLifecycleState

VALID_ENTITY_KINDS = {"recommendation", "opportunity"}
VALID_STATUSES = {"new", "accepted", "dismissed", "completed", "converted_to_follow_up"}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def get_lifecycle_state(
    db: Session,
    user_id: int,
    entity_kind: str,
    entity_id: str,
) -> Optional[ActionLifecycleState]:
    return (
        db.query(ActionLifecycleState)
        .filter(
            ActionLifecycleState.user_id == user_id,
            ActionLifecycleState.entity_kind == entity_kind,
            ActionLifecycleState.entity_id == entity_id,
        )
        .first()
    )


def _apply_status_timestamps(
    state: ActionLifecycleState,
    status: str,
    now: datetime,
) -> None:
    if status == "accepted" and state.accepted_at is None:
        state.accepted_at = now
    elif status == "dismissed" and state.dismissed_at is None:
        state.dismissed_at = now
    elif status in {"completed", "converted_to_follow_up"} and state.completed_at is None:
        state.completed_at = now


def upsert_lifecycle_state(
    db: Session,
    user_id: int,
    entity_kind: str,
    entity_id: str,
    *,
    entity_type: Optional[str] = None,
    status: str = "new",
    converted_follow_up_id: Optional[int] = None,
    notes: Optional[str] = None,
    mark_seen: bool = False,
) -> ActionLifecycleState:
    if entity_kind not in VALID_ENTITY_KINDS:
        raise ValueError(f"entity_kind must be one of {VALID_ENTITY_KINDS}")
    if status not in VALID_STATUSES:
        raise ValueError(f"status must be one of {VALID_STATUSES}")
    if status == "converted_to_follow_up" and converted_follow_up_id is None:
        raise ValueError("converted_follow_up_id is required for converted_to_follow_up status")
    if entity_type is None:
        raise ValueError("entity_type is required")

    now = _utcnow()
    state = get_lifecycle_state(db, user_id, entity_kind, entity_id)
    if state is None:
        state = ActionLifecycleState(
            user_id=user_id,
            entity_kind=entity_kind,
            entity_id=entity_id,
            entity_type=entity_type,
            status=status,
            converted_follow_up_id=converted_follow_up_id,
            notes=notes,
            first_seen_at=now if mark_seen or status == "new" else None,
            last_seen_at=now if mark_seen or status == "new" else None,
        )
        _apply_status_timestamps(state, status, now)
        db.add(state)
    else:
        if entity_type:
            state.entity_type = entity_type
        state.status = status
        if converted_follow_up_id is not None:
            state.converted_follow_up_id = converted_follow_up_id
        if notes is not None:
            state.notes = notes
        if mark_seen:
            if state.first_seen_at is None:
                state.first_seen_at = now
            state.last_seen_at = now
        _apply_status_timestamps(state, status, now)

    db.commit()
    db.refresh(state)
    return state


def merge_lifecycle_state(
    db: Session,
    user_id: int,
    entity_kind: str,
    items: Iterable,
    *,
    entity_id_field: str,
    entity_type_field: str,
    mark_seen: bool = True,
) -> list[dict]:
    serialized_items: list[dict] = []
    raw_items = list(items)
    if not raw_items:
        return serialized_items

    entity_ids = [getattr(item, entity_id_field) for item in raw_items]
    existing_states = (
        db.query(ActionLifecycleState)
        .filter(
            ActionLifecycleState.user_id == user_id,
            ActionLifecycleState.entity_kind == entity_kind,
            ActionLifecycleState.entity_id.in_(entity_ids),
        )
        .all()
    )
    state_by_entity_id = {state.entity_id: state for state in existing_states}

    if mark_seen:
        now = _utcnow()
        pending = False
        for item in raw_items:
            entity_id = getattr(item, entity_id_field)
            entity_type = getattr(item, entity_type_field)
            state = state_by_entity_id.get(entity_id)
            if state is None:
                state = ActionLifecycleState(
                    user_id=user_id,
                    entity_kind=entity_kind,
                    entity_id=entity_id,
                    entity_type=entity_type,
                    status="new",
                    first_seen_at=now,
                    last_seen_at=now,
                )
                db.add(state)
                state_by_entity_id[entity_id] = state
                pending = True
            else:
                if state.first_seen_at is None:
                    state.first_seen_at = now
                state.last_seen_at = now
                if not state.entity_type:
                    state.entity_type = entity_type
                pending = True
        if pending:
            db.commit()
            for state in state_by_entity_id.values():
                if state.id is None:
                    db.refresh(state)

    for item in raw_items:
        entity_id = getattr(item, entity_id_field)
        state = state_by_entity_id.get(entity_id)
        serialized_items.append(
            {
                **item.__dict__,
                "lifecycle_status": state.status if state else "new",
                "converted_follow_up_id": state.converted_follow_up_id if state else None,
                "lifecycle_updated_at": state.updated_at if state else None,
            }
        )

    return serialized_items
