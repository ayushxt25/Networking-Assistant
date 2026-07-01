from app.routes import conversation as conversation_routes
from app.services import context_service
from app.services.context_service import assemble_generation_context
from app.services.vector_store import VectorSearchResult


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


def test_generation_with_semantic_memory_available(client, auth_headers, monkeypatch):
    client.post(
        "/contacts",
        json={
            "name": "Leena",
            "company": "Graph Works",
            "role": "Founder",
            "notes": "Met at AI infrastructure dinner",
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
        json={"description": "AI infrastructure dinner", "interests": ["founders"]},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert "Semantic memory:" in captured["relationship_context"]
    assert "Leena" in captured["relationship_context"]


def test_generation_with_no_semantic_memory(client, auth_headers, monkeypatch):
    captured = {}

    def fake_generate_topics(themes, interests, relationship_context=None):
        captured["relationship_context"] = relationship_context
        return ["starter"]

    monkeypatch.setattr(conversation_routes, "generate_topics", fake_generate_topics)
    monkeypatch.setattr(context_service, "semantic_search_memories", lambda **kwargs: [])

    response = client.post(
        "/generate-conversation",
        json={"description": "General meetup", "interests": ["people"]},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert "Semantic memory:" not in (captured["relationship_context"] or "")


def test_generation_vector_failure_fallback(client, auth_headers, monkeypatch):
    captured = {}

    def fake_generate_topics(themes, interests, relationship_context=None):
        captured["relationship_context"] = relationship_context
        return ["starter"]

    monkeypatch.setattr(conversation_routes, "generate_topics", fake_generate_topics)
    monkeypatch.setattr(
        context_service,
        "semantic_search_memories",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("vector unavailable")),
    )

    response = client.post(
        "/generate-conversation",
        json={"description": "Developer event", "interests": ["python"]},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert captured["relationship_context"] is None or "Semantic memory:" not in captured["relationship_context"]


def test_generation_still_works_with_reranked_memory(client, auth_headers, monkeypatch):
    captured = {}

    def fake_generate_topics(themes, interests, relationship_context=None):
        captured["relationship_context"] = relationship_context
        return ["starter"]

    monkeypatch.setattr(conversation_routes, "generate_topics", fake_generate_topics)
    monkeypatch.setattr(
        context_service,
        "semantic_search_memories",
        lambda **kwargs: [
            VectorSearchResult(
                id="generic",
                text="General founder note",
                metadata={"user_id": kwargs["user_id"]},
                score=0.95,
            ),
            VectorSearchResult(
                id="specific",
                text="Healthcare AI founder interested in partnerships",
                metadata={"user_id": kwargs["user_id"]},
                score=0.75,
            ),
        ],
    )

    response = client.post(
        "/generate-conversation",
        json={"description": "Healthcare AI founder dinner", "interests": ["partnerships"]},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert "Semantic memory:" in captured["relationship_context"]
    assert "Healthcare AI founder" in captured["relationship_context"]


def test_generation_reranker_failure_falls_back_to_raw_results(client, auth_headers, monkeypatch):
    captured = {}

    def fake_generate_topics(themes, interests, relationship_context=None):
        captured["relationship_context"] = relationship_context
        return ["starter"]

    monkeypatch.setattr(conversation_routes, "generate_topics", fake_generate_topics)
    monkeypatch.setattr(
        context_service,
        "semantic_search_memories",
        lambda **kwargs: [
            VectorSearchResult(
                id="raw",
                text="Raw semantic memory snippet",
                metadata={"user_id": kwargs["user_id"]},
                score=0.8,
            )
        ],
    )
    monkeypatch.setattr(
        context_service,
        "rerank_memory_results",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("rerank failed")),
    )

    response = client.post(
        "/generate-conversation",
        json={"description": "Founder meetup", "interests": ["ai"]},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert "Raw semantic memory snippet" in captured["relationship_context"]


def test_generation_semantic_memory_user_isolation(client, monkeypatch):
    client.post("/auth/register", json={"username": "memory_a", "password": "passwordA123"})
    token_a = client.post(
        "/auth/login", json={"username": "memory_a", "password": "passwordA123"}
    ).json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    client.post(
        "/contacts",
        json={
            "name": "Private Contact",
            "company": "Hidden AI",
            "role": "Founder",
            "notes": "Confidential healthcare context",
        },
        headers=headers_a,
    )

    client.post("/auth/register", json={"username": "memory_b", "password": "passwordB123"})
    token_b = client.post(
        "/auth/login", json={"username": "memory_b", "password": "passwordB123"}
    ).json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    captured = {}

    def fake_generate_topics(themes, interests, relationship_context=None):
        captured["relationship_context"] = relationship_context
        return ["starter"]

    monkeypatch.setattr(conversation_routes, "generate_topics", fake_generate_topics)

    response = client.post(
        "/generate-conversation",
        json={"description": "Healthcare founder dinner", "interests": ["ai"]},
        headers=headers_b,
    )

    assert response.status_code == 200
    assert "Private Contact" not in (captured["relationship_context"] or "")
