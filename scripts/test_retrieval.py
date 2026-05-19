"""
CLI script to test retrieval quality from the vector store.

Usage:
    python scripts/test_retrieval.py "variables in python"
    python scripts/test_retrieval.py "numpy arrays" --type analogy
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from ai.retrieval.search import (
    search_teaching_examples,
    search_analogies,
    search_exercises,
    search_code_examples,
    search_all_references,
)


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_retrieval.py \"topic\" [--type analogy|exercise|code|all]")
        return

    topic = sys.argv[1]
    search_type = "all"

    if "--type" in sys.argv:
        idx = sys.argv.index("--type")
        if idx + 1 < len(sys.argv):
            search_type = sys.argv[idx + 1]

    print(f"{'='*60}")
    print(f"  Retrieval Test: \"{topic}\"")
    print(f"  Type: {search_type}")
    print(f"{'='*60}\n")

    if search_type == "all":
        refs = search_all_references(topic)
        for category, items in refs.items():
            print(f"\n── {category.upper()} ({len(items)} results) ──")
            for i, item in enumerate(items, 1):
                meta = item.get("metadata", {})
                print(f"\n  [{i}] Similarity: {item.get('similarity', 0):.4f}")
                print(f"      Course: {meta.get('course_title', 'N/A')}")
                print(f"      Lesson: {meta.get('lesson_title', 'N/A')}")
                print(f"      Type:   {meta.get('chunk_type', 'N/A')}")
                print(f"      Style:  {meta.get('teaching_style', 'N/A')}")
                content_preview = item["content"][:200].replace("\n", " ")
                print(f"      Content: {content_preview}...")
    else:
        search_fn = {
            "analogy": search_analogies,
            "exercise": search_exercises,
            "code": search_code_examples,
            "teaching": search_teaching_examples,
        }.get(search_type, search_teaching_examples)

        results = search_fn(topic)
        print(f"Found {len(results)} results:\n")
        for i, item in enumerate(results, 1):
            meta = item.get("metadata", {})
            print(f"[{i}] Similarity: {item.get('similarity', 0):.4f}")
            print(f"    From: {meta.get('course_title', '')} / {meta.get('lesson_title', '')}")
            print(f"    Type: {meta.get('chunk_type', '')} | Style: {meta.get('teaching_style', '')}")
            print(f"    Content:\n      {item['content'][:300]}")
            print()


if __name__ == "__main__":
    main()
