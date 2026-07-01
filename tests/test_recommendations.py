from datetime import datetime, timedelta, timezone


def test_recommendations_from_overdue_followups(client, auth_headers):
    contact = client.post(
        "/contacts",
        json={"name": "Mina", "company": "Orbit", "role": "Founder", "relationship_strength": 4},
        headers=auth_headers,
    ).json()

    client.post(
        "/follow-ups",
        json={
            "contact_id": contact["id"],
            "title": "Send intro",
            "status": "pending",
            "due_date": (datetime.now(timezone.utc) - timedelta(days=3)).isoformat(),
        },
        headers=auth_headers,
    )

    response = client.get("/recommendations", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert any(item["recommendation_type"] == "complete_overdue_follow_up" for item in body)


def test_recommendations_from_cold_contacts(client, auth_headers):
    contact = client.post(
        "/contacts",
        json={"name": "Raj", "company": "Delta", "role": "Investor", "relationship_strength": 2},
        headers=auth_headers,
    ).json()

    response = client.get("/recommendations", headers=auth_headers)
    assert response.status_code == 200
    assert any(
        item["recommendation_type"] == "reconnect_with_cold_relationship"
        and item["related_contact_id"] == contact["id"]
        for item in response.json()
    )


def test_recommendation_ids_are_generated_stably(client, auth_headers):
    client.post(
        "/contacts",
        json={"name": "Stable", "company": "Delta", "role": "Investor", "relationship_strength": 5},
        headers=auth_headers,
    )

    first = client.get("/recommendations", headers=auth_headers).json()
    second = client.get("/recommendations", headers=auth_headers).json()

    first_item = next(item for item in first if item["recommendation_type"] == "strengthen_high_value_contact")
    second_item = next(item for item in second if item["recommendation_type"] == "strengthen_high_value_contact")
    assert first_item["recommendation_id"]
    assert first_item["recommendation_id"] == second_item["recommendation_id"]
    assert first_item["id"] == first_item["recommendation_id"]


def test_recommendations_using_user_goals_and_interests(client, auth_headers):
    client.put(
        "/profile",
        json={"goals": ["healthcare"], "interests": ["community"]},
        headers=auth_headers,
    )
    contact = client.post(
        "/contacts",
        json={
            "name": "Sara",
            "company": "MedAI",
            "role": "Founder",
            "notes": "Building healthcare AI tools",
            "relationship_strength": 4,
        },
        headers=auth_headers,
    ).json()

    response = client.get("/recommendations/next-best-actions", headers=auth_headers)
    assert response.status_code == 200
    assert any(
        item["recommendation_type"] == "strengthen_high_value_contact"
        and item["related_contact_id"] == contact["id"]
        for item in response.json()
    )


def test_recommendations_empty_state(client, auth_headers):
    response = client.get("/recommendations", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_recommendations_user_isolation(client):
    client.post("/auth/register", json={"username": "rec_a", "password": "passwordA123"})
    token_a = client.post(
        "/auth/login", json={"username": "rec_a", "password": "passwordA123"}
    ).json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}
    client.post(
        "/contacts",
        json={"name": "Private", "company": "Secret", "role": "CEO", "relationship_strength": 5},
        headers=headers_a,
    )

    client.post("/auth/register", json={"username": "rec_b", "password": "passwordB123"})
    token_b = client.post(
        "/auth/login", json={"username": "rec_b", "password": "passwordB123"}
    ).json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    response = client.get("/recommendations", headers=headers_b)
    assert response.status_code == 200
    assert response.json() == []


def test_recommendations_priority_ordering(client, auth_headers):
    contact = client.post(
        "/contacts",
        json={"name": "Ava", "company": "North", "role": "Founder", "relationship_strength": 5},
        headers=auth_headers,
    ).json()
    client.post(
        "/follow-ups",
        json={
            "contact_id": contact["id"],
            "title": "Urgent follow-up",
            "status": "pending",
            "due_date": (datetime.now(timezone.utc) - timedelta(days=5)).isoformat(),
        },
        headers=auth_headers,
    )

    response = client.get("/recommendations", headers=auth_headers)
    assert response.status_code == 200
    scores = [item["priority_score"] for item in response.json()]
    assert scores == sorted(scores, reverse=True)


def test_helpful_feedback_boosts_similar_recommendation_type(client, auth_headers):
    contact = client.post(
        "/contacts",
        json={"name": "Mina", "company": "Orbit", "role": "Founder", "relationship_strength": 5},
        headers=auth_headers,
    ).json()
    recommendation = next(
        item
        for item in client.get("/recommendations", headers=auth_headers).json()
        if item["recommendation_type"] == "strengthen_high_value_contact"
        and item["related_contact_id"] == contact["id"]
    )

    client.post(
        "/feedback",
        json={
            "suggestion": "Strengthen this relationship",
            "category": "helpful",
            "target_type": "recommendation",
            "target_id": recommendation["recommendation_id"],
        },
        headers=auth_headers,
    )

    response = client.get("/recommendations", headers=auth_headers)
    item = next(
        entry
        for entry in response.json()
        if entry["recommendation_type"] == "strengthen_high_value_contact"
        and entry["related_contact_id"] == contact["id"]
    )
    assert "Prior feedback signaled" in item["reason"]
    assert item["priority_score"] >= 88


def test_dismissed_feedback_reduces_similar_recommendation_type(client, auth_headers):
    contact = client.post(
        "/contacts",
        json={"name": "Ravi", "company": "North", "role": "Investor", "relationship_strength": 5},
        headers=auth_headers,
    ).json()
    base_response = client.get("/recommendations", headers=auth_headers)
    base_item = next(
        entry
        for entry in base_response.json()
        if entry["recommendation_type"] == "strengthen_high_value_contact"
        and entry["related_contact_id"] == contact["id"]
    )

    client.post(
        "/feedback",
        json={
            "suggestion": "Not useful now",
            "category": "dismissed",
            "target_type": "recommendation",
            "target_id": base_item["recommendation_id"],
        },
        headers=auth_headers,
    )

    tuned_response = client.get("/recommendations", headers=auth_headers)
    tuned_item = next(
        entry
        for entry in tuned_response.json()
        if entry["recommendation_type"] == "strengthen_high_value_contact"
        and entry["related_contact_id"] == contact["id"]
    )
    assert tuned_item["priority_score"] < base_item["priority_score"]


def test_irrelevant_feedback_reduces_similar_recommendation_type(client, auth_headers):
    contact = client.post(
        "/contacts",
        json={"name": "Ari", "company": "East", "role": "Founder", "relationship_strength": 4},
        headers=auth_headers,
    ).json()
    recommendation = next(
        item
        for item in client.get("/recommendations", headers=auth_headers).json()
        if item["recommendation_type"] == "strengthen_high_value_contact"
        and item["related_contact_id"] == contact["id"]
    )
    client.post(
        "/feedback",
        json={
            "suggestion": "Not relevant",
            "category": "irrelevant",
            "target_type": "recommendation",
            "target_id": recommendation["recommendation_id"],
        },
        headers=auth_headers,
    )

    response = client.get("/recommendations", headers=auth_headers)
    item = next(
        entry
        for entry in response.json()
        if entry["recommendation_type"] == "strengthen_high_value_contact"
        and entry["related_contact_id"] == contact["id"]
    )
    assert "Prior feedback reduced" in item["reason"]


def test_feedback_effect_is_bounded(client, auth_headers):
    contact = client.post(
        "/contacts",
        json={"name": "Bounded", "company": "Axis", "role": "Founder", "relationship_strength": 5},
        headers=auth_headers,
    ).json()
    recommendation = next(
        item
        for item in client.get("/recommendations", headers=auth_headers).json()
        if item["recommendation_type"] == "strengthen_high_value_contact"
        and item["related_contact_id"] == contact["id"]
    )
    for _ in range(10):
        client.post(
            "/feedback",
            json={
                "suggestion": "Strong yes",
                "category": "accepted",
                "target_type": "recommendation",
                "target_id": recommendation["recommendation_id"],
            },
            headers=auth_headers,
        )

    response = client.get("/recommendations", headers=auth_headers)
    item = next(
        entry
        for entry in response.json()
        if entry["recommendation_type"] == "strengthen_high_value_contact"
        and entry["related_contact_id"] == contact["id"]
    )
    assert item["priority_score"] <= 93


def test_wrong_tone_does_not_strongly_reduce_recommendation_relevance(client, auth_headers):
    contact = client.post(
        "/contacts",
        json={"name": "Tone", "company": "Wave", "role": "Founder", "relationship_strength": 5},
        headers=auth_headers,
    ).json()
    base_response = client.get("/recommendations", headers=auth_headers)
    base_item = next(
        entry
        for entry in base_response.json()
        if entry["recommendation_type"] == "strengthen_high_value_contact"
        and entry["related_contact_id"] == contact["id"]
    )

    client.post(
        "/feedback",
        json={
            "suggestion": "Tone issue",
            "category": "wrong_tone",
            "target_type": "recommendation",
            "target_id": base_item["recommendation_id"],
        },
        headers=auth_headers,
    )

    tuned_response = client.get("/recommendations", headers=auth_headers)
    tuned_item = next(
        entry
        for entry in tuned_response.json()
        if entry["recommendation_type"] == "strengthen_high_value_contact"
        and entry["related_contact_id"] == contact["id"]
    )
    assert tuned_item["priority_score"] == base_item["priority_score"]


def test_feedback_tuning_is_user_isolated(client):
    client.post("/auth/register", json={"username": "fb_rec_a", "password": "passwordA123"})
    token_a = client.post(
        "/auth/login", json={"username": "fb_rec_a", "password": "passwordA123"}
    ).json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}
    client.post(
        "/feedback",
        json={
            "suggestion": "Private feedback",
            "category": "dismissed",
            "target_type": "recommendation",
            "target_id": "strengthen_high_value_contact",
        },
        headers=headers_a,
    )

    client.post("/auth/register", json={"username": "fb_rec_b", "password": "passwordB123"})
    token_b = client.post(
        "/auth/login", json={"username": "fb_rec_b", "password": "passwordB123"}
    ).json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}
    contact_b = client.post(
        "/contacts",
        json={"name": "Shared", "company": "Clear", "role": "Founder", "relationship_strength": 5},
        headers=headers_b,
    ).json()

    response = client.get("/recommendations", headers=headers_b)
    item = next(
        entry
        for entry in response.json()
        if entry["recommendation_type"] == "strengthen_high_value_contact"
        and entry["related_contact_id"] == contact_b["id"]
    )
    assert "Prior feedback" not in item["reason"]


