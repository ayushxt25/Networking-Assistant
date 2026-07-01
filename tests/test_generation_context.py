from app.routes import conversation as conversation_routes
from app.services.context_service import assemble_generation_context


def test_generation_with_empty_context(db_session):
    context = assemble_generation_context(
        db=db_session,
        user_id=999,
        description="AI summit",
        interests=["climate"],
        themes=["artificial intelligence"],
    )
    assert context.combined_summary is None


def test_generation_with_contacts(client, auth_headers, monkeypatch):
    client.post(
        "/contacts",
        json={
            "name": "Mira",
            "company": "Signal Labs",
            "role": "Product Lead",
            "notes": "Interested in AI operations",
        },
        headers=auth_headers,
    )

    captured = {}

    def fake_generate_topics(themes, interests, relationship_context=None):
        captured["relationship_context"] = relationship_context
        return ["starter"]

    monkeypatch.setattr(conversation_routes, "generate_topics", fake_generate_topics)

    response = client.post(
        "/generate-conversation",
        json={"description": "AI operations meetup", "interests": ["product"]},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert "Mira" in captured["relationship_context"]
    assert "Signal Labs" in captured["relationship_context"]


def test_generation_with_interactions(client, auth_headers, monkeypatch):
    contact = client.post(
        "/contacts",
        json={"name": "Rohan", "company": "Northstar", "role": "Founder"},
        headers=auth_headers,
    ).json()

    client.post(
        "/interactions",
        json={
            "contact_id": contact["id"],
            "interaction_type": "coffee_chat",
            "notes": "Discussed partnership ideas for fintech AI",
            "sentiment": "positive",
        },
        headers=auth_headers,
    )

    captured = {}

    def fake_generate_topics(themes, interests, relationship_context=None):
        captured["relationship_context"] = relationship_context
        return ["starter"]

    monkeypatch.setattr(conversation_routes, "generate_topics", fake_generate_topics)

    response = client.post(
        "/generate-conversation",
        json={"description": "Fintech AI roundtable", "interests": ["partnerships"]},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert "coffee_chat" in captured["relationship_context"]
    assert "partnership" in captured["relationship_context"].lower()


def test_generation_with_profile_data(client, auth_headers, monkeypatch):
    client.put(
        "/profile",
        json={
            "full_name": "Ayush",
            "headline": "Relationship builder",
            "interests": ["ai", "communities"],
            "preferred_tone": "warm",
        },
        headers=auth_headers,
    )

    captured = {}

    def fake_generate_topics(themes, interests, relationship_context=None):
        captured["relationship_context"] = relationship_context
        return ["starter"]

    monkeypatch.setattr(conversation_routes, "generate_topics", fake_generate_topics)

    response = client.post(
        "/generate-conversation",
        json={"description": "Community AI event", "interests": ["communities"]},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert "Ayush" in captured["relationship_context"]
    assert "preferred tone=warm" in captured["relationship_context"]
