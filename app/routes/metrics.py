from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.db_models import User
from app.dependencies import get_current_user
from app.models import MetricsResponse, MetricsSummaryResponse
from app.services.metrics_service import get_metrics_payload, get_metrics_summary_payload

router = APIRouter(tags=["metrics"])


@router.get("/metrics", response_model=MetricsResponse)
def metrics(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MetricsResponse:
    return MetricsResponse(**get_metrics_payload(db, user_id=current_user.id))


@router.get("/metrics/summary", response_model=MetricsSummaryResponse)
def metrics_summary(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MetricsSummaryResponse:
    return MetricsSummaryResponse(**get_metrics_summary_payload(db, user_id=current_user.id))
