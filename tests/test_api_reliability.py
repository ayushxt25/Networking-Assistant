from datetime import datetime, timedelta, timezone


def test_contacts_pagination_filtering_and_sorting(client, auth_headers):
    client.post(
        "/contacts",
        json={"name": "Zara", "company": "Beta", "role": "Founder", "relationship_strength": 2, "tags": ["ops"]},
        headers=auth_headers,
    )
    client.post(
        "/contacts",
        json={"name": "Aman", "company": "Alpha", "role": "Engineer", "relationship_strength": 5, "tags": ["ai"]},
        headers=auth_headers,
    )

    response = client.get(
        "/contacts?company=Alpha&sort_by=name&sort_order=asc&limit=1&offset=0",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["name"] == "Aman"


def test_follow_ups_filtering_and_pagination(client, auth_headers):
    contact = client.post(
        "/contacts",
        json={"name": "Mina", "company": "Orbit", "role": "Founder"},
        headers=auth_headers,
    ).json()
    client.post(
        "/follow-ups",
        json={"contact_id": contact["id"], "title": "Pending", "status": "pending"},
        headers=auth_headers,
    )
    client.post(
        "/follow-ups",
        json={"contact_id": contact["id"], "title": "Done", "status": "done"},
        headers=auth_headers,
    )

    response = client.get("/follow-ups?status=pending&limit=5", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["title"] == "Pending"


def test_recommendations_support_filtering_and_pagination(client, auth_headers):
    contact = client.post(
        "/contacts",
        json={"name": "Priya", "company": "North", "role": "Founder", "relationship_strength": 5},
        headers=auth_headers,
    ).json()
    client.post(
        "/follow-ups",
        json={
            "contact_id": contact["id"],
            "title": "Overdue",
            "status": "pending",
            "due_date": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
        },
        headers=auth_headers,
    )

    response = client.get(
        "/recommendations?recommendation_type=complete_overdue_follow_up&limit=1&offset=0",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["recommendation_type"] == "complete_overdue_follow_up"


def test_audit_logs_filtering(client, auth_headers):
    client.post(
        "/generate-conversation",
        json={"description": "AI meetup", "interests": ["robotics"]},
        headers=auth_headers,
    )

    response = client.get("/audit/logs?event_type=generation_request&limit=10", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body
    assert all(item["event_type"] == "generation_request" for item in body)


def test_standardized_unauthorized_error_and_correlation_id(client):
    response = client.post("/analyze-event", json={"description": "Conference"})
    assert response.status_code == 401
    assert response.headers["X-Correlation-ID"]
    body = response.json()
    assert body["error"]["code"] == "unauthorized"
    assert body["correlation_id"] == response.headers["X-Correlation-ID"]


def test_standardized_validation_error(client, auth_headers):
    response = client.post("/generate-conversation", json={"description": "AI meetup"}, headers=auth_headers)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_standardized_not_found_error(client, auth_headers):
    response = client.get("/contacts/999", headers=auth_headers)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_rate_limit_error_is_standardized(client, auth_headers, monkeypatch):
    monkeypatch.setattr("app.routes.conversation.fact_check", lambda query: "ok")
    last_response = None
    for _ in range(21):
        last_response = client.post("/fact-check", json={"query": "topic"}, headers=auth_headers)
    assert last_response is not None
    assert last_response.status_code == 429
    assert last_response.json()["error"]["code"] == "rate_limit_exceeded"


def test_health_endpoints_report_dependencies(client):
    for path in ("/health", "/ready", "/live"):
        response = client.get(path)
        assert response.status_code == 200

    ready_response = client.get("/ready")
    body = ready_response.json()
    assert "dependencies" in body
    assert set(body["dependencies"].keys()) == {"database", "vector_store", "redis", "ml_ranker"}


def test_correlation_id_header_is_preserved(client):
    response = client.get("/health", headers={"X-Correlation-ID": "corr-test-123"})
    assert response.status_code == 200
    assert response.headers["X-Correlation-ID"] == "corr-test-123"
