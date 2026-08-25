import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

import pymupdf
import yaml
from langchain_ollama import OllamaEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.config import BASE_DIR, settings
from app.text_processing import batched, chunk_text, normalize_text, split_sections


def load_sources() -> list[dict]:
    with open(settings.sources_file, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)["sources"]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def extract_pdf_chunks(source: dict) -> list[dict]:
    path = BASE_DIR / source["path"]
    chunks: list[dict] = []
    current_section: str | None = None
    chunk_index = 0

    with pymupdf.open(path) as document:
        for page_number, page in enumerate(document, start=1):
            page_text = normalize_text(page.get_text("text"))
            sections, current_section = split_sections(page_text, current_section)

            for section, section_text in sections:
                for text in chunk_text(section_text):
                    chunk_id = str(
                        uuid5(
                            NAMESPACE_URL,
                            f"{source['source_id']}|{page_number}|{section}|{chunk_index}|{text[:120]}",
                        )
                    )
                    chunks.append(
                        {
                            "chunk_id": chunk_id,
                            "source_id": source["source_id"],
                            "title": source["title"],
                            "url": source["url"],
                            "authority": source["authority"],
                            "source_type": source["source_type"],
                            "page": page_number,
                            "section": section,
                            "chunk_index": chunk_index,
                            "text": text,
                        }
                    )
                    chunk_index += 1

    return chunks


def build_index() -> dict:
    sources = load_sources()
    all_chunks: list[dict] = []
    source_manifest: list[dict] = []

    for source in sources:
        path = BASE_DIR / source["path"]
        if not path.exists():
            raise FileNotFoundError(
                f"Missing source file: {path}. Run: python scripts/download_sources.py"
            )
        actual_hash = sha256_file(path)
        expected_hash = source.get("sha256")
        if expected_hash and actual_hash.lower() != expected_hash.lower():
            raise ValueError(f"SHA256 mismatch for {path.name}")

        chunks = extract_pdf_chunks(source)
        all_chunks.extend(chunks)
        source_manifest.append(
            {
                "source_id": source["source_id"],
                "file": str(path.relative_to(BASE_DIR)),
                "sha256": actual_hash,
                "chunks": len(chunks),
            }
        )

    embeddings = OllamaEmbeddings(
        model=settings.embedding_model,
        base_url=settings.ollama_base_url,
    )

    qdrant_path = Path(settings.qdrant_path)
    qdrant_path.mkdir(parents=True, exist_ok=True)
    client = QdrantClient(path=str(qdrant_path))

    try:
        if client.collection_exists(settings.qdrant_collection):
            client.delete_collection(settings.qdrant_collection)

        client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=VectorParams(
                size=settings.embedding_dimensions,
                distance=Distance.COSINE,
            ),
        )

        indexed = 0
        for batch in batched(all_chunks, 32):
            document_texts = [
                f"title: {chunk['title']} | text: {chunk['text']}" for chunk in batch
            ]
            vectors = embeddings.embed_documents(document_texts)
            points = [
                PointStruct(id=chunk["chunk_id"], vector=vector, payload=chunk)
                for chunk, vector in zip(batch, vectors, strict=True)
            ]
            client.upsert(collection_name=settings.qdrant_collection, points=points)
            indexed += len(points)
            print(f"Indexed {indexed}/{len(all_chunks)} chunks")
    finally:
        client.close()

    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "collection": settings.qdrant_collection,
        "embedding_model": settings.embedding_model,
        "embedding_dimensions": settings.embedding_dimensions,
        "chunk_count": len(all_chunks),
        "sources": source_manifest,
    }

    data_dir = Path(settings.data_dir)
    (data_dir / "index_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    (data_dir / ".indexed").write_text(manifest["created_at"], encoding="utf-8")
    return manifest