def test_recommendation_feedback_backward_compatibility_with_type_id(client, auth_headers):
    contact = client.post(
        "/contacts",
        json={"name": "Legacy", "company": "Clear", "role": "Founder", "relationship_strength": 5},
        headers=auth_headers,
    ).json()
    client.post(
        "/feedback",
        json={
            "suggestion": "Legacy feedback",
            "category": "helpful",
            "target_type": "recommendation",
            "target_id": "strengthen_high_value_contact",
        },
        headers=auth_headers,
    )

    response = client.get("/recommendations", headers=auth_headers)
    item = next(
        entry
        for entry in response.json()
        if entry["recommendation_type"] == "strengthen_high_value_contact"
        and entry["related_contact_id"] == contact["id"]
    )
    assert "Prior feedback signaled" in item["reason"]


def test_recommendation_impressions_are_logged(client, auth_headers):
    client.post(
        "/contacts",
        json={"name": "Log Me", "company": "Orbit", "role": "Founder", "relationship_strength": 5},
        headers=auth_headers,
    )

    response = client.get("/recommendations", headers=auth_headers)
    assert response.status_code == 200

    training_data = client.get("/recommendations/training-data", headers=auth_headers)
    assert training_data.status_code == 200
    rows = training_data.json()
    assert rows
    assert any(row["recommendation_type"] == "strengthen_high_value_contact" for row in rows)


