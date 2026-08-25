from pathlib import Path

from langchain_ollama import OllamaEmbeddings
from qdrant_client import QdrantClient

from app.config import settings


class Retriever:
    def __init__(self) -> None:
        Path(settings.qdrant_path).mkdir(parents=True, exist_ok=True)
        self.client = QdrantClient(path=settings.qdrant_path)
        self.embeddings = OllamaEmbeddings(
            model=settings.embedding_model,
            base_url=settings.ollama_base_url,
        )

    def ready(self) -> bool:
        return self.client.collection_exists(settings.qdrant_collection)

    def search(self, query: str, limit: int | None = None) -> list[dict]:
        if not self.ready():
            raise RuntimeError("Vector index is missing. Run: python scripts/ingest.py")

        query_text = f"task: search result | query: {query}"
        vector = self.embeddings.embed_query(query_text)
        result = self.client.query_points(
            collection_name=settings.qdrant_collection,
            query=vector,
            limit=limit or settings.retrieval_top_k,
            with_payload=True,
        )

        hits: list[dict] = []
        for point in result.points:
            payload = dict(point.payload or {})
            payload["score"] = float(point.score)
            hits.append(payload)
        return hits

    def close(self) -> None:
        self.client.close()

    def __enter__(self) -> "Retriever":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()
