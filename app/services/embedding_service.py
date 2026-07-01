import hashlib
import math
from typing import List, Protocol


class EmbeddingService(Protocol):
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        ...


class HashEmbeddingService:
    def __init__(self, dimension: int = 64):
        self.dimension = dimension

    def _embed_text(self, text: str) -> List[float]:
        vector = [0.0] * self.dimension
        tokens = text.lower().split() or [text.lower()]

        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            bucket = int.from_bytes(digest[:4], "big") % self.dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[bucket] += sign

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector

        return [value / norm for value in vector]

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        return [self._embed_text(text) for text in texts]


class SentenceTransformerEmbeddingService:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(model_name, local_files_only=True)

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        vectors = self.model.encode(texts, normalize_embeddings=True)
        return [list(vector) for vector in vectors]


def build_embedding_service() -> EmbeddingService:
    try:
        return SentenceTransformerEmbeddingService()
    except Exception:
        return HashEmbeddingService()


_embedding_service: EmbeddingService | None = None


def get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = build_embedding_service()
    return _embedding_service
