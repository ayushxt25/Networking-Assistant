import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SQLITE_PATH = PROJECT_ROOT / "data" / "app.db"
DEFAULT_RANKER_MODEL_DIR = PROJECT_ROOT / "data" / "models"
DEFAULT_CORS_ALLOWED_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)


def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_SQLITE_PATH}")

    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+psycopg://", 1)

    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)

    return database_url


def get_celery_enabled() -> bool:
    return os.getenv("CELERY_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


def get_celery_broker_url() -> str:
    return os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")


def get_celery_result_backend() -> str:
    return os.getenv("CELERY_RESULT_BACKEND", get_celery_broker_url())


def get_ml_ranker_enabled() -> bool:
    return os.getenv("ML_RANKER_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


def get_ml_ranker_model_dir() -> Path:
    return Path(os.getenv("ML_RANKER_MODEL_DIR", str(DEFAULT_RANKER_MODEL_DIR)))


def get_ml_ranker_blend_weight() -> float:
    return float(os.getenv("ML_RANKER_BLEND_WEIGHT", "0.35"))


def get_ml_ranker_min_labeled_rows() -> int:
    return int(os.getenv("ML_RANKER_MIN_LABELED_ROWS", "3"))


def get_redis_url() -> str:
    return os.getenv("REDIS_URL", get_celery_broker_url())


def get_cache_enabled() -> bool:
    return os.getenv("CACHE_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


def get_cache_ttl_seconds() -> int:
    return int(os.getenv("CACHE_TTL_SECONDS", "300"))


def get_cors_allowed_origins() -> list[str]:
    raw_value = os.getenv("CORS_ALLOWED_ORIGINS", "")
    if raw_value.strip():
        return [origin.strip() for origin in raw_value.split(",") if origin.strip()]
    return list(DEFAULT_CORS_ALLOWED_ORIGINS)
