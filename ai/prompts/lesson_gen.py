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
GENERATION INSTRUCTIONS
═══════════════════════════════════════════════════════════

Generate the COMPLETE lesson content as a JSON array of builder blocks.

Follow the lesson structure plan above. For each planned section:
1. Create a heading block
2. Write 2-4 text blocks with substantial, conversational teaching content
3. Include code blocks with practical examples (not toy code)
4. Add appropriate callout blocks (analogies, tips, warnings)
5. End with a practice exercise and quiz

CRITICAL QUALITY RULES:
- Each text block should be 2-3 sentences. NEVER write giant paragraphs.
- After every code block, add a text block explaining what the code does.
- Use <b>bold</b> for key terms and <code>inline code</code> for syntax references.
- Make analogies specific and visual, not vague.
- Total blocks: {lesson_plan.get('estimated_blocks', 15)} minimum.
- The content should feel like a patient mentor explaining things, NOT like a textbook.

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
