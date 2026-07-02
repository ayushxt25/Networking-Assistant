from datetime import datetime, timedelta, timezone

from app.services.advanced_retrieval_service import AdvancedRetrievalResult, RetrievalScoreComponents


def test_advanced_retrieval_empty_state(client, auth_headers):
    response = client.get("/retrieval/debug?q=founder", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_advanced_retrieval_is_deterministic_and_explainable(client, auth_headers):
    client.put(
        "/profile",
        json={"goals": ["healthcare"], "interests": ["ai"], "preferred_tone": "warm"},
        headers=auth_headers,
    )
    contact = client.post(
        "/contacts",
        json={
            "name": "Asha",
            "company": "HealthGraph",
            "role": "Founder",
            "tags": ["ai", "healthcare"],
            "notes": "Strong healthcare AI operator",
            "relationship_strength": 5,
        },
        headers=auth_headers,
    ).json()
    event = client.post(
        "/events",
        json={
            "title": "Healthcare AI Summit",
            "description": "Summit for AI founders in healthcare",
            "event_date": (datetime.now(timezone.utc) + timedelta(days=3)).isoformat(),
        },
        headers=auth_headers,
    ).json()
    client.post(
        "/interactions",
        json={
            "contact_id": contact["id"],
            "event_id": event["id"],
            "interaction_type": "coffee",
            "notes": "Discussed healthcare AI partnerships",
            "sentiment": "positive",
        },
        headers=auth_headers,
    )
    client.post(
        "/follow-ups",
        json={
            "contact_id": contact["id"],
            "title": "Founder follow-up",
            "status": "pending",
            "due_date": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
        },
        headers=auth_headers,
    )
    rec = next(
        item for item in client.get("/recommendations", headers=auth_headers).json()
        if item["recommendation_type"] == "prepare_for_upcoming_event"
    )
    client.post(
        "/feedback",
        json={
            "suggestion": "Helpful retrieval-adjacent recommendation",
            "category": "accepted",
            "target_type": "recommendation",
            "target_id": rec["recommendation_id"],
        },
        headers=auth_headers,
    )

    first = client.get(
        "/retrieval/debug?q=healthcare ai founder&interests=healthcare,ai&themes=partnerships",
        headers=auth_headers,
    )
    second = client.get(
        "/retrieval/debug?q=healthcare ai founder&interests=healthcare,ai&themes=partnerships",
        headers=auth_headers,
    )
    assert first.status_code == 200
    assert [item["id"] for item in first.json()] == [item["id"] for item in second.json()]

    body = first.json()
    assert body
    scores = [item["retrieval_score"] for item in body]
    assert scores == sorted(scores, reverse=True)
    assert set(body[0]["components"].keys()) == {
        "semantic_similarity",
        "relationship_weight",
        "personalization_weight",
        "graph_weight",
        "recency_weight",
        "feedback_weight",
    }
    assert body[0]["reasons"]


def test_advanced_retrieval_fail_open_behavior(client, auth_headers, monkeypatch):
    monkeypatch.setattr(
        "app.services.advanced_retrieval_service.semantic_search_memories",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("vector down")),
    )
    response = client.get("/retrieval/debug?q=anything", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_advanced_retrieval_user_isolation(client):
    client.post("/auth/register", json={"username": "retrieval_a", "password": "passwordA123"})
    token_a = client.post(
        "/auth/login", json={"username": "retrieval_a", "password": "passwordA123"}
    ).json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}
    client.post(
        "/contacts",
        json={"name": "Private Memory", "company": "Secret", "role": "Founder", "notes": "Confidential AI", "relationship_strength": 5},
        headers=headers_a,
    )

    client.post("/auth/register", json={"username": "retrieval_b", "password": "passwordB123"})
    token_b = client.post(
        "/auth/login", json={"username": "retrieval_b", "password": "passwordB123"}
    ).json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    response = client.get("/retrieval/debug?q=confidential ai", headers=headers_b)
    assert response.status_code == 200
    assert response.json() == []


def test_context_service_uses_advanced_retrieval(client, auth_headers, monkeypatch):
    from app.routes import conversation as conversation_routes

    captured = {}

    def fake_generate_topics(themes, interests, relationship_context=None):
        captured["relationship_context"] = relationship_context
        return ["starter"]

    monkeypatch.setattr(conversation_routes, "generate_topics", fake_generate_topics)
    monkeypatch.setattr(
        "app.services.context_service.advanced_retrieve_relationship_intelligence",
        lambda **kwargs: [
            AdvancedRetrievalResult(
                id="contact:1",
                entity_type="contact",
                record_id=1,
                text="Advanced retrieval snippet",
                retrieval_score=91.7,
                components=RetrievalScoreComponents(42, 18, 12, 9, 6, 4),
                reasons=["advanced"],
                metadata={"user_id": kwargs["user_id"]},
            )
        ],
    )

    response = client.post(
        "/generate-conversation",
        json={"description": "Founder meetup", "interests": ["ai"]},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert "Advanced retrieval snippet" in captured["relationship_context"]
