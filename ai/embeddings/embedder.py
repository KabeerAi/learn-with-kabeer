"""
Embedding generator using Google Gemini embedding model.

Handles batching and rate limiting for efficient embedding generation.
"""

import os
import time
from typing import Optional

from google import genai

from ai.config import (
    EMBEDDING_MODEL,
    EMBEDDING_RATE_LIMIT_DELAY,
)

# Smaller batch size to respect free-tier rate limits
_BATCH_SIZE = 10

_client: Optional[genai.Client] = None


def _get_client() -> genai.Client:
    """Lazy-init the Gemini client."""
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    return _client


def _embed_batch(client, batch: list[str], max_retries: int = 5) -> list[list[float]]:
    """Embed a single batch with retry logic. Returns embeddings or raises."""
    for attempt in range(1, max_retries + 1):
        try:
            result = client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=batch,
            )
            return [emb.values for emb in result.embeddings]
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                wait = EMBEDDING_RATE_LIMIT_DELAY * (2 ** attempt)
                print(f"  [RATE LIMIT] Waiting {wait:.1f}s before retry {attempt}/{max_retries}...")
                time.sleep(wait)
            else:
                raise
    # If all retries fail, raise
    raise RuntimeError(f"Failed to embed batch after {max_retries} retries")


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """
    Generate embeddings for a list of texts using Gemini.

    Handles batching and rate limiting automatically.
    Returns a list of embedding vectors (each a list of floats).
    Guarantees len(result) == len(texts) or raises an error.
    """
    client = _get_client()
    all_embeddings = []

    for i in range(0, len(texts), _BATCH_SIZE):
        batch = texts[i : i + _BATCH_SIZE]
        batch_num = (i // _BATCH_SIZE) + 1
        total_batches = (len(texts) + _BATCH_SIZE - 1) // _BATCH_SIZE
        print(f"  [EMBED] Batch {batch_num}/{total_batches} ({len(batch)} texts)...")

        try:
            embeddings = _embed_batch(client, batch)
            all_embeddings.extend(embeddings)
        except RuntimeError:
            # Fallback: embed one by one
            print(f"  [FALLBACK] Embedding one-by-one for batch {batch_num}...")
            for j, text in enumerate(batch):
                try:
                    embs = _embed_batch(client, [text], max_retries=5)
                    all_embeddings.extend(embs)
                except Exception as e:
                    print(f"  [ERROR] Failed to embed text {i+j}: {e}")
                    # Use zero vector as fallback to maintain alignment
                    all_embeddings.append([0.0] * 768)
                time.sleep(EMBEDDING_RATE_LIMIT_DELAY * 2)

        # Pause between batches to respect rate limits
        if i + _BATCH_SIZE < len(texts):
            time.sleep(EMBEDDING_RATE_LIMIT_DELAY * 2)

    assert len(all_embeddings) == len(texts), (
        f"Embedding count mismatch: {len(all_embeddings)} != {len(texts)}"
    )
    return all_embeddings


def generate_single_embedding(text: str) -> list[float]:
    """Generate embedding for a single text string."""
    results = generate_embeddings([text])
    if results:
        return results[0]
    return []

