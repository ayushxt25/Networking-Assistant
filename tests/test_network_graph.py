from datetime import datetime


def test_network_graph_empty_state(client, auth_headers):
    response = client.get("/network/graph-insights", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total_contacts"] == 0
    assert body["network_density_estimate"] == 0.0
    assert body["centrality_scores"] == []
    assert body["clusters"] == []


def test_network_graph_centrality_and_strong_weak_ties(client, auth_headers):
    alpha = client.post(
        "/contacts",
        json={"name": "Alpha", "company": "Orbit", "role": "Founder", "tags": ["ai"], "relationship_strength": 5},
        headers=auth_headers,
    ).json()
    beta = client.post(
        "/contacts",
        json={"name": "Beta", "company": "Orbit", "role": "Founder", "tags": ["ai"], "relationship_strength": 2},
        headers=auth_headers,
    ).json()
    client.post(
        "/interactions",
        json={"contact_id": alpha["id"], "interaction_type": "coffee", "notes": "Strong discussion"},
        headers=auth_headers,
    )
    client.post(
        "/interactions",
        json={"contact_id": alpha["id"], "interaction_type": "email", "notes": "Follow up"},
        headers=auth_headers,
    )

    response = client.get("/network/graph-insights", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["centrality_scores"][0]["name"] == "Alpha"
    assert any(item["name"] == "Alpha" for item in body["strong_tie_contacts"])
    assert any(item["name"] == "Beta" for item in body["weak_tie_candidates"])


def test_network_graph_bridge_cluster_and_isolated_contacts(client, auth_headers):
    summit = client.post(
        "/events",
        json={"title": "AI Summit", "event_date": datetime(2026, 7, 20, 9, 0, 0).isoformat()},
        headers=auth_headers,
    ).json()
    bridge = client.post(
        "/contacts",
        json={"name": "Bridge", "company": "Orbit", "role": "Founder", "tags": ["ai", "fintech"], "relationship_strength": 4},
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
    isolated = client.post(
        "/contacts",
        json={"name": "Isolated", "company": "Solo", "role": "Advisor", "tags": ["health"], "relationship_strength": 1},
        headers=auth_headers,
    ).json()

    client.post(
        "/interactions",
        json={"contact_id": bridge["id"], "event_id": summit["id"], "interaction_type": "panel", "notes": "Met at summit"},
        headers=auth_headers,
    )
    client.post(
        "/interactions",
        json={"contact_id": left["id"], "event_id": summit["id"], "interaction_type": "coffee", "notes": "Met at summit"},
        headers=auth_headers,
    )

    response = client.get("/network/graph-insights", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert any(item["name"] == "Bridge" for item in body["bridge_contacts"])
    assert any(item["name"] == "Isolated" and item["contact_id"] == isolated["id"] for item in body["isolated_contacts"])
    assert body["clusters"]
    cluster_names = body["clusters"][0]["contact_names"]
    assert "Bridge" in cluster_names
    assert "Left" in cluster_names


def test_network_graph_user_isolation(client):
    client.post("/auth/register", json={"username": "graph_a", "password": "passwordA123"})
    token_a = client.post(
        "/auth/login", json={"username": "graph_a", "password": "passwordA123"}
    ).json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}
    client.post(
        "/contacts",
        json={"name": "Private Graph", "company": "Hidden", "role": "CEO", "relationship_strength": 5},
        headers=headers_a,
    )

    client.post("/auth/register", json={"username": "graph_b", "password": "passwordB123"})
    token_b = client.post(
        "/auth/login", json={"username": "graph_b", "password": "passwordB123"}
    ).json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    response = client.get("/network/graph-insights", headers=headers_b)
    assert response.status_code == 200
    assert response.json()["total_contacts"] == 0
