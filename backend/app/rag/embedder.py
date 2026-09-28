from abc import ABC, abstractmethod
from typing import List, Optional
import os
from app.core.config import settings

class EmbeddingProvider(ABC):
    @abstractmethod
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        pass

    @abstractmethod
    def embed_query(self, query: str) -> List[float]:
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        pass


class SentenceTransformersEmbeddingProvider(EmbeddingProvider):
    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5"):
        self.model_name = model_name
        self._model = None
        self._dimension = 384  # default for bge-small

    @property
    def model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
            self._dimension = self._model.get_sentence_embedding_dimension()
        return self._model

    @property
    def dimension(self) -> int:
        if self._model is None:
            # Infer dimension from well-known model names before loading
            if "bge-small" in self.model_name.lower():
                return 384
            elif "bge-large" in self.model_name.lower():
                return 1024
            elif "bge-base" in self.model_name.lower():
                return 768
            # Trigger load to get precise dimension
            return self.model.get_sentence_embedding_dimension()
        return self._dimension

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        embeddings = self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return embeddings.tolist()

    def embed_query(self, query: str) -> List[float]:
        if not query or not query.strip():
            return [0.0] * self.dimension
        embedding = self.model.encode(query, normalize_embeddings=True, show_progress_bar=False)
        return embedding.tolist()


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self, model_name: str = "text-embedding-3-small", api_key: Optional[str] = None):
        self.model_name = model_name or "text-embedding-3-small"
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._client = None
        self._dim = 1536

    @property
    def client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=self.api_key)
        return self._client

    @property
    def dimension(self) -> int:
        return self._dim

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        response = self.client.embeddings.create(
            input=texts,
            model=self.model_name
        )
        return [item.embedding for item in response.data]

    def embed_query(self, query: str) -> List[float]:
        if not query or not query.strip():
            return [0.0] * self.dimension
        response = self.client.embeddings.create(
            input=[query],
            model=self.model_name
        )
        return response.data[0].embedding


def get_embedding_provider() -> EmbeddingProvider:
    provider = settings.EMBEDDING_PROVIDER.lower()
    if provider == "openai":
        return OpenAIEmbeddingProvider(
            model_name=settings.EMBEDDING_MODEL or "text-embedding-3-small",
            api_key=settings.OPENAI_API_KEY
        )
    # Default to SentenceTransformers
    return SentenceTransformersEmbeddingProvider(
        model_name=settings.EMBEDDING_MODEL or "BAAI/bge-small-en-v1.5"
    )

embedder = get_embedding_provider()
