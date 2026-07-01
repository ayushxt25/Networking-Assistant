from datetime import datetime, timedelta, timezone

from app.db_models import Contact, User
from app.services.embedding_service import HashEmbeddingService, build_embedding_service
from app.services.memory_documents import build_memory_documents
from app.services.retrieval_quality_service import rerank_memory_results
from app.services.semantic_memory_service import semantic_search_memories
from app.services.vector_store import InMemoryVectorStore, VectorSearchResult


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


def test_reranking_improves_ordering_based_on_keyword_overlap():
    results = [
        VectorSearchResult(
            id="a",
            text="General founder networking note",
            metadata={"user_id": 1},
            score=0.95,
        ),
        VectorSearchResult(
            id="b",
            text="Healthcare AI founder with machine learning background",
            metadata={"user_id": 1},
            score=0.80,
        ),
    ]
    reranked = rerank_memory_results(
        results=results,
        user_id=1,
        query_text="healthcare machine learning founder",
        interests=["healthcare"],
        themes=["machine learning"],
        top_k=2,
    )
    assert reranked[0].result.id == "b"


def test_duplicate_snippets_are_removed():
    results = [
        VectorSearchResult(id="a", text="AI healthcare founder", metadata={"user_id": 1}, score=0.9),
        VectorSearchResult(id="b", text="AI healthcare founder", metadata={"user_id": 1}, score=0.8),
    ]
    reranked = rerank_memory_results(results=results, user_id=1, query_text="healthcare founder", top_k=3)
    assert len(reranked) == 1


def test_very_short_snippets_are_penalized():
    results = [
        VectorSearchResult(id="a", text="AI", metadata={"user_id": 1}, score=0.9),
        VectorSearchResult(
            id="b",
            text="AI founder focused on healthcare partnerships",
            metadata={"user_id": 1},
            score=0.75,
        ),
    ]
    reranked = rerank_memory_results(results=results, user_id=1, query_text="healthcare partnerships", top_k=2)
    assert reranked[0].result.id == "b"


def test_fresher_memory_is_preferred_when_relevant():
    older = (datetime.now(timezone.utc) - timedelta(days=20)).isoformat()
    newer = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    results = [
        VectorSearchResult(
            id="old",
            text="AI founder for healthcare partnerships",
            metadata={"user_id": 1, "updated_at": older},
            score=0.8,
        ),
        VectorSearchResult(
            id="new",
            text="AI founder for healthcare partnerships",
            metadata={"user_id": 1, "updated_at": newer},
            score=0.8,
        ),
    ]
    reranked = rerank_memory_results(results=results, user_id=1, query_text="healthcare partnerships", top_k=2)
    assert reranked[0].result.id == "new"


def test_reranker_preserves_user_isolation():
    results = [
        VectorSearchResult(id="a", text="Private note", metadata={"user_id": 1}, score=0.9),
        VectorSearchResult(id="b", text="Other user note", metadata={"user_id": 2}, score=0.99),
    ]
    reranked = rerank_memory_results(results=results, user_id=1, query_text="note", top_k=3)
    assert len(reranked) == 1
    assert reranked[0].result.id == "a"
