"""
Shared pytest fixtures.

- Ensures the project root is on sys.path so `import app.xxx` works
  regardless of which directory pytest is invoked from.
- Provides a `db_session` fixture backed by a fresh in-memory SQLite
  database per test, so tests never touch the real data/app.db file and
  don't leak state between tests.
- Provides a `client` fixture: a FastAPI TestClient with the app's
  get_db dependency overridden to use the in-memory test database.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture()
def test_engine():
    """A fresh in-memory SQLite engine for each test."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # keeps the same in-memory DB alive across connections
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db_session(test_engine):
    """A SQLAlchemy session bound to the per-test in-memory engine."""
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(test_engine):
    """
    A FastAPI TestClient with get_db overridden to use the per-test
    in-memory database, instead of the real SQLite file on disk.
    """
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    def override_get_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    try:
        app.state.limiter._storage.reset()
    except Exception:
        pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def auth_headers(client):
    """
    Registers a fresh test user, logs in, and returns Authorization
    headers carrying a valid bearer token for that user.
    """
    client.post("/auth/register", json={"username": "testuser", "password": "testpassword123"})
    response = client.post(
        "/auth/login", json={"username": "testuser", "password": "testpassword123"}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
