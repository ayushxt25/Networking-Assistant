from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.db_models import User
from app.dependencies import get_current_user
from app.models import NetworkGraphInsightsResponse
from app.services.network_graph_service import get_network_graph_insights

router = APIRouter(tags=["network"])


@router.get("/network/graph-insights", response_model=NetworkGraphInsightsResponse)
def network_graph_insights(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NetworkGraphInsightsResponse:
    insights = get_network_graph_insights(db, current_user.id)
    return NetworkGraphInsightsResponse(
        total_contacts=insights.total_contacts,
        network_density_estimate=insights.network_density_estimate,
        centrality_scores=[item.__dict__ for item in insights.centrality_scores],
        weak_tie_candidates=[item.__dict__ for item in insights.weak_tie_candidates],
        strong_tie_contacts=[item.__dict__ for item in insights.strong_tie_contacts],
        bridge_contacts=[item.__dict__ for item in insights.bridge_contacts],
        isolated_contacts=[item.__dict__ for item in insights.isolated_contacts],
        clusters=[item.__dict__ for item in insights.clusters],
        created_at=insights.created_at,
    )
