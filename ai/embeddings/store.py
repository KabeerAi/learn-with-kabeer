"""
Dual-mode vector store wrapper.

Uses PostgreSQL (pgvector) when available (Render/Production),
falls back to ChromaDB for local development (SQLite).
"""

import os
import json
import threading
from typing import Optional

import chromadb
import psycopg2
from flask import current_app

from ai.config import CHROMADB_DIR, COLLECTION_NAME


# ─── Shared State ───────────────────────────────────────────────────────────

_chroma_client: Optional[chromadb.PersistentClient] = None
_collection: Optional[chromadb.Collection] = None
_chroma_lock = threading.Lock()


def _get_db_type():
    """Detect if we should use Postgres or ChromaDB."""
    try:
        db_uri = current_app.config.get("DATABASE", "")
    except:
        db_uri = os.environ.get("DATABASE_URL", "")
    
    if db_uri.startswith(("postgresql://", "postgres://")):
        return "postgres", db_uri
    return "chroma", None


# ─── ChromaDB Implementation ────────────────────────────────────────────────

def _get_collection() -> chromadb.Collection:
    """Get or create the ChromaDB collection (thread-safe)."""
    global _chroma_client, _collection

    with _chroma_lock:
        if _collection is not None:
            return _collection

        os.makedirs(CHROMADB_DIR, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(
            path=CHROMADB_DIR,
            settings=chromadb.Settings(anonymized_telemetry=False)
        )
        
        _collection = _chroma_client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
            embedding_function=None
        )
        return _collection


# ─── Public API ─────────────────────────────────────────────────────────────

def upsert_chunks(
    ids: list[str],
    embeddings: list[list[float]],
    documents: list[str],
    metadatas: list[dict],
) -> None:
    """Upsert embedded chunks into the active vector store."""
    db_type, db_uri = _get_db_type()

    if db_type == "postgres":
        conn = psycopg2.connect(db_uri)
        try:
            with conn.cursor() as cur:
                for i in range(len(ids)):
                    cur.execute(
                        """
                        INSERT INTO educational_chunks (id, content, embedding, metadata)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET 
                            content = EXCLUDED.content, 
                            embedding = EXCLUDED.embedding, 
                            metadata = EXCLUDED.metadata
                        """,
                        (ids[i], documents[i], embeddings[i], json.dumps(metadatas[i]))
                    )
            conn.commit()
            print(f"  [PG-STORE] Upserted {len(ids)} chunks to Postgres")
        finally:
            conn.close()
    else:
        collection = _get_collection()
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
    """Query the vector store for similar chunks."""
    db_type, db_uri = _get_db_type()

    if db_type == "postgres":
        conn = psycopg2.connect(db_uri)
        try:
            with conn.cursor() as cur:
                # Basic cosine similarity search using pgvector
                # Operators: <=> is cosine distance. 1 - distance is similarity.
                
                query = """
                    SELECT id, content, metadata, 1 - (embedding <=> %s::vector) AS similarity
                    FROM educational_chunks
                """
                params = [query_embedding]

                # Simple metadata filtering if provided
                if where:
                    filters = []
                    for key, value in where.items():
                        filters.append(f"metadata->>'{key}' = %s")
                        params.append(str(value))
                    query += " WHERE " + " AND ".join(filters)

                query += " ORDER BY embedding <=> %s::vector LIMIT %s"
                params.extend([query_embedding, n_results])

                cur.execute(query, params)
                rows = cur.fetchall()

                # Format results to match ChromaDB structure
                return {
                    "documents": [[r[1] for r in rows]],
                    "metadatas": [[json.loads(r[2]) if isinstance(r[2], str) else r[2] for r in rows]],
                    "distances": [[1 - float(r[3]) for r in rows]], # Convert similarity back to distance
                }
        except Exception as e:
            print(f"  [PG-STORE ERROR] {e}")
            return {"documents": [[]], "metadatas": [[]], "distances": [[]]}
        finally:
            conn.close()
    else:
        collection = _get_collection()
        with _chroma_lock:
            return collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where,
                where_document=where_document,
                include=["documents", "metadatas", "distances"]
            )


def get_collection_count() -> int:
    """Return the number of chunks stored in the active store."""
    db_type, db_uri = _get_db_type()
    if db_type == "postgres":
        conn = psycopg2.connect(db_uri)
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM educational_chunks")
                return cur.fetchone()[0]
        except:
            return 0
        finally:
            conn.close()
    else:
        try:
            collection = _get_collection()
            return collection.count()
        except:
            return 0


def reset_collection() -> None:
    """Clear all data from the active vector store."""
    db_type, db_uri = _get_db_type()
    if db_type == "postgres":
        conn = psycopg2.connect(db_uri)
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM educational_chunks")
            conn.commit()
        finally:
            conn.close()
    else:
        global _collection
        _get_collection() # Ensure client is init
        try:
            _chroma_client.delete_collection(COLLECTION_NAME)
        except:
            pass
        _collection = None
        _get_collection()
