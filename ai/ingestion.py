"""
Dataset ingestion orchestrator.

Scans the transformed dataset directory, parses course JSONs,
chunks educational content, generates embeddings, and stores
everything in ChromaDB.
"""

import hashlib
import os
import time

from ai.config import DATASET_DIR
from ai.embeddings.chunker import chunk_course, load_course_json
from ai.embeddings.embedder import generate_embeddings
from ai.embeddings.store import (
    get_collection_count,
    reset_collection,
    upsert_chunks,
)


def ingest_all_datasets(rebuild: bool = False) -> dict:
    """
    Ingest all transformed course JSON files into the vector store.

    Args:
        rebuild: If True, wipe the vector store and re-ingest everything.

    Returns:
        Stats dict with ingestion results.
    """
    start_time = time.time()
    stats = {
        "files_found": 0,
        "files_ingested": 0,
        "total_chunks": 0,
        "total_embeddings": 0,
        "errors": [],
        "elapsed_seconds": 0,
    }

    if rebuild:
        print("[INGEST] Rebuilding vector store from scratch...")
        reset_collection()

    # Discover all JSON files in dataset/transformed/
    json_files = _discover_dataset_files()
    stats["files_found"] = len(json_files)
    print(f"[INGEST] Found {len(json_files)} dataset file(s) in {DATASET_DIR}")

    if not json_files:
        print("[INGEST] No dataset files found. Skipping ingestion.")
        stats["elapsed_seconds"] = time.time() - start_time
        return stats

    all_chunks = []

    # Phase 1: Parse and chunk all courses
    for filepath in json_files:
        rel_path = os.path.relpath(filepath, DATASET_DIR)
        print(f"  [PARSE] {rel_path}")

        course_data = load_course_json(filepath)
        if course_data is None:
            stats["errors"].append(f"Failed to parse: {rel_path}")
            continue

        chunks = chunk_course(course_data, source_file=rel_path)
        print(f"    -> {len(chunks)} chunks")
        all_chunks.extend(chunks)
        stats["files_ingested"] += 1

    stats["total_chunks"] = len(all_chunks)

    if not all_chunks:
        print("[INGEST] No chunks produced. Skipping embedding.")
        stats["elapsed_seconds"] = time.time() - start_time
        return stats

    # Phase 2: Generate embeddings
    print(f"[INGEST] Generating embeddings for {len(all_chunks)} chunks...")
    texts = [c["content"] for c in all_chunks]
    embeddings = generate_embeddings(texts)
    stats["total_embeddings"] = len(embeddings)
    print(f"  -> Generated {len(embeddings)} embeddings")

    # Phase 3: Store in ChromaDB
    print("[INGEST] Storing in vector database...")
    ids = []
    documents = []
    metadatas = []

    for i, chunk in enumerate(all_chunks):
        # Create a stable, unique ID based on content hash
        content_hash = hashlib.md5(
            chunk["content"].encode("utf-8")
        ).hexdigest()[:12]
        chunk_id = f"chunk_{content_hash}_{i}"

        ids.append(chunk_id)
        documents.append(chunk["content"])
        metadatas.append(chunk["metadata"])

    upsert_chunks(ids, embeddings, documents, metadatas)
    print(f"  -> Stored {len(ids)} chunks in ChromaDB")

    elapsed = time.time() - start_time
    stats["elapsed_seconds"] = round(elapsed, 2)

    print(f"[INGEST] Complete in {elapsed:.1f}s")
    print(f"  Files: {stats['files_ingested']}/{stats['files_found']}")
    print(f"  Chunks: {stats['total_chunks']}")
    print(f"  Embeddings: {stats['total_embeddings']}")

    if stats["errors"]:
        print(f"  Errors: {len(stats['errors'])}")
        for err in stats["errors"]:
            print(f"    - {err}")

    return stats


def get_ingestion_stats() -> dict:
    """Return current vector store statistics."""
    count = get_collection_count()
    files = _discover_dataset_files()
    return {
        "dataset_files": len(files),
        "stored_chunks": count,
        "dataset_dir": DATASET_DIR,
    }


def ensure_ingested() -> None:
    """
    Check if the vector store is populated; if not, run ingestion.
    Called on app startup to ensure the dataset is ready.
    """
    count = get_collection_count()
    if count == 0:
        print("[STARTUP] Vector store is empty. Running initial dataset ingestion...")
        ingest_all_datasets()
    else:
        print(f"[STARTUP] Vector store ready: {count} chunks loaded.")


def _discover_dataset_files() -> list[str]:
    """Recursively find all .json files in the dataset directory."""
    json_files = []
    if not os.path.exists(DATASET_DIR):
        return json_files

    for root, _dirs, files in os.walk(DATASET_DIR):
        for fname in sorted(files):
            if fname.endswith(".json"):
                json_files.append(os.path.join(root, fname))

    return json_files
