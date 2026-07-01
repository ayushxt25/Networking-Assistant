import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Protocol

from app.services.memory_documents import MemoryDocument


@dataclass
class VectorSearchResult:
    id: str
    text: str
    metadata: Dict[str, Any]
    score: float


class VectorStore(Protocol):
    def upsert(self, documents: List[MemoryDocument], embeddings: List[List[float]]) -> None:
        ...

    def search(self, query_embedding: List[float], user_id: int, top_k: int) -> List[VectorSearchResult]:
        ...


class InMemoryVectorStore:
    def __init__(self):
        self._records: Dict[str, tuple[MemoryDocument, List[float]]] = {}

    def upsert(self, documents: List[MemoryDocument], embeddings: List[List[float]]) -> None:
        for document, embedding in zip(documents, embeddings):
            self._records[document.id] = (document, embedding)

    def search(self, query_embedding: List[float], user_id: int, top_k: int) -> List[VectorSearchResult]:
        matches: List[VectorSearchResult] = []

        for document, embedding in self._records.values():
            if document.user_id != user_id:
                continue

            score = _cosine_similarity(query_embedding, embedding)
            matches.append(
                VectorSearchResult(
                    id=document.id,
                    text=document.text,
                    metadata=document.metadata,
                    score=score,
                )
            )

        matches.sort(key=lambda match: match.score, reverse=True)
        return matches[:top_k]


class ChromaVectorStore:
    def __init__(self, persist_path: Path):
        import chromadb

        self.client = chromadb.PersistentClient(path=str(persist_path))
        self.collection = self.client.get_or_create_collection("relationship_memory")

    def upsert(self, documents: List[MemoryDocument], embeddings: List[List[float]]) -> None:
        if not documents:
            return

        self.collection.upsert(
            ids=[document.id for document in documents],
            documents=[document.text for document in documents],
            metadatas=[document.metadata for document in documents],
            embeddings=embeddings,
        )

    def search(self, query_embedding: List[float], user_id: int, top_k: int) -> List[VectorSearchResult]:
        result = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where={"user_id": user_id},
        )

        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        ids = result.get("ids", [[]])[0]
        distances = result.get("distances", [[]])[0]

        matches: List[VectorSearchResult] = []
        for match_id, text, metadata, distance in zip(ids, documents, metadatas, distances):
            matches.append(
                VectorSearchResult(
                    id=match_id,
                    text=text,
                    metadata=metadata,
                    score=1.0 - float(distance),
                )
            )
        return matches


def _cosine_similarity(left: List[float], right: List[float]) -> float:
    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))

    if left_norm == 0 or right_norm == 0:
        return 0.0

    return numerator / (left_norm * right_norm)


def build_vector_store() -> VectorStore:
    try:
        persist_path = Path(__file__).resolve().parent.parent.parent / "data" / "chroma"
        persist_path.mkdir(parents=True, exist_ok=True)
        return ChromaVectorStore(persist_path)
    except Exception:
        return InMemoryVectorStore()


_vector_store: VectorStore | None = None


def get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = build_vector_store()
    return _vector_store
