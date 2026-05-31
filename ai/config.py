"""
Centralized configuration for the AI educational engine.
"""

import os

# ─── Models ─────────────────────────────────────────────────────────────────

GENERATION_MODEL = "llama-3.3-70b-versatile"
EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIMENSIONS = 3072

# ─── Paths ──────────────────────────────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_DIR = os.path.join(BASE_DIR, "dataset", "transformed")
CHROMADB_DIR = os.path.join(BASE_DIR, "instance", "chromadb")

# ─── Chunking ───────────────────────────────────────────────────────────────

# Maximum number of components to group into a single chunk
MAX_COMPONENTS_PER_CHUNK = 6
# Minimum components before creating a chunk (avoid tiny fragments)
MIN_COMPONENTS_PER_CHUNK = 2

# ─── Retrieval ──────────────────────────────────────────────────────────────

# Default number of results to retrieve
DEFAULT_RETRIEVAL_K = 5
# Maximum tokens budget for retrieved context
MAX_CONTEXT_TOKENS = 4000
# ChromaDB collection name
COLLECTION_NAME = "educational_chunks"

# ─── Generation ─────────────────────────────────────────────────────────────

# Minimum builder blocks per generated lesson
MIN_BLOCKS_PER_LESSON = 15
# Maximum builder blocks per generated lesson
MAX_BLOCKS_PER_LESSON = 25

# ─── Quality ────────────────────────────────────────────────────────────────

# Minimum overall quality score (0-10) to pass validation
QUALITY_THRESHOLD = 7.0
# Maximum regeneration attempts for weak sections
MAX_REGEN_ATTEMPTS = 1

# ─── Embedding Batch ────────────────────────────────────────────────────────

EMBEDDING_BATCH_SIZE = 50
EMBEDDING_RATE_LIMIT_DELAY = 3.0  # seconds between batches (generous for free tier)
