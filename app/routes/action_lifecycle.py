from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.db_models import User
from app.dependencies import get_current_user
from app.models import ActionLifecycleMutationRequest, ActionLifecycleStateResponse
from app.services.action_lifecycle_service import upsert_lifecycle_state

router = APIRouter(tags=["action-lifecycle"])


@router.post("/action-lifecycle", response_model=ActionLifecycleStateResponse)
def mutate_action_lifecycle(
    request: Request,
    body: ActionLifecycleMutationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ActionLifecycleStateResponse:
    try:
        state = upsert_lifecycle_state(
            db,
            current_user.id,
            body.entity_kind,
            body.entity_id,
            entity_type=body.entity_type or body.entity_kind,
            status=body.status,
            converted_follow_up_id=body.converted_follow_up_id,
            notes=body.notes,
            mark_seen=body.status == "new",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return ActionLifecycleStateResponse.model_validate(state)
