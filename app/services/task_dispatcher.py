from typing import Any

from sqlalchemy.orm import Session

from app.config import get_celery_enabled
from app.services.audit_logger import log_audit_event
from app.services.cache_service import invalidate_user_cache
from app.services.metrics_service import get_metrics_service
from app.tasks import (
    refresh_user_analytics_task,
    refresh_user_recommendations_task,
    sync_user_semantic_memory_task,
)

REFRESH_TASK_NAMES = (
    "sync_user_semantic_memory",
    "refresh_user_analytics",
    "refresh_user_recommendations",
)

TASK_REGISTRY = {
    "sync_user_semantic_memory": sync_user_semantic_memory_task,
    "refresh_user_analytics": refresh_user_analytics_task,
    "refresh_user_recommendations": refresh_user_recommendations_task,
}


def dispatch_optional_task(
    task_name: str,
    *args: Any,
    user_id: int | None = None,
    db: Session | None = None,
    **kwargs: Any,
) -> bool:
    try:
        get_metrics_service().record_task_dispatch()
    except Exception:
        pass
    log_audit_event(
        event_type="background_task_dispatch",
        status="attempted",
        user_id=user_id,
        entity_type="task",
        entity_id=task_name,
        message="Background task dispatch attempted",
        db=db,
    )
    if not get_celery_enabled():
        try:
            get_metrics_service().record_task_dispatch_failure()
        except Exception:
            pass
        log_audit_event(
            event_type="background_task_dispatch",
            status="failed",
            user_id=user_id,
            entity_type="task",
            entity_id=task_name,
            message="Celery disabled",
            db=db,
        )
        return False

    task = TASK_REGISTRY.get(task_name)
    if task is None:
        try:
            get_metrics_service().record_task_dispatch_failure()
        except Exception:
            pass
        log_audit_event(
            event_type="background_task_dispatch",
            status="failed",
            user_id=user_id,
            entity_type="task",
            entity_id=task_name,
            message="Task not registered",
            db=db,
        )
        return False

    try:
        task.delay(*args, **kwargs)
        log_audit_event(
            event_type="background_task_dispatch",
            status="completed",
            user_id=user_id,
            entity_type="task",
            entity_id=task_name,
            message="Background task dispatch completed",
            db=db,
        )
        return True
    except Exception:
        try:
            get_metrics_service().record_task_dispatch_failure()
        except Exception:
            pass
        log_audit_event(
            event_type="background_task_dispatch",
            status="failed",
            user_id=user_id,
            entity_type="task",
            entity_id=task_name,
            message="Background task dispatch failed",
            db=db,
        )
        return False


def dispatch_user_refreshes(user_id: int, db: Session | None = None) -> dict[str, bool]:
    invalidate_user_cache(user_id)
    results: dict[str, bool] = {}
    for task_name in dict.fromkeys(REFRESH_TASK_NAMES):
        results[task_name] = dispatch_optional_task(task_name, user_id, user_id=user_id, db=db)
    return results
