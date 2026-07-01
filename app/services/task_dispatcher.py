from typing import Any

from app.config import get_celery_enabled
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


def dispatch_optional_task(task_name: str, *args: Any, **kwargs: Any) -> bool:
    if not get_celery_enabled():
        return False

    task = TASK_REGISTRY.get(task_name)
    if task is None:
        return False

    try:
        task.delay(*args, **kwargs)
        return True
    except Exception:
        return False


def dispatch_user_refreshes(user_id: int) -> dict[str, bool]:
    results: dict[str, bool] = {}
    for task_name in dict.fromkeys(REFRESH_TASK_NAMES):
        results[task_name] = dispatch_optional_task(task_name, user_id)
    return results
