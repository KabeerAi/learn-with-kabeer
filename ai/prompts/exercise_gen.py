"""
Prompt template for exercise generation.

Used when the main lesson generator produces weak exercises
or when standalone exercises are needed.
"""


def build_exercise_prompt(
    topic: str,
    difficulty: str,
    concepts_covered: list[str],
    exercise_references: str = "",
) -> str:
    """Build prompt for generating a practice exercise."""

    concepts_text = ", ".join(concepts_covered) if concepts_covered else topic

    return f"""You are creating a hands-on practice exercise for a {difficulty} programming student.

TOPIC: {topic}
CONCEPTS THE STUDENT JUST LEARNED: {concepts_text}

{exercise_references}

Create a practical, achievable exercise that:
1. Tests understanding of the concepts just taught
2. Is specific — tells the student EXACTLY what to build
3. Has a clear expected outcome
4. Is something they can complete in 5-10 minutes
5. Feels like a real-world task, not a textbook drill

EXERCISE QUALITY RULES:
- Don't say "write a program that..." — frame it as a mini-challenge or scenario
- Give concrete values and expected outputs
- Make it interesting (use fun scenarios, relatable contexts)
- Include one small twist that makes them think

Return JSON:
{{
  "exercise": {{
    "description": "The exercise prompt text (2-3 sentences)",
    "hint": "A subtle hint without giving the answer",
    "expected_concepts": ["concept1", "concept2"]
  }}
}}
"""
