"""
Prompt template for lesson planning stage.

The planner determines the structure and flow of a lesson BEFORE
content generation begins, ensuring intentional pedagogy.
"""


def build_lesson_plan_prompt(
    lesson_title: str,
    lesson_objective: str,
    course_title: str,
    difficulty: str,
    memory_context: str,
    teaching_patterns: str,
) -> str:
    """Build the prompt for lesson structure planning."""

    return f"""You are planning the educational structure for a single lesson in a programming course.

COURSE: {course_title}
LESSON: {lesson_title}
OBJECTIVE: {lesson_objective}
DIFFICULTY: {difficulty}

{memory_context}

{teaching_patterns}

Your job is to create a detailed lesson PLAN — not the content itself, just the blueprint.

For each section of the lesson, specify:
1. The heading text
2. What educational purpose it serves (intuition, explanation, example, practice, etc.)
3. Which block types to use (text, code, callout, quiz)
4. Brief notes on what to cover
5. Estimated number of blocks for that section

Output valid JSON:
{{
  "lesson_plan": {{
    "title": "{lesson_title}",
    "summary": "One sentence summary of what students will learn",
    "estimated_blocks": 15,
    "sections": [
      {{
        "heading": "Section heading text",
        "purpose": "intuition|explanation|example|deeper|mistakes|practice|recap",
        "block_types": ["text", "code", "callout"],
        "notes": "Brief description of what to cover",
        "estimated_blocks": 3
      }}
    ],
    "key_concepts": ["concept1", "concept2"],
    "terminology": ["term1", "term2"],
    "prerequisite_concepts": ["what students should already know"]
  }}
}}

RULES:
- Plan for 12-20 total blocks (this is a real lesson, not a summary).
- Follow the pedagogical flow: intuition → explanation → code → deeper → mistakes → practice → recap.
- Include at least one analogy section and one common-mistake section.
- The recap section should include a quiz.
- Be specific in your notes — they guide the content generator.
"""