def test_training_data_generated_from_impressions_and_feedback(client, auth_headers):
    client.post(
        "/contacts",
        json={"name": "Train", "company": "North", "role": "Founder", "relationship_strength": 5},
        headers=auth_headers,
    )
    recommendations = client.get("/recommendations", headers=auth_headers).json()
    recommendation = next(
        item for item in recommendations if item["recommendation_type"] == "strengthen_high_value_contact"
    )
    client.post(
        "/feedback",
        json={
            "suggestion": "Good recommendation",
            "category": "accepted",
            "target_type": "recommendation",
            "target_id": recommendation["recommendation_id"],
        },
        headers=auth_headers,
    )

    response = client.get("/recommendations/training-data", headers=auth_headers)
    assert response.status_code == 200
    row = next(
        entry
        for entry in response.json()
        if entry["recommendation_type"] == "strengthen_high_value_contact"
    )
    assert row["recommendation_id"] == recommendation["recommendation_id"]
    assert row["label"] == 1
    assert row["feedback_category"] == "accepted"
    assert row["has_contact"] is True


def test_recommendation_training_data_empty_state(client, auth_headers):
    response = client.get("/recommendations/training-data", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_recommendation_training_data_user_isolation(client):
    client.post("/auth/register", json={"username": "train_a", "password": "passwordA123"})
    token_a = client.post(
        "/auth/login", json={"username": "train_a", "password": "passwordA123"}
    ).json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}
    client.post(
        "/contacts",
        json={"name": "Private", "company": "Scope", "role": "Founder", "relationship_strength": 5},
        headers=headers_a,
    )
    client.get("/recommendations", headers=headers_a)

    client.post("/auth/register", json={"username": "train_b", "password": "passwordB123"})
    token_b = client.post(
        "/auth/login", json={"username": "train_b", "password": "passwordB123"}
    ).json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    response = client.get("/recommendations/training-data", headers=headers_b)
    assert response.status_code == 200
    assert response.json() == []
