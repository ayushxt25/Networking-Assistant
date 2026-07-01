from datetime import datetime


def test_contacts_crud_flow(client, auth_headers):
    create_response = client.post(
        "/contacts",
        json={
            "name": "Priya Shah",
            "company": "Acme",
            "role": "Founder",
            "email": "priya@example.com",
            "tags": ["investor", "saas"],
            "relationship_strength": 4,
        },
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    contact = create_response.json()
    assert contact["name"] == "Priya Shah"
    assert contact["tags"] == ["investor", "saas"]

    list_response = client.get("/contacts", headers=auth_headers)
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    update_response = client.put(
        f"/contacts/{contact['id']}",
        json={"notes": "Met after keynote", "tags": ["warm lead"]},
        headers=auth_headers,
    )
    assert update_response.status_code == 200
    assert update_response.json()["notes"] == "Met after keynote"
    assert update_response.json()["tags"] == ["warm lead"]

    delete_response = client.delete(f"/contacts/{contact['id']}", headers=auth_headers)
    assert delete_response.status_code == 200
    assert delete_response.json()["status"] == "ok"


def test_events_crud_flow(client, auth_headers):
    response = client.post(
        "/events",
        json={
            "title": "AI Summit",
            "location": "Bangalore",
            "event_date": datetime(2026, 7, 10, 18, 0, 0).isoformat(),
            "goals": ["meet founders", "find design partners"],
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    event = response.json()
    assert event["goals"] == ["meet founders", "find design partners"]

    response = client.put(
        f"/events/{event['id']}",
        json={"description": "Two-day industry event"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["description"] == "Two-day industry event"


def test_interactions_and_follow_ups_support_contact_and_event_links(client, auth_headers):
    contact = client.post(
        "/contacts",
        json={"name": "Nina", "company": "Orbit", "role": "VP Partnerships"},
        headers=auth_headers,
    ).json()
    event = client.post(
        "/events",
        json={"title": "Fintech Mixer"},
        headers=auth_headers,
    ).json()

    interaction_response = client.post(
        "/interactions",
        json={
            "contact_id": contact["id"],
            "event_id": event["id"],
            "interaction_type": "in_person",
            "notes": "Good chemistry",
            "sentiment": "positive",
        },
        headers=auth_headers,
    )
    assert interaction_response.status_code == 201
    interaction = interaction_response.json()
    assert interaction["contact_id"] == contact["id"]
    assert interaction["event_id"] == event["id"]

    follow_up_response = client.post(
        "/follow-ups",
        json={
            "contact_id": contact["id"],
            "event_id": event["id"],
            "title": "Send intro deck",
            "status": "pending",
        },
        headers=auth_headers,
    )
    assert follow_up_response.status_code == 201
    follow_up = follow_up_response.json()
    assert follow_up["title"] == "Send intro deck"

    follow_up_update = client.put(
        f"/follow-ups/{follow_up['id']}",
        json={"status": "done"},
        headers=auth_headers,
    )
    assert follow_up_update.status_code == 200
    assert follow_up_update.json()["status"] == "done"


def test_profile_upsert_flow(client, auth_headers):
    missing_response = client.get("/profile", headers=auth_headers)
    assert missing_response.status_code == 404

    upsert_response = client.put(
        "/profile",
        json={
            "full_name": "Ayush",
            "headline": "Operator",
            "goals": ["build relationships"],
            "interests": ["ai", "communities"],
            "preferred_tone": "warm",
        },
        headers=auth_headers,
    )
    assert upsert_response.status_code == 200
    profile = upsert_response.json()
    assert profile["goals"] == ["build relationships"]
    assert profile["interests"] == ["ai", "communities"]

    get_response = client.get("/profile", headers=auth_headers)
    assert get_response.status_code == 200
    assert get_response.json()["full_name"] == "Ayush"


def test_new_routes_are_user_scoped(client):
    client.post("/auth/register", json={"username": "user_a", "password": "passwordA123"})
    token_a = client.post(
        "/auth/login", json={"username": "user_a", "password": "passwordA123"}
    ).json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    contact = client.post(
        "/contacts",
        json={"name": "Hidden Contact", "company": "Stealth", "role": "CEO"},
        headers=headers_a,
    ).json()

    client.post("/auth/register", json={"username": "user_b", "password": "passwordB123"})
    token_b = client.post(
        "/auth/login", json={"username": "user_b", "password": "passwordB123"}
    ).json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    list_response = client.get("/contacts", headers=headers_b)
    assert list_response.status_code == 200
    assert list_response.json() == []

    detail_response = client.get(f"/contacts/{contact['id']}", headers=headers_b)
    assert detail_response.status_code == 404


def test_linked_entities_must_belong_to_current_user(client):
    client.post("/auth/register", json={"username": "owner", "password": "passwordA123"})
    owner_token = client.post(
        "/auth/login", json={"username": "owner", "password": "passwordA123"}
    ).json()["access_token"]
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    owner_contact = client.post(
        "/contacts",
        json={"name": "Owner Contact", "company": "Owner Co", "role": "Lead"},
        headers=owner_headers,
    ).json()

    client.post("/auth/register", json={"username": "other", "password": "passwordB123"})
    other_token = client.post(
        "/auth/login", json={"username": "other", "password": "passwordB123"}
    ).json()["access_token"]
    other_headers = {"Authorization": f"Bearer {other_token}"}

    response = client.post(
        "/interactions",
        json={
            "contact_id": owner_contact["id"],
            "interaction_type": "email",
            "notes": "Should fail",
        },
        headers=other_headers,
    )
    assert response.status_code == 404


def test_dispatch_on_create(client, auth_headers, monkeypatch):
    calls = []

    def fake_dispatch(user_id):
        calls.append(user_id)
        return {
            "sync_user_semantic_memory": True,
            "refresh_user_analytics": True,
            "refresh_user_recommendations": True,
        }

    monkeypatch.setattr("app.routes.relationship_data.dispatch_user_refreshes", fake_dispatch)

    response = client.post(
        "/contacts",
        json={"name": "Dispatch Create", "company": "Acme", "role": "Founder"},
        headers=auth_headers,
    )

    assert response.status_code == 201
    assert len(calls) == 1


def test_dispatch_on_update(client, auth_headers, monkeypatch):
    calls = []

    def fake_dispatch(user_id):
        calls.append(user_id)
        return {
            "sync_user_semantic_memory": True,
            "refresh_user_analytics": True,
            "refresh_user_recommendations": True,
        }

    contact = client.post(
        "/contacts",
        json={"name": "Dispatch Update", "company": "Acme", "role": "Founder"},
        headers=auth_headers,
    ).json()
    calls.clear()
    monkeypatch.setattr("app.routes.relationship_data.dispatch_user_refreshes", fake_dispatch)

    response = client.put(
        f"/contacts/{contact['id']}",
        json={"notes": "Updated"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert len(calls) == 1


def test_dispatch_on_delete(client, auth_headers, monkeypatch):
    calls = []

    def fake_dispatch(user_id):
        calls.append(user_id)
        return {
            "sync_user_semantic_memory": True,
            "refresh_user_analytics": True,
            "refresh_user_recommendations": True,
        }

    profile = client.put(
        "/profile",
        json={"full_name": "Delete Me"},
        headers=auth_headers,
    )
    assert profile.status_code == 200
    calls.clear()
    monkeypatch.setattr("app.routes.relationship_data.dispatch_user_refreshes", fake_dispatch)

    response = client.delete("/profile", headers=auth_headers)

    assert response.status_code == 200
    assert len(calls) == 1


def test_dispatch_fail_open_behavior(client, auth_headers, monkeypatch):
    def fake_dispatch(user_id):
        return {
            "sync_user_semantic_memory": False,
            "refresh_user_analytics": False,
            "refresh_user_recommendations": False,
        }

    monkeypatch.setattr("app.routes.relationship_data.dispatch_user_refreshes", fake_dispatch)

    response = client.post(
        "/events",
        json={"title": "Fail Open Event"},
        headers=auth_headers,
    )

    assert response.status_code == 201
    assert response.json()["title"] == "Fail Open Event"
