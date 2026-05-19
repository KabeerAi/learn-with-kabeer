"""
AI Educational Engine for Learn with Kabeer.

Dataset-driven course generation using RAG (Retrieval-Augmented Generation)
to produce premium-quality programming lessons.
"""

from ai.ingestion import ingest_all_datasets, get_ingestion_stats
from ai.pipelines.course_pipeline import generate_course

__all__ = [
    "ingest_all_datasets",
    "get_ingestion_stats",
    "generate_course",
]
