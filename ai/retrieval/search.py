"""
Semantic search engine for educational content.

Provides specialized search functions that retrieve relevant teaching
examples, analogies, exercises, and pacing patterns from the dataset.
"""

from typing import Optional

from ai.config import DEFAULT_RETRIEVAL_K
from ai.embeddings.embedder import generate_single_embedding
from ai.embeddings.store import query_chunks


def search_teaching_examples(
    topic: str,
    difficulty: Optional[str] = None,
    k: int = DEFAULT_RETRIEVAL_K,
) -> list[dict]:
    """
    Search for teaching examples relevant to a topic.

    Returns chunks that show how similar concepts are explained
    in the dataset courses.
    """
    embedding = generate_single_embedding(
        f"How to teach and explain {topic} to a {difficulty or 'beginner'} student"
    )

    where = {}
    if difficulty:
        where["difficulty"] = difficulty

    results = query_chunks(
        query_embedding=embedding,
        n_results=k,
        where=where if where else None,
    )

    return _format_results(results)


def search_analogies(topic: str, k: int = 3) -> list[dict]:
    """Search for analogies used to explain similar concepts."""
    embedding = generate_single_embedding(
        f"Analogy or metaphor to explain {topic} in simple terms"
    )

    results = query_chunks(
        query_embedding=embedding,
        n_results=k,
        where={"chunk_type": "analogy"},
    )

    return _format_results(results)


def search_exercises(topic: str, k: int = 3) -> list[dict]:
    """Search for exercises related to a topic."""
    embedding = generate_single_embedding(
        f"Practice exercise or hands-on challenge for {topic}"
    )

    results = query_chunks(
        query_embedding=embedding,
        n_results=k,
        where={"chunk_type": "exercise"},
    )

    return _format_results(results)


def search_recaps(topic: str, k: int = 3) -> list[dict]:
    """Search for recap patterns used in similar lessons."""
    embedding = generate_single_embedding(
        f"Summary and recap of key points about {topic}"
    )

    results = query_chunks(
        query_embedding=embedding,
        n_results=k,
        where={"chunk_type": "recap"},
    )

    return _format_results(results)


def search_code_examples(topic: str, k: int = 3) -> list[dict]:
    """Search for code examples related to a topic."""
    embedding = generate_single_embedding(
        f"Code example demonstrating {topic} with explanation"
    )

    results = query_chunks(
        query_embedding=embedding,
        n_results=k,
        where={"chunk_type": "explained_code"},
    )

    # Fall back to code_example if explained_code doesn't have enough
    if len(_format_results(results)) < k:
        fallback = query_chunks(
            query_embedding=embedding,
            n_results=k,
            where={"chunk_type": "code_example"},
        )
        results_list = _format_results(results) + _format_results(fallback)
        return results_list[:k]

    return _format_results(results)


def search_pacing_examples(topic: str, k: int = 3) -> list[dict]:
    """
    Search for full explanation blocks to understand pacing.

    Returns broader teaching blocks that show how lessons are structured.
    """
    embedding = generate_single_embedding(
        f"Beginner-friendly lesson teaching {topic} step by step"
    )

    results = query_chunks(
        query_embedding=embedding,
        n_results=k,
        where={"chunk_type": "explanation"},
    )

    return _format_results(results)


def search_all_references(topic: str, difficulty: str = "Beginner") -> dict:
    """
    Perform a comprehensive search across all chunk types for a topic.

    Returns a dict with categorized results for context building.
    Uses batch embedding to minimize API latency.
    """
    from ai.embeddings.embedder import generate_embeddings
    
    # 1. Prepare all query prompts
    prompts = [
        f"How to teach and explain {topic} to a {difficulty} student",      # teaching examples
        f"Analogy or metaphor to explain {topic} in simple terms",          # analogies
        f"Practice exercise or hands-on challenge for {topic}",            # exercises
        f"Summary and recap of key points about {topic}",                 # recaps
        f"Code example demonstrating {topic} with explanation",           # code
        f"Beginner-friendly lesson teaching {topic} step by step"          # pacing
    ]
    
    # 2. Generate all embeddings in one batch
    print(f"    [RETRIEVE] Generating batch embeddings for search queries...")
    embeddings = generate_embeddings(prompts)
    
    # 3. Perform ChromaDB queries with pre-generated embeddings
    return {
        "teaching_examples": _format_results(query_chunks(
            query_embedding=embeddings[0], n_results=4, where={"difficulty": difficulty} if difficulty else None
        )),
        "analogies": _format_results(query_chunks(
            query_embedding=embeddings[1], n_results=2, where={"chunk_type": "analogy"}
        )),
        "exercises": _format_results(query_chunks(
            query_embedding=embeddings[2], n_results=2, where={"chunk_type": "exercise"}
        )),
        "code_examples": _format_results(query_chunks(
            query_embedding=embeddings[4], n_results=2, where={"chunk_type": "explained_code"}
        )),
        "pacing_examples": _format_results(query_chunks(
            query_embedding=embeddings[5], n_results=2, where={"chunk_type": "explanation"}
        )),
    }


def _format_results(results: dict) -> list[dict]:
    """Convert ChromaDB query results into a clean list of dicts."""
    if not results or not results.get("documents"):
        return []

    formatted = []
    docs = results["documents"][0] if results["documents"] else []
    metas = results["metadatas"][0] if results.get("metadatas") else []
    dists = results["distances"][0] if results.get("distances") else []

    for i, doc in enumerate(docs):
        item = {
            "content": doc,
            "metadata": metas[i] if i < len(metas) else {},
            "similarity": round(1 - (dists[i] if i < len(dists) else 0), 4),
        }
        formatted.append(item)

    return formatted
