from typing import List, Optional

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.db_models import User
from app.dependencies import get_current_user
from app.models import AdvancedRetrievalResultResponse
from app.services.advanced_retrieval_service import advanced_retrieve_relationship_intelligence

router = APIRouter(tags=["retrieval"])


def _split_csv(value: Optional[str]) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


@router.get("/retrieval/debug", response_model=List[AdvancedRetrievalResultResponse])
def retrieval_debug(
    request: Request,
    q: str,
    top_k: int = 5,
    interests: Optional[str] = None,
    themes: Optional[str] = None,
    opportunity_type: Optional[str] = None,
    recommendation_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[AdvancedRetrievalResultResponse]:
    results = advanced_retrieve_relationship_intelligence(
        db=db,
        user_id=current_user.id,
        query_text=q,
        interests=_split_csv(interests),
        themes=_split_csv(themes),
        preferred_opportunity_type=opportunity_type,
        preferred_recommendation_type=recommendation_type,
        top_k=max(1, min(top_k, 10)),
    )
    return [
        AdvancedRetrievalResultResponse(
            id=item.id,
            entity_type=item.entity_type,
            record_id=item.record_id,
            text=item.text,
            retrieval_score=item.retrieval_score,
            components=item.components.__dict__,
            reasons=item.reasons,
            metadata=item.metadata,
        )
        for item in results
    ]
