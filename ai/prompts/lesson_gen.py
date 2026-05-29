"""
Prompt template for full lesson content generation.

Takes a lesson plan + educational references and generates
the complete builder_json content.
"""

from ai.prompts.system import SYSTEM_PERSONA, PEDAGOGICAL_FLOW, BLOCK_TYPES_REFERENCE


def build_lesson_generation_prompt(
    lesson_plan: dict,
    course_title: str,
    difficulty: str,
    memory_context: str,
    rag_context: str,
    section_name: str,
) -> str:
    """Build the prompt for generating a single lesson's full content."""

    plan_sections = lesson_plan.get("sections", [])
    plan_text = ""
    for sec in plan_sections:
        plan_text += f"\n  - [{sec['purpose']}] {sec['heading']}: {sec.get('notes', '')}"
        plan_text += f" (blocks: {', '.join(sec.get('block_types', []))})"

    summary = lesson_plan.get("summary", "")
    title = lesson_plan.get("title", "Untitled Lesson")
    key_concepts = ", ".join(lesson_plan.get("key_concepts", []))

    return f"""{SYSTEM_PERSONA}

{PEDAGOGICAL_FLOW}

{BLOCK_TYPES_REFERENCE}

═══════════════════════════════════════════════════════════
LESSON GENERATION TASK
═══════════════════════════════════════════════════════════

COURSE: {course_title}
SECTION: {section_name}
LESSON: {title}
SUMMARY: {summary}
DIFFICULTY: {difficulty}
KEY CONCEPTS: {key_concepts}

LESSON STRUCTURE PLAN:
{plan_text}

{memory_context}

{rag_context}

═══════════════════════════════════════════════════════════
PRACTICAL TEACHING RULES
═══════════════════════════════════════════════════════════

1. SHOW CODE FIRST
Always start by showing a short, focused code snippet (max 10 lines) that teaches one specific concept. Use realistic examples like login systems, shopping carts, or API calls—not toy examples like x = 5.

2. EXPLAIN CLEARLY
After showing the code:
- First, explain what the code does in simple terms
- Then, break down each important line with:
  - What it does
  - Why it's written that way
  - Any syntax the student needs to know

3. ONE SMALL IDEA AT A TIME
Don't overload the student! Teach one concept, let them absorb it, then move on. Use SEPARATOR blocks every 3-5 blocks to split the lesson into digestible slides.

4. PRACTICAL & USEFUL
Focus on what developers actually do in real projects. Show the most common way to write code first, then mention variations or best practices.

5. INTERACTIVE
Include quizzes to test understanding, callouts for tips and common mistakes, and encourage the student to experiment.

═══════════════════════════════════════════════════════════
FINAL GOAL
═══════════════════════════════════════════════════════════

Make the student feel:
- Confident that they understand the concept
- Excited to use what they've learned
- Like they're getting real, practical skills

Generate the lesson accordingly.

OUTPUT FORMAT — return ONLY this JSON:
{{
  "title": "{title}",
  "summary": "{summary}",
  "builder_json": [
    {{"type": "heading", "data": {{"text": "..."}}}},
    {{"type": "text", "data": {{"text": "..."}}}},
    ...
  ]
}}
"""
