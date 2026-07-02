from datetime import datetime, timedelta, timezone


def test_opportunities_empty_state(client, auth_headers):
    response = client.get("/opportunities", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_opportunities_overdue_follow_up_and_no_duplicates(client, auth_headers):
    contact = client.post(
        "/contacts",
        json={"name": "Mina", "company": "Orbit", "role": "Founder", "relationship_strength": 4},
        headers=auth_headers,
    ).json()
    follow_up = client.post(
        "/follow-ups",
        json={
            "contact_id": contact["id"],
            "title": "Overdue note",
            "status": "pending",
            "due_date": (datetime.now(timezone.utc) - timedelta(days=4)).isoformat(),
        },
        headers=auth_headers,
    ).json()

    response = client.get("/opportunities", headers=auth_headers)
    assert response.status_code == 200
    opportunities = response.json()
    overdue = [item for item in opportunities if item["opportunity_type"] == "follow_up_overdue"]
    assert len(overdue) == 1
    assert overdue[0]["related_follow_up_id"] == follow_up["id"]


def test_opportunities_cold_contact_and_priority_ordering(client, auth_headers):
    cold = client.post(
        "/contacts",
        json={"name": "Cold", "company": "Quiet", "role": "Advisor", "relationship_strength": 2},
        headers=auth_headers,
    ).json()
    urgent = client.post(
        "/contacts",
        json={"name": "Urgent", "company": "Orbit", "role": "Founder", "relationship_strength": 5},
        headers=auth_headers,
    ).json()
    client.post(
        "/follow-ups",
        json={
            "contact_id": urgent["id"],
            "title": "Past due",
            "status": "pending",
            "due_date": (datetime.now(timezone.utc) - timedelta(days=8)).isoformat(),
        },
        headers=auth_headers,
    )

    response = client.get("/opportunities", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert any(item["opportunity_type"] == "reconnect_with_cold_contact" and item["related_contact_id"] == cold["id"] for item in body)
    scores = [item["priority_score"] for item in body]
    assert scores == sorted(scores, reverse=True)


def test_opportunities_strategic_bridge_and_upcoming_event(client, auth_headers):
    strategic = client.post(
        "/contacts",
        json={"name": "Bridge", "company": "Orbit", "role": "Founder", "tags": ["ai", "fintech"], "relationship_strength": 5},
        headers=auth_headers,
    ).json()
    left = client.post(
        "/contacts",
        json={"name": "Left", "company": "Orbit", "role": "Founder", "tags": ["ai"], "relationship_strength": 3},
        headers=auth_headers,
    ).json()
    right = client.post(
        "/contacts",
        json={"name": "Right", "company": "Nova", "role": "Investor", "tags": ["fintech"], "relationship_strength": 3},
        headers=auth_headers,
    ).json()
    event = client.post(
        "/events",
        json={"title": "AI Summit", "event_date": (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()},
        headers=auth_headers,
    ).json()
    client.post(
        "/interactions",
        json={"contact_id": strategic["id"], "event_id": event["id"], "interaction_type": "panel", "notes": "Met at summit"},
        headers=auth_headers,
    )
    client.post(
        "/interactions",
        json={"contact_id": left["id"], "event_id": event["id"], "interaction_type": "coffee", "notes": "Met at summit"},
        headers=auth_headers,
    )
    client.post(
        "/interactions",
        json={"contact_id": strategic["id"], "interaction_type": "email", "notes": "Important relationship"},
        headers=auth_headers,
    )

    response = client.get("/opportunities", headers=auth_headers)
    body = response.json()
    assert any(item["opportunity_type"] == "strengthen_strategic_contact" and item["related_contact_id"] == strategic["id"] for item in body)
    assert any(item["opportunity_type"] == "activate_bridge_contact" and item["related_contact_id"] == strategic["id"] for item in body)
    assert any(item["opportunity_type"] == "prepare_for_upcoming_event" and item["related_event_id"] == event["id"] for item in body)
    assert any(item["opportunity_type"] == "nurture_high_score_relationship" and item["related_contact_id"] == strategic["id"] for item in body)


def test_opportunities_user_isolation(client):
    client.post("/auth/register", json={"username": "opp_a", "password": "passwordA123"})
    token_a = client.post(
        "/auth/login", json={"username": "opp_a", "password": "passwordA123"}
    ).json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}
    client.post(
        "/contacts",
        json={"name": "Private Opp", "company": "Secret", "role": "CEO", "relationship_strength": 5},
        headers=headers_a,
    )

    client.post("/auth/register", json={"username": "opp_b", "password": "passwordB123"})
    token_b = client.post(
        "/auth/login", json={"username": "opp_b", "password": "passwordB123"}
    ).json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    response = client.get("/opportunities", headers=headers_b)
    assert response.status_code == 200
    assert response.json() == []


def test_opportunity_lifecycle_endpoint_and_response_fields(client, auth_headers):
    contact = client.post(
        "/contacts",
        json={"name": "Opp Lifecycle", "company": "Quiet", "role": "Advisor", "relationship_strength": 2},
        headers=auth_headers,
    ).json()

    opportunity = next(
        item
        for item in client.get("/opportunities", headers=auth_headers).json()
        if item["opportunity_type"] == "reconnect_with_cold_contact"
        and item["related_contact_id"] == contact["id"]
    )
    assert opportunity["lifecycle_status"] == "new"
    assert opportunity["converted_follow_up_id"] is None

    mutation = client.post(
        "/action-lifecycle",
        json={
            "entity_kind": "opportunity",
            "entity_id": opportunity["opportunity_id"],
            "entity_type": opportunity["opportunity_type"],
            "status": "dismissed",
        },
        headers=auth_headers,
    )
    assert mutation.status_code == 200
    assert mutation.json()["status"] == "dismissed"

    updated = next(
        item
        for item in client.get("/opportunities", headers=auth_headers).json()
        if item["opportunity_id"] == opportunity["opportunity_id"]
    )
    assert updated["lifecycle_status"] == "dismissed"
    assert updated["lifecycle_updated_at"] is not None
