from datetime import datetime, timedelta, timezone

import app.services.task_dispatcher as task_dispatcher

from app.services.cache_service import RedisCacheBackend, reset_cache_backend
from app.services.metrics_service import get_metrics_service


class FakeRedisClient:
    def __init__(self):
        self.store = {}

    def ping(self):
        return True

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value, ex=None):
        self.store[key] = value
        return True

    def delete(self, *keys):
        deleted = 0
        for key in keys:
            if key in self.store:
                del self.store[key]
                deleted += 1
        return deleted

    def scan_iter(self, match=None):
        prefix = (match or "").rstrip("*")
        for key in list(self.store.keys()):
            if key.startswith(prefix):
                yield key


def test_metrics_empty_state_and_uptime(client, auth_headers):
    response = client.get("/metrics", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["uptime_seconds"] >= 0
    assert body["api"]["request_count"] >= 1
    assert body["retrieval"]["retrieval_count"] == 0
    assert body["cache"]["hit_ratio"] == 0.0


def test_metrics_collection_and_summary(client, auth_headers):
    client.get("/health")
    client.post(
        "/generate-conversation",
        json={"description": "AI meetup", "interests": ["robotics"]},
        headers=auth_headers,
    )
    response = client.get("/metrics/summary", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert "summary" in body
    assert "API handled" in body["summary"]
    assert body["service_health_snapshot"] in {"ok", "degraded"}


def test_cache_metrics(client, auth_headers, monkeypatch):
    reset_cache_backend()
    monkeypatch.setattr("app.services.cache_service.build_cache_backend", lambda: RedisCacheBackend(FakeRedisClient()))
    first = client.get("/recommendations", headers=auth_headers)
    second = client.get("/recommendations", headers=auth_headers)
    assert first.status_code == 200
    assert second.status_code == 200

    metrics = client.get("/metrics", headers=auth_headers).json()
    assert metrics["cache"]["cache_hits"] >= 1
    assert metrics["cache"]["cache_misses"] >= 1


def test_retrieval_metrics_and_fail_open_behavior(client, auth_headers, monkeypatch):
    client.post(
        "/contacts",
        json={"name": "Asha", "company": "North", "role": "Founder", "notes": "Healthcare AI"},
        headers=auth_headers,
    )
    ok = client.get("/retrieval/debug?q=healthcare ai", headers=auth_headers)
    assert ok.status_code == 200

    monkeypatch.setattr(
        "app.services.advanced_retrieval_service.semantic_search_memories",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("broken")),
    )
    failed = client.get("/retrieval/debug?q=broken", headers=auth_headers)
    assert failed.status_code == 200

    metrics = client.get("/metrics", headers=auth_headers).json()
    assert metrics["retrieval"]["retrieval_count"] >= 2
    assert metrics["retrieval"]["retrieval_failures"] >= 1


def test_recommendation_and_opportunity_metrics_with_user_isolation(client):
    client.post("/auth/register", json={"username": "metrics_a", "password": "passwordA123"})
    token_a = client.post(
        "/auth/login", json={"username": "metrics_a", "password": "passwordA123"}
    ).json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}
    contact = client.post(
        "/contacts",
        json={"name": "Mina", "company": "Orbit", "role": "Founder", "relationship_strength": 5},
        headers=headers_a,
    ).json()
    client.post(
        "/follow-ups",
        json={
            "contact_id": contact["id"],
            "title": "Send note",
            "status": "done",
            "due_date": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
        },
        headers=headers_a,
    )
    rec = next(
        item for item in client.get("/recommendations", headers=headers_a).json()
        if item["recommendation_type"] == "strengthen_high_value_contact"
    )
    client.post(
        "/feedback",
        json={
            "suggestion": "helpful rec",
            "category": "accepted",
            "target_type": "recommendation",
            "target_id": rec["recommendation_id"],
        },
        headers=headers_a,
    )
    client.get("/opportunities", headers=headers_a)
    metrics_a = client.get("/metrics", headers=headers_a).json()
    assert metrics_a["recommendations"]["recommendation_count"] >= 1
    assert metrics_a["opportunities"]["opportunity_generation_count"] >= 0
    assert metrics_a["user_effectiveness"]["recommendations"]["acceptance_rate"] > 0
    assert metrics_a["user_effectiveness"]["opportunities"]["opportunity_conversion_rate"] > 0

    client.post("/auth/register", json={"username": "metrics_b", "password": "passwordB123"})
    token_b = client.post(
        "/auth/login", json={"username": "metrics_b", "password": "passwordB123"}
    ).json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}
    metrics_b = client.get("/metrics", headers=headers_b).json()
    assert metrics_b["user_effectiveness"]["recommendations"]["feedback_count"] == 0
    assert metrics_b["user_effectiveness"]["opportunities"]["tracked_follow_ups"] == 0


def test_background_task_metrics(client, auth_headers, monkeypatch):
    monkeypatch.setattr("app.services.task_dispatcher.get_celery_enabled", lambda: False)
    assert task_dispatcher.dispatch_optional_task("sync_user_semantic_memory", 1) is False
    metrics = client.get("/metrics", headers=auth_headers).json()
    assert metrics["background_tasks"]["dispatch_count"] >= 1
    assert metrics["background_tasks"]["dispatch_failures"] >= 1


def test_metrics_fail_open(monkeypatch, client, auth_headers):
    service = get_metrics_service()
    monkeypatch.setattr(service, "record_api_request", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("metrics broken")))
    response = client.get("/health")
    assert response.status_code == 200
