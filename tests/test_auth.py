"""
Tests for app.routes.auth -- registration and login endpoints.
"""

from app.config import (
    get_supabase_audience,
    get_supabase_auth_enabled,
    get_supabase_dual_auth_enabled,
    get_supabase_jwt_secret,
    get_supabase_url,
)
from app.db_models import User
from app.dependencies import get_current_user
from app.roles import coerce_user_role, normalize_user_role
from app.supabase_auth import SupabaseJWTClaims


def test_register_new_user_succeeds(client):
    response = client.post(
        "/auth/register", json={"username": "alice", "password": "supersecret123"}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["username"] == "alice"
    assert "id" in body
    assert "password" not in body  # never echo the password back


def test_register_duplicate_username_fails(client):
    client.post("/auth/register", json={"username": "bob", "password": "supersecret123"})
    response = client.post(
        "/auth/register", json={"username": "bob", "password": "anotherpassword456"}
    )
    assert response.status_code == 409


def test_register_short_password_fails_validation(client):
    response = client.post("/auth/register", json={"username": "carol", "password": "short"})
    assert response.status_code == 422


def test_login_with_correct_credentials_returns_token(client):
    client.post("/auth/register", json={"username": "dave", "password": "supersecret123"})
    response = client.post(
        "/auth/login", json={"username": "dave", "password": "supersecret123"}
    )
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


def test_login_with_wrong_password_fails(client):
    client.post("/auth/register", json={"username": "erin", "password": "supersecret123"})
    response = client.post("/auth/login", json={"username": "erin", "password": "wrongpassword"})
    assert response.status_code == 401


def test_login_with_nonexistent_user_fails(client):
    response = client.post(
        "/auth/login", json={"username": "doesnotexist", "password": "whatever123"}
    )
    assert response.status_code == 401


def test_login_error_message_does_not_distinguish_user_existence(client):
    """Both 'wrong password' and 'user doesn't exist' should return the same
    generic error, so the API doesn't leak which usernames are registered."""
    client.post("/auth/register", json={"username": "frank", "password": "supersecret123"})

    wrong_password_response = client.post(
        "/auth/login", json={"username": "frank", "password": "wrongpassword"}
    )
    nonexistent_user_response = client.post(
        "/auth/login", json={"username": "ghost", "password": "whatever123"}
    )

    assert wrong_password_response.json()["detail"] == nonexistent_user_response.json()["detail"]


def test_custom_auth_still_works_when_supabase_disabled(client, auth_headers, monkeypatch):
    monkeypatch.setattr("app.dependencies.get_supabase_auth_enabled", lambda: False)
    response = client.get("/history", headers=auth_headers)
    assert response.status_code == 200


def test_supabase_config_defaults_are_safe(monkeypatch):
    for key in (
        "SUPABASE_URL",
        "SUPABASE_JWT_SECRET",
        "SUPABASE_AUDIENCE",
        "SUPABASE_AUTH_ENABLED",
        "SUPABASE_DUAL_AUTH_ENABLED",
    ):
        monkeypatch.delenv(key, raising=False)

    assert get_supabase_url() is None
    assert get_supabase_jwt_secret() is None
    assert get_supabase_audience() == "authenticated"
    assert get_supabase_auth_enabled() is False
    assert get_supabase_dual_auth_enabled() is True


def test_supabase_user_resolution_can_create_local_user_from_verified_claims(db_session, monkeypatch):
    monkeypatch.setattr("app.dependencies.get_supabase_auth_enabled", lambda: True)
    monkeypatch.setattr("app.dependencies.get_supabase_dual_auth_enabled", lambda: True)
    monkeypatch.setattr(
        "app.dependencies.verify_supabase_jwt",
        lambda token: SupabaseJWTClaims(
            supabase_user_id="supabase-user-123",
            email="sam@example.com",
            role="admin",
            raw_claims={"sub": "supabase-user-123"},
        ),
    )

    user = get_current_user(token="supabase-token", db=db_session)

    assert user.supabase_user_id == "supabase-user-123"
    assert user.username == "sam"
    assert user.role == "admin"
    assert user.hashed_password


def test_supabase_user_resolution_reuses_existing_local_user(db_session, monkeypatch):
    existing = User(
        username="existing-user",
        hashed_password="not-used",
        supabase_user_id="supabase-user-456",
        role="admin",
    )
    db_session.add(existing)
    db_session.commit()
    db_session.refresh(existing)

    monkeypatch.setattr("app.dependencies.get_supabase_auth_enabled", lambda: True)
    monkeypatch.setattr("app.dependencies.get_supabase_dual_auth_enabled", lambda: True)
    monkeypatch.setattr(
        "app.dependencies.verify_supabase_jwt",
        lambda token: SupabaseJWTClaims(
            supabase_user_id="supabase-user-456",
            email="other@example.com",
            role="user",
            raw_claims={"sub": "supabase-user-456"},
        ),
    )

    user = get_current_user(token="supabase-token", db=db_session)

    assert user.id == existing.id
    assert db_session.query(User).filter(User.supabase_user_id == "supabase-user-456").count() == 1


def test_role_normalization_and_invalid_role_fallback():
    assert normalize_user_role("ADMIN") == "admin"
    assert coerce_user_role("superadmin") == "user"
