from typing import List

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.db_models import User
from app.dependencies import get_current_user
from app.models import OpportunityResponse
from app.services.action_lifecycle_service import merge_lifecycle_state
from app.services.opportunity_detection_service import detect_opportunities

router = APIRouter(tags=["opportunities"])


@router.get("/opportunities", response_model=List[OpportunityResponse])
def list_opportunities(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[OpportunityResponse]:
    items = detect_opportunities(db, current_user.id)
    merged = merge_lifecycle_state(
        db,
        current_user.id,
        "opportunity",
        items,
        entity_id_field="opportunity_id",
        entity_type_field="opportunity_type",
    )
    return [OpportunityResponse(**item) for item in merged]
