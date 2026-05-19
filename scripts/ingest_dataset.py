"""
CLI script to ingest the transformed educational dataset into the vector store.

Usage:
    python scripts/ingest_dataset.py             # Incremental ingestion
    python scripts/ingest_dataset.py --rebuild    # Full rebuild
    python scripts/ingest_dataset.py --stats      # Show stats only
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from ai.ingestion import ingest_all_datasets, get_ingestion_stats


def main():
    args = sys.argv[1:]

    if "--stats" in args:
        stats = get_ingestion_stats()
        print("=== Dataset Ingestion Stats ===")
        print(f"  Dataset directory: {stats['dataset_dir']}")
        print(f"  Dataset files:     {stats['dataset_files']}")
        print(f"  Stored chunks:     {stats['stored_chunks']}")
        return

    rebuild = "--rebuild" in args
    print("=" * 50)
    print("  Learn with Kabeer — Dataset Ingestion")
    print("=" * 50)
    print()

    stats = ingest_all_datasets(rebuild=rebuild)

    print()
    print("=" * 50)
    print("  Ingestion Summary")
    print("=" * 50)
    print(f"  Files found:    {stats['files_found']}")
    print(f"  Files ingested: {stats['files_ingested']}")
    print(f"  Total chunks:   {stats['total_chunks']}")
    print(f"  Embeddings:     {stats['total_embeddings']}")
    print(f"  Time:           {stats['elapsed_seconds']}s")

    if stats["errors"]:
        print(f"  Errors:         {len(stats['errors'])}")
    print()


if __name__ == "__main__":
    main()
