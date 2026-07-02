from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.db_models import User
from app.dependencies import get_current_user
from app.models import PersonalizationProfileResponse
from app.services.personalization_service import get_personalization_profile

router = APIRouter(tags=["personalization"])


@router.get("/personalization/profile", response_model=PersonalizationProfileResponse)
def personalization_profile(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PersonalizationProfileResponse:
    profile = get_personalization_profile(db, current_user.id)
    return PersonalizationProfileResponse(**profile.__dict__)
