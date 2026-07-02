from datetime import datetime, timedelta, timezone


def test_personalization_profile_empty_state(client, auth_headers):
    response = client.get("/personalization/profile", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["preference_vector"] == {}
    assert body["top_preferences"] == []
    assert body["confidence_score"] == 0.0
    assert body["learning_status"] == "cold_start"


def test_personalization_learns_preferences_and_keeps_recommendations_deterministic(client, auth_headers):
    founder = client.post(
        "/contacts",
        json={"name": "Founder Contact", "company": "Orbit", "role": "Founder", "tags": ["ai"], "relationship_strength": 4},
        headers=auth_headers,
    ).json()
    recruiter = client.post(
        "/contacts",
        json={"name": "Recruiter Contact", "company": "Orbit", "role": "Recruiter", "tags": ["talent"], "relationship_strength": 4},
        headers=auth_headers,
    ).json()

    baseline = client.get("/recommendations", headers=auth_headers).json()
    founder_rec = next(
        item for item in baseline
        if item["recommendation_type"] == "strengthen_high_value_contact"
        and item["related_contact_id"] == founder["id"]
    )

    client.post(
        "/feedback",
        json={
            "suggestion": "Yes to founders",
            "category": "accepted",
            "target_type": "recommendation",
            "target_id": founder_rec["recommendation_id"],
        },
        headers=auth_headers,
    )

    first = client.get("/recommendations", headers=auth_headers).json()
    second = client.get("/recommendations", headers=auth_headers).json()
    assert [item["recommendation_id"] for item in first] == [item["recommendation_id"] for item in second]

    founder_tuned = next(
        item for item in first
        if item["recommendation_type"] == "strengthen_high_value_contact"
        and item["related_contact_id"] == founder["id"]
    )
    recruiter_tuned = next(
        item for item in first
        if item["recommendation_type"] == "strengthen_high_value_contact"
        and item["related_contact_id"] == recruiter["id"]
    )
    assert founder_tuned["priority_score"] > recruiter_tuned["priority_score"]
    assert "Personalization adjusted score by" in founder_tuned["reason"]

    profile = client.get("/personalization/profile", headers=auth_headers).json()
    assert "strengthen_high_value_contact" in profile["preferred_recommendation_categories"]
    assert "founder" in profile["preferred_contact_categories"]
    assert profile["confidence_score"] > 0.0


def test_personalization_rejected_recommendation_penalty_and_explainability(client, auth_headers):
    contact = client.post(
        "/contacts",
        json={"name": "Penalty", "company": "Quiet", "role": "Founder", "relationship_strength": 5},
        headers=auth_headers,
    ).json()
    base = client.get("/recommendations", headers=auth_headers).json()
    base_item = next(
        item for item in base
        if item["recommendation_type"] == "strengthen_high_value_contact"
        and item["related_contact_id"] == contact["id"]
    )

    client.post(
        "/feedback",
        json={
            "suggestion": "Not now",
            "category": "dismissed",
            "target_type": "recommendation",
            "target_id": base_item["recommendation_id"],
        },
        headers=auth_headers,
    )

    tuned = client.get("/recommendations", headers=auth_headers).json()
    tuned_item = next(
        item for item in tuned
        if item["recommendation_type"] == "strengthen_high_value_contact"
        and item["related_contact_id"] == contact["id"]
    )
    assert tuned_item["priority_score"] < base_item["priority_score"]
    assert "Personalization adjusted score by" in tuned_item["reason"]
    assert "dismisses" in tuned_item["reason"] or "deprioritizes" in tuned_item["reason"]


def test_personalization_can_reorder_relationship_priorities(client, auth_headers):
    founder = client.post(
        "/contacts",
        json={"name": "Zulu", "company": "Orbit", "role": "Founder", "relationship_strength": 4},
        headers=auth_headers,
    ).json()
    investor = client.post(
        "/contacts",
        json={"name": "Alpha", "company": "Orbit", "role": "Investor", "relationship_strength": 4},
        headers=auth_headers,
    ).json()

    recommendations = client.get("/recommendations", headers=auth_headers).json()
    founder_rec = next(
        item for item in recommendations
        if item["recommendation_type"] == "strengthen_high_value_contact"
        and item["related_contact_id"] == founder["id"]
    )
    client.post(
        "/feedback",
        json={
            "suggestion": "Prefer founders",
            "category": "accepted",
            "target_type": "recommendation",
            "target_id": founder_rec["recommendation_id"],
        },
        headers=auth_headers,
    )

    response = client.get("/relationships/scores", headers=auth_headers)
    assert response.status_code == 200
    names = [item["name"] for item in response.json()["scores"]]
    assert names[0] == "Zulu"
    assert "Alpha" in names


def test_personalization_opportunities_and_user_isolation(client):
    client.post("/auth/register", json={"username": "personal_a", "password": "passwordA123"})
    token_a = client.post(
        "/auth/login", json={"username": "personal_a", "password": "passwordA123"}
    ).json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}
    contact = client.post(
        "/contacts",
        json={"name": "Bridge", "company": "Orbit", "role": "Founder", "relationship_strength": 5},
        headers=headers_a,
    ).json()
    event = client.post(
        "/events",
        json={"title": "Founder Summit", "event_date": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()},
        headers=headers_a,
    ).json()
    client.post(
        "/interactions",
        json={"contact_id": contact["id"], "event_id": event["id"], "interaction_type": "coffee", "notes": "Great founder chat"},
        headers=headers_a,
    )
    rec = next(
        item for item in client.get("/recommendations", headers=headers_a).json()
        if item["recommendation_type"] == "prepare_for_upcoming_event"
    )
    client.post(
        "/feedback",
        json={
            "suggestion": "Love event prep",
            "category": "accepted",
            "target_type": "recommendation",
            "target_id": rec["recommendation_id"],
        },
        headers=headers_a,
    )

    opportunities = client.get("/opportunities", headers=headers_a).json()
    prep = next(item for item in opportunities if item["opportunity_type"] == "prepare_for_upcoming_event")
    assert "Personalization adjusted score by" in prep["reason"]
    assert any(signal.startswith("personalization_boost:") for signal in prep["supporting_signals"])

    client.post("/auth/register", json={"username": "personal_b", "password": "passwordB123"})
    token_b = client.post(
        "/auth/login", json={"username": "personal_b", "password": "passwordB123"}
    ).json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    profile_b = client.get("/personalization/profile", headers=headers_b)
    assert profile_b.status_code == 200
    assert profile_b.json()["top_preferences"] == []
