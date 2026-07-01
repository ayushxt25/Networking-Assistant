from typing import List

from sqlalchemy.orm import Session

from app.services.embedding_service import get_embedding_service
from app.services.memory_documents import MemoryDocument, build_memory_documents
from app.services.vector_store import VectorSearchResult, get_vector_store


def sync_user_memories(db: Session, user_id: int) -> List[MemoryDocument]:
    documents = build_memory_documents(db, user_id)
    if not documents:
        return []

    embedding_service = get_embedding_service()
    vector_store = get_vector_store()
    embeddings = embedding_service.embed_texts([document.text for document in documents])
    vector_store.upsert(documents, embeddings)
    return documents


def semantic_search_memories(
    db: Session,
    query_text: str,
    user_id: int,
    top_k: int = 3,
) -> List[VectorSearchResult]:
    try:
        documents = sync_user_memories(db, user_id)
        if not documents:
            return []

        embedding_service = get_embedding_service()
        vector_store = get_vector_store()
        query_embedding = embedding_service.embed_texts([query_text])[0]
        return vector_store.search(query_embedding, user_id=user_id, top_k=top_k)
    except Exception:
        return []
