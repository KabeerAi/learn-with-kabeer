"""
ChromaDB vector store wrapper for educational content chunks.

Handles collection management, upserting embedded chunks,
and semantic search with metadata filtering.
"""

import os
import threading
from typing import Optional

import chromadb

from ai.config import CHROMADB_DIR, COLLECTION_NAME


_chroma_client: Optional[chromadb.PersistentClient] = None
_collection: Optional[chromadb.Collection] = None
_chroma_lock = threading.Lock()


def _get_collection() -> chromadb.Collection:
    """Get or create the ChromaDB collection (thread-safe)."""
    global _chroma_client, _collection

    with _chroma_lock:
        if _collection is not None:
            return _collection

        os.makedirs(CHROMADB_DIR, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(path=CHROMADB_DIR)
        _collection = _chroma_client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        return _collection


def upsert_chunks(
    ids: list[str],
    embeddings: list[list[float]],
    documents: list[str],
    metadatas: list[dict],
) -> None:
    """
    Upsert embedded chunks into ChromaDB.

    Args:
        ids: Unique identifiers for each chunk.
        embeddings: Embedding vectors.
        documents: The raw text content of each chunk.
        metadatas: Metadata dicts for each chunk.
    """
    collection = _get_collection()

    # ChromaDB has a batch limit, upsert in groups of 500
    batch_size = 500
    for i in range(0, len(ids), batch_size):
        end = i + batch_size
        collection.upsert(
            ids=ids[i:end],
            embeddings=embeddings[i:end],
            documents=documents[i:end],
            metadatas=metadatas[i:end],
        )


def query_chunks(
    query_embedding: list[float],
    n_results: int = 5,
    where: Optional[dict] = None,
    where_document: Optional[dict] = None,
) -> dict:
    """
    Query the vector store for similar chunks.

    Args:
        query_embedding: The embedding vector to search with.
        n_results: Number of results to return.
        where: Metadata filter dict (e.g., {"chunk_type": "analogy"}).
        where_document: Document content filter.

    Returns:
        ChromaDB query results dict with keys:
        ids, documents, metadatas, distances
    """
    collection = _get_collection()

    kwargs = {
        "query_embeddings": [query_embedding],
        "n_results": n_results,
        "include": ["documents", "metadatas", "distances"],
    }

    if where:
        kwargs["where"] = where
    if where_document:
        kwargs["where_document"] = where_document

    return collection.query(**kwargs)


def get_collection_count() -> int:
    """Return the number of chunks stored in the collection."""
    try:
        collection = _get_collection()
        return collection.count()
    except Exception:
        return 0


def reset_collection() -> None:
    """Delete and recreate the collection (for full rebuild)."""
    global _collection
    client = _get_collection()  # ensures client is initialized

    try:
        _chroma_client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    _collection = _chroma_client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
