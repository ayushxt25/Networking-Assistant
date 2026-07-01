from app.db_models import Contact, User
from app.services.embedding_service import HashEmbeddingService, build_embedding_service
from app.services.memory_documents import build_memory_documents
from app.services.semantic_memory_service import semantic_search_memories
from app.services.vector_store import InMemoryVectorStore


def test_memory_document_creation(db_session):
    user = User(username="memory_user", hashed_password="hashed")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    db_session.add(
        Contact(
            user_id=user.id,
            name="Asha",
            company="Northwind",
            role="Designer",
            notes="Interested in brand systems",
        )
    )
    db_session.commit()

    documents = build_memory_documents(db_session, user.id)
    assert len(documents) == 1
    assert documents[0].entity_type == "contact"
    assert "Asha" in documents[0].text


def test_embedding_service_fallback(monkeypatch):
    monkeypatch.setattr(
        "app.services.embedding_service.SentenceTransformerEmbeddingService",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("no model")),
    )
    service = build_embedding_service()
    assert isinstance(service, HashEmbeddingService)
    vectors = service.embed_texts(["hello world"])
    assert len(vectors) == 1
    assert len(vectors[0]) == 64


def test_vector_upsert_and_search():
    store = InMemoryVectorStore()
    embedding_service = HashEmbeddingService()

    class Doc:
        def __init__(self, doc_id, user_id, text):
            self.id = doc_id
            self.user_id = user_id
            self.text = text
            self.metadata = {"user_id": user_id}

    documents = [Doc("contact:1", 1, "AI founder in climate tech")]
    embeddings = embedding_service.embed_texts([documents[0].text])
    store.upsert(documents, embeddings)

    query_embedding = embedding_service.embed_texts(["climate founder"])[0]
    results = store.search(query_embedding, user_id=1, top_k=1)
    assert len(results) == 1
    assert results[0].id == "contact:1"


def test_user_isolation_in_semantic_search(db_session):
    user_a = User(username="semantic_a", hashed_password="hashed")
    user_b = User(username="semantic_b", hashed_password="hashed")
    db_session.add_all([user_a, user_b])
    db_session.commit()
    db_session.refresh(user_a)
    db_session.refresh(user_b)

    db_session.add_all(
        [
            Contact(
                user_id=user_a.id,
                name="Alice",
                company="AI Labs",
                role="Founder",
                notes="Machine learning healthcare",
            ),
            Contact(
                user_id=user_b.id,
                name="Bob",
                company="Retail Co",
                role="Manager",
                notes="Supply chain operations",
            ),
        ]
    )
    db_session.commit()

    results = semantic_search_memories(
        db=db_session,
        query_text="healthcare machine learning",
        user_id=user_a.id,
        top_k=3,
    )
    assert results
    assert all(result.metadata["user_id"] == user_a.id for result in results)
    assert any("Alice" in result.text for result in results)
