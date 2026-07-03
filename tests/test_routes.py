"""
Integration tests for the conversation API routes, using FastAPI's
TestClient. All protected routes now require a valid bearer token (see the
`auth_headers` fixture in conftest.py), and history/feedback are scoped to
the authenticated user.
"""


def test_health_check(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_protected_route_without_token_returns_401(client):
    response = client.post("/analyze-event", json={"description": "A conference"})
    assert response.status_code == 401


def test_protected_route_with_invalid_token_returns_401(client):
    response = client.post(
        "/analyze-event",
        json={"description": "A conference"},
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert response.status_code == 401


def test_analyze_event_returns_themes(client, auth_headers):
    response = client.post(
        "/analyze-event",
        json={"description": "A conference on renewable energy"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert "themes" in body
    assert isinstance(body["themes"], list)


def test_analyze_event_missing_description_returns_422(client, auth_headers):
    response = client.post("/analyze-event", json={}, headers=auth_headers)
    assert response.status_code == 422


def test_fact_check_endpoint(client, auth_headers):
    response = client.post(
        "/fact-check", json={"query": "blockchain"}, headers=auth_headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "blockchain"
    assert "summary" in body


def test_generate_conversation_returns_themes_and_suggestions(client, auth_headers):
    response = client.post(
        "/generate-conversation",
        json={"description": "AI for Sustainable Cities", "interests": ["climate change"]},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert "themes" in body
    assert "suggestions" in body
    assert isinstance(body["suggestions"], list)


def test_generate_conversation_missing_interests_returns_422(client, auth_headers):
    response = client.post(
        "/generate-conversation", json={"description": "AI conference"}, headers=auth_headers
    )
    assert response.status_code == 422


def test_generate_conversation_appears_in_history(client, auth_headers):
    client.post(
        "/generate-conversation",
        json={"description": "AI for Sustainable Cities", "interests": ["climate change"]},
        headers=auth_headers,
    )

    history_response = client.get("/history", headers=auth_headers)
    assert history_response.status_code == 200
    history = history_response.json()
    assert len(history) == 1
    assert history[0]["description"] == "AI for Sustainable Cities"
    assert history[0]["interests"] == ["climate change"]


def test_generate_conversation_long_input_does_not_crash_on_topic_generator_value_error(
    client, auth_headers, monkeypatch
):
    from app.routes import conversation as conversation_routes

    def fake_generate_topics(themes, interests, relationship_context=None):
        raise ValueError("Input length of input_ids is 80, but `max_length` is set to 80.")

    monkeypatch.setattr(conversation_routes, "generate_topics", fake_generate_topics)

    response = client.post(
        "/generate-conversation",
        json={
            "description": " ".join(["long-event-context"] * 200),
            "interests": ["ai", "networking"],
        },
        headers=auth_headers,
    )

    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "http_error"
    assert body["error"]["message"] == "Conversation generation is temporarily unavailable"


def test_generate_conversation_replaces_known_gibberish_pattern_with_fallback(
    client, auth_headers, monkeypatch
):
    from app.routes import conversation as conversation_routes

    def fake_generate_topics(themes, interests, relationship_context=None):
        return [
            "Ejfhe | efaijdww | ejfhe",
            "zzzz zzzz zzzz",
            "qwert",
        ]

    monkeypatch.setattr(conversation_routes, "generate_topics", fake_generate_topics)

    response = client.post(
        "/generate-conversation",
        json={"description": "AI for Sustainable Cities", "interests": ["climate change"]},
        headers=auth_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["suggestions"]
    assert all("|" not in item for item in body["suggestions"])
    assert any(
        "climate change" in item.lower() or "ai for sustainable cities" in item.lower()
        for item in body["suggestions"]
    )


def test_feedback_endpoint_accepts_valid_action(client, auth_headers):
    response = client.post(
        "/feedback",
        json={"suggestion": "Ask about their work", "action": "like"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_feedback_endpoint_rejects_invalid_action(client, auth_headers):
    response = client.post(
        "/feedback",
        json={"suggestion": "Ask about their work", "action": "maybe"},
        headers=auth_headers,
    )
    assert response.status_code == 400


def test_feedback_appears_in_feedback_history(client, auth_headers):
    client.post(
        "/feedback",
        json={"suggestion": "Ask about their work", "action": "like"},
        headers=auth_headers,
    )

    response = client.get("/feedback-history", headers=auth_headers)
    assert response.status_code == 200
    entries = response.json()
    assert len(entries) == 1
    assert entries[0]["suggestion"] == "Ask about their work"
    assert entries[0]["action"] == "like"


def test_feedback_can_be_tied_to_recommendation(client, auth_headers):
    response = client.post(
        "/feedback",
        json={
            "suggestion": "Reconnect with Mina",
            "category": "accepted",
            "target_type": "recommendation",
            "target_id": "rec-1",
            "notes": "I plan to do this today",
        },
        headers=auth_headers,
    )
    assert response.status_code == 200

    history = client.get("/feedback-history", headers=auth_headers).json()
    assert history[0]["category"] == "accepted"
    assert history[0]["target_type"] == "recommendation"
    assert history[0]["target_id"] == "rec-1"


def test_feedback_can_be_tied_to_generation_output(client, auth_headers):
    response = client.post(
        "/feedback",
        json={
            "suggestion": "What inspired you to build this?",
            "category": "wrong_tone",
            "target_type": "generation_suggestion",
            "target_id": "gen-1",
        },
        headers=auth_headers,
    )
    assert response.status_code == 200

    history = client.get("/feedback-history", headers=auth_headers).json()
    assert history[0]["action"] == "dislike"
    assert history[0]["category"] == "wrong_tone"


def test_feedback_can_be_tied_to_fact_check_result(client, auth_headers):
    response = client.post(
        "/feedback",
        json={
            "suggestion": "AI infrastructure market",
            "category": "not_helpful",
            "target_type": "fact_check",
            "target_id": "fact-check:ai-infrastructure-market",
            "notes": "Needed more detail",
        },
        headers=auth_headers,
    )
    assert response.status_code == 200

    history = client.get("/feedback-history", headers=auth_headers).json()
    assert history[0]["target_type"] == "fact_check"
    assert history[0]["target_id"] == "fact-check:ai-infrastructure-market"
    assert history[0]["category"] == "not_helpful"


def test_feedback_can_be_tied_to_app_experience(client, auth_headers):
    response = client.post(
        "/feedback",
        json={
            "suggestion": "App feedback: bug",
            "category": "not_helpful",
            "target_type": "app_experience",
            "target_id": "/help",
            "notes": "The onboarding language could be clearer.",
        },
        headers=auth_headers,
    )
    assert response.status_code == 200

    history = client.get("/feedback-history", headers=auth_headers).json()
    assert history[0]["target_type"] == "app_experience"
    assert history[0]["target_id"] == "/help"
    assert history[0]["category"] == "not_helpful"


def test_feedback_summary_endpoint(client, auth_headers):
    client.post(
        "/feedback",
        json={
            "suggestion": "Ask about their team",
            "category": "too_generic",
            "target_type": "generation_suggestion",
        },
        headers=auth_headers,
    )
    client.post(
        "/feedback",
        json={
            "suggestion": "Follow up with Priya",
            "category": "helpful",
            "target_type": "recommendation",
        },
        headers=auth_headers,
    )

    response = client.get("/feedback/summary", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["generation_quality"]["category_counts"]["too_generic"] == 1
    assert body["recommendation_quality"]["category_counts"]["helpful"] == 1
    assert body["user_preferences"]["specificity_adjustment_signals"] == 1


def test_feedback_summary_is_user_isolated(client):
    client.post("/auth/register", json={"username": "feedback_a", "password": "passwordA123"})
    token_a = client.post(
        "/auth/login", json={"username": "feedback_a", "password": "passwordA123"}
    ).json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}
    client.post(
        "/feedback",
        json={
            "suggestion": "Private recommendation",
            "category": "accepted",
            "target_type": "recommendation",
        },
        headers=headers_a,
    )

    client.post("/auth/register", json={"username": "feedback_b", "password": "passwordB123"})
    token_b = client.post(
        "/auth/login", json={"username": "feedback_b", "password": "passwordB123"}
    ).json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    response = client.get("/feedback/summary", headers=headers_b)
    assert response.status_code == 200
    assert response.json()["recommendation_quality"]["total"] == 0


def test_feedback_endpoint_rejects_invalid_category(client, auth_headers):
    response = client.post(
        "/feedback",
        json={"suggestion": "Ask about their work", "category": "confusing"},
        headers=auth_headers,
    )
    assert response.status_code == 400


def test_history_is_isolated_per_user(client):
    # User A generates a conversation.
    client.post("/auth/register", json={"username": "user_a", "password": "passwordA123"})
    token_a = client.post(
        "/auth/login", json={"username": "user_a", "password": "passwordA123"}
    ).json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    client.post(
        "/generate-conversation",
        json={"description": "User A's event", "interests": ["AI"]},
        headers=headers_a,
    )

    # User B should see an empty history, not User A's data.
    client.post("/auth/register", json={"username": "user_b", "password": "passwordB123"})
    token_b = client.post(
        "/auth/login", json={"username": "user_b", "password": "passwordB123"}
    ).json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    history_b = client.get("/history", headers=headers_b).json()
    assert history_b == []

    history_a = client.get("/history", headers=headers_a).json()
    assert len(history_a) == 1
    assert history_a[0]["description"] == "User A's event"
