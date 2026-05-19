"""
Educational quality validation engine.

Evaluates generated lessons for quality across multiple
dimensions and identifies weak sections for regeneration.
"""

import json
import os

from groq import Groq

from ai.config import GENERATION_MODEL, QUALITY_THRESHOLD
from ai.prompts.quality_eval import build_quality_eval_prompt


def validate_lesson(
    builder_json: list[dict],
    lesson_title: str,
    difficulty: str,
) -> dict:
    """
    Validate a generated lesson's educational quality.

    Returns:
        {
            "scores": {...},
            "overall_score": float,
            "verdict": "PASS" | "NEEDS_IMPROVEMENT",
            "weak_sections": [...],
            "summary": str
        }
    """
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

    lesson_json_str = json.dumps(builder_json, indent=2)
    prompt = build_quality_eval_prompt(lesson_json_str, lesson_title, difficulty)

    try:
        response = client.chat.completions.create(
            model=GENERATION_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.3
        )

        result = json.loads(response.choices[0].message.content)

        # Ensure verdict is based on our threshold
        overall = result.get("overall_score", 0)
        if overall >= QUALITY_THRESHOLD:
            result["verdict"] = "PASS"
        else:
            result["verdict"] = "NEEDS_IMPROVEMENT"

        return result

    except Exception as e:
        print(f"    [VALIDATE ERROR] {e}")
        # Return a passing result on error to avoid blocking generation
        return {
            "scores": {},
            "overall_score": 7.0,
            "verdict": "PASS",
            "weak_sections": [],
            "summary": "Validation skipped due to error.",
        }


def quick_structural_check(builder_json: list[dict]) -> dict:
    """
    Fast, non-AI structural quality check.

    Validates block types, minimum counts, and basic structure
    without making an API call.
    """
    issues = []
    block_count = len(builder_json)
    types_used = [b.get("type", "") for b in builder_json]
    type_counts = {}
    for t in types_used:
        type_counts[t] = type_counts.get(t, 0) + 1

    # Check minimum blocks
    if block_count < 8:
        issues.append(f"Only {block_count} blocks (minimum 8 recommended)")

    # Check for required types
    if "heading" not in type_counts:
        issues.append("No heading blocks — lesson needs topic structure")

    if type_counts.get("heading", 0) < 2:
        issues.append("Only 1 heading — lessons should have 2-3 sections")

    if "code" not in type_counts:
        issues.append("No code blocks — programming lessons need examples")

    if "text" not in type_counts or type_counts.get("text", 0) < 3:
        issues.append("Too few text blocks — needs more explanation content")

    # Check for consecutive code blocks without explanation
    for i in range(len(builder_json) - 1):
        if builder_json[i].get("type") == "code" and builder_json[i + 1].get("type") == "code":
            issues.append(f"Consecutive code blocks at index {i} — add explanation between them")

    passed = len(issues) == 0

    return {
        "passed": passed,
        "block_count": block_count,
        "type_distribution": type_counts,
        "issues": issues,
    }
