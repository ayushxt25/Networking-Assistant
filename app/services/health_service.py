from pathlib import Path

from sqlalchemy import text

from app.config import get_celery_broker_url, get_celery_enabled, get_ml_ranker_enabled, get_ml_ranker_model_dir
from app.database import SessionLocal
from app.services.vector_store import get_vector_store


def _database_health() -> dict:
    session = SessionLocal()
    try:
        session.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}
    finally:
        session.close()


def _vector_store_health() -> dict:
    try:
        store = get_vector_store()
        return {"status": "ok", "backend": store.__class__.__name__}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


def _redis_health() -> dict:
    if not get_celery_enabled():
        return {"status": "disabled"}

    try:
        import redis

        client = redis.Redis.from_url(get_celery_broker_url(), socket_connect_timeout=0.1, socket_timeout=0.1)
        client.ping()
        return {"status": "ok"}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


def _ml_ranker_health() -> dict:
    model_dir: Path = get_ml_ranker_model_dir()
    return {
        "status": "ok" if get_ml_ranker_enabled() else "disabled",
        "enabled": get_ml_ranker_enabled(),
        "model_dir": str(model_dir),
        "model_files": len(list(model_dir.glob("recommendation_ranker_user_*.json"))) if model_dir.exists() else 0,
    }


def get_dependency_health() -> dict:
    dependencies = {
        "database": _database_health(),
        "vector_store": _vector_store_health(),
        "redis": _redis_health(),
        "ml_ranker": _ml_ranker_health(),
    }
    overall = "ok"
    if any(item["status"] == "error" for item in dependencies.values()):
        overall = "degraded"
    return {"status": overall, "dependencies": dependencies}
