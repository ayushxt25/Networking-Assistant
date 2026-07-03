from datetime import datetime, timedelta, timezone


def test_analytics_empty_state(client, auth_headers):
    response = client.get("/analytics/summary", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total_contacts"] == 0
    assert body["total_events"] == 0
    assert body["total_interactions"] == 0
    assert body["total_follow_ups"] == 0
    assert body["overdue_follow_ups_count"] == 0
    assert body["completed_follow_ups_count"] == 0
    assert body["upcoming_follow_ups_count"] == 0
    assert body["cold_contacts_count"] == 0
    assert body["average_relationship_strength"] == 0.0
    assert body["interaction_frequency"] == 0.0
    assert body["top_relationship_tags"] == []
    assert 0.0 <= body["network_health_score"] <= 100.0


def test_analytics_with_contacts_interactions_and_followups(client, auth_headers):
    contact = client.post(
        "/contacts",
        json={
            "name": "Nina",
            "company": "Orbit",
            "role": "Founder",
            "relationship_strength": 4,
            "tags": ["investor", "ai"],
        },
        headers=auth_headers,
    ).json()
    client.post(
        "/events",
        json={"title": "AI Demo Day", "goals": ["meet founders"]},
        headers=auth_headers,
    )
    client.post(
        "/interactions",
        json={
            "contact_id": contact["id"],
            "interaction_type": "coffee_chat",
            "notes": "Good discussion on partnerships",
        },
        headers=auth_headers,
    )
    client.post(
        "/follow-ups",
        json={
            "contact_id": contact["id"],
            "title": "Share deck",
            "status": "pending",
            "due_date": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
        },
        headers=auth_headers,
    )

    response = client.get("/analytics/summary", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total_contacts"] == 1
    assert body["total_events"] == 1
    assert body["total_interactions"] == 1
    assert body["total_follow_ups"] == 1
    assert body["upcoming_follow_ups_count"] == 1
    assert body["cold_contacts_count"] == 0
    assert body["average_relationship_strength"] == 4.0
    assert body["interaction_frequency"] == 1.0
    assert body["top_relationship_tags"] == ["ai", "investor"]


def test_analytics_overdue_follow_up_calculation(client, auth_headers):
    client.post(
        "/follow-ups",
        json={
            "title": "Past due note",
            "status": "pending",
            "due_date": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
        },
        headers=auth_headers,
    )
    client.post(
        "/follow-ups",
        json={
            "title": "Completed note",
            "status": "done",
            "due_date": (datetime.now(timezone.utc) - timedelta(days=4)).isoformat(),
        },
        headers=auth_headers,
    )

    response = client.get("/analytics/summary", headers=auth_headers)
    body = response.json()
    assert body["overdue_follow_ups_count"] == 1
    assert body["completed_follow_ups_count"] == 1


def test_analytics_cold_contact_calculation(client, auth_headers):
    client.post(
        "/contacts",
        json={"name": "Cold", "company": "Quiet", "role": "VC", "relationship_strength": 2},
        headers=auth_headers,
    )

    response = client.get("/analytics/summary", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["cold_contacts_count"] == 1


def test_analytics_network_health_score_range(client, auth_headers):
    contact = client.post(
        "/contacts",
        json={"name": "Asha", "company": "Spark", "role": "PM", "relationship_strength": 5},
        headers=auth_headers,
    ).json()
    client.post(
        "/interactions",
        json={
            "contact_id": contact["id"],
            "interaction_type": "email",
            "notes": "Strong follow-up momentum",
        },
        headers=auth_headers,
    )

    response = client.get("/analytics/summary", headers=auth_headers)
    score = response.json()["network_health_score"]
    assert 0.0 <= score <= 100.0


def test_analytics_user_isolation(client):
    client.post("/auth/register", json={"username": "analytics_a", "password": "passwordA123"})
    token_a = client.post(
        "/auth/login", json={"username": "analytics_a", "password": "passwordA123"}
    ).json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}
    client.post(
        "/contacts",
        json={"name": "Private", "company": "Secret", "role": "CEO", "relationship_strength": 5},
        headers=headers_a,
    )

    client.post("/auth/register", json={"username": "analytics_b", "password": "passwordB123"})
    token_b = client.post(
        "/auth/login", json={"username": "analytics_b", "password": "passwordB123"}
    ).json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    response = client.get("/analytics/summary", headers=headers_b)
    assert response.status_code == 200
    body = response.json()
    assert body["total_contacts"] == 0
    assert body["total_interactions"] == 0
    assert body["total_follow_ups"] == 0


def test_non_admin_user_can_access_user_analytics_but_not_admin_metrics(client, auth_headers):
    analytics_response = client.get("/analytics/summary", headers=auth_headers)
    assert analytics_response.status_code == 200

    metrics_response = client.get("/metrics", headers=auth_headers)
    assert metrics_response.status_code == 403
