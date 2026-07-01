from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api_utils import pagination_limit, pagination_offset
from app.database import get_db
from app.db_models import AuditLog
from app.db_models import User
from app.dependencies import get_current_user
from app.models import AuditLogResponse
from app.services.audit_logger import load_audit_logs

router = APIRouter(tags=["audit"])


@router.get("/audit/logs", response_model=List[AuditLogResponse])
def list_audit_logs(
    request: Request,
    limit: int = pagination_limit(default=50),
    offset: int = pagination_offset(),
    event_type: Optional[str] = None,
    status_filter: Optional[str] = None,
    entity_type: Optional[str] = None,
    sort_order: Literal["asc", "desc"] = "desc",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[AuditLogResponse]:
    query = db.query(AuditLog).filter(AuditLog.user_id == current_user.id)
    if event_type:
        query = query.filter(AuditLog.event_type == event_type)
    if status_filter:
        query = query.filter(AuditLog.status == status_filter)
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    query = query.order_by(
        AuditLog.created_at.desc() if sort_order == "desc" else AuditLog.created_at.asc(),
        AuditLog.id.desc(),
    )
    entries = query.offset(offset).limit(limit).all()
    return [AuditLogResponse(**entry.__dict__) for entry in entries]
