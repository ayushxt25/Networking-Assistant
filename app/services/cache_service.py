import hashlib
import json
from dataclasses import asdict, is_dataclass
from datetime import datetime
from typing import Any, Protocol

from app.config import get_cache_enabled, get_cache_ttl_seconds, get_redis_url
from app.services.metrics_service import get_metrics_service


class CacheBackend(Protocol):
    def get(self, key: str) -> Any | None:
        ...

    def set(self, key: str, value: Any, ttl_seconds: int) -> bool:
        ...

    def delete(self, key: str) -> bool:
        ...

    def delete_by_prefix(self, prefix: str) -> int:
        ...

    def health(self) -> dict[str, Any]:
        ...


def _json_default(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if is_dataclass(value):
        return asdict(value)
    raise TypeError(f"Unsupported cache value: {type(value)!r}")


class NoOpCacheBackend:
    def get(self, key: str) -> Any | None:
        return None

    def set(self, key: str, value: Any, ttl_seconds: int) -> bool:
        return False

    def delete(self, key: str) -> bool:
        return False

    def delete_by_prefix(self, prefix: str) -> int:
        return 0

    def health(self) -> dict[str, Any]:
        return {"status": "disabled", "backend": "noop"}


class RedisCacheBackend:
    def __init__(self, client: Any):
        self.client = client

    def get(self, key: str) -> Any | None:
        payload = self.client.get(key)
        if payload is None:
            return None
        return json.loads(payload)

    def set(self, key: str, value: Any, ttl_seconds: int) -> bool:
        payload = json.dumps(value, default=_json_default)
        return bool(self.client.set(key, payload, ex=ttl_seconds))

    def delete(self, key: str) -> bool:
        return bool(self.client.delete(key))

    def delete_by_prefix(self, prefix: str) -> int:
        keys = list(self.client.scan_iter(match=f"{prefix}*"))
        if not keys:
            return 0
        return int(self.client.delete(*keys))

    def health(self) -> dict[str, Any]:
        try:
            self.client.ping()
            return {"status": "ok", "backend": "redis"}
        except Exception as exc:
            return {"status": "error", "backend": "redis", "detail": str(exc)}


def build_cache_backend() -> CacheBackend:
    if not get_cache_enabled():
        return NoOpCacheBackend()

    try:
        import redis

        client = redis.Redis.from_url(
            get_redis_url(),
            decode_responses=True,
            socket_connect_timeout=0.1,
            socket_timeout=0.1,
        )
        client.ping()
        return RedisCacheBackend(client)
    except Exception:
        return NoOpCacheBackend()


_cache_backend: CacheBackend | None = None


def get_cache_backend() -> CacheBackend:
    global _cache_backend
    if _cache_backend is None:
        _cache_backend = build_cache_backend()
    return _cache_backend


def reset_cache_backend() -> None:
    global _cache_backend
    _cache_backend = None


def cache_key_for_user(user_id: int, suffix: str) -> str:
    return f"user:{user_id}:{suffix}"


def semantic_search_cache_key(user_id: int, query_text: str, top_k: int) -> str:
    digest = hashlib.sha1(query_text.encode("utf-8")).hexdigest()
    return cache_key_for_user(user_id, f"semantic_search:{top_k}:{digest}")


def get_cached_json(key: str) -> Any | None:
    try:
        value = get_cache_backend().get(key)
        if value is None:
            get_metrics_service().record_cache_miss()
        else:
            get_metrics_service().record_cache_hit()
        return value
    except Exception:
        try:
            get_metrics_service().record_cache_miss()
        except Exception:
            pass
        return None


def set_cached_json(key: str, value: Any, ttl_seconds: int | None = None) -> bool:
    try:
        return get_cache_backend().set(key, value, ttl_seconds or get_cache_ttl_seconds())
    except Exception:
        return False


def delete_cached_key(key: str) -> bool:
    try:
        return get_cache_backend().delete(key)
    except Exception:
        return False


def invalidate_user_cache(user_id: int) -> int:
    try:
        return get_cache_backend().delete_by_prefix(cache_key_for_user(user_id, ""))
    except Exception:
        return 0


def get_cache_health() -> dict[str, Any]:
    try:
        return get_cache_backend().health()
    except Exception as exc:
        return {"status": "error", "backend": "unknown", "detail": str(exc)}
