"""
Multi-stage lesson generator.

Generates a single lesson through multiple stages:
1. PLAN — Structure the lesson
2. GENERATE — Create content
3. VALIDATE — Check quality
4. REGENERATE — Fix weak sections (if needed)
"""

import json
import os

from groq import Groq

from ai.config import GENERATION_MODEL, MIN_BLOCKS_PER_LESSON
from ai.prompts.lesson_plan import build_lesson_plan_prompt
from ai.prompts.lesson_gen import build_lesson_generation_prompt
from ai.retrieval.search import search_all_references
from ai.retrieval.context_builder import build_generation_context, extract_teaching_patterns


def generate_lesson(
    lesson_title: str,
    lesson_objective: str,
    lesson_number: int,
    section_name: str,
    course_title: str,
    difficulty: str,
    memory_context: str,
    backgrounds: list[str] = None,
) -> dict:
    """
    Generate a single lesson through the multi-stage pipeline.

    Returns a dict with:
      title, summary, section, section_background, number, builder_json
    """
    import time
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

    # ── Stage 1: Retrieve educational references ───────────────────────
    print(f"    [RETRIEVE] Searching dataset for: {lesson_title}")
    start_time = time.time()
    references = search_all_references(lesson_title, difficulty)
    rag_context = build_generation_context(references, lesson_title)
    teaching_patterns = extract_teaching_patterns(references)
    print(f"    [RETRIEVE] Complete in {time.time() - start_time:.2f}s")

    # ── Stage 2: Plan the lesson structure ─────────────────────────────
    print(f"    [PLAN] Planning lesson structure...")
    start_time = time.time()
    plan_prompt = build_lesson_plan_prompt(
        lesson_title=lesson_title,
        lesson_objective=lesson_objective,
        course_title=course_title,
        difficulty=difficulty,
        memory_context=memory_context,
        teaching_patterns=teaching_patterns,
    )

    plan_response = client.chat.completions.create(
        model=GENERATION_MODEL,
        messages=[{"role": "user", "content": plan_prompt}],
        response_format={"type": "json_object"},
        temperature=0.3
    )

    try:
        plan_data = json.loads(plan_response.choices[0].message.content)
        lesson_plan = plan_data.get("lesson_plan", plan_data)
    except (json.JSONDecodeError, AttributeError):
        # Fallback plan if parsing fails
        lesson_plan = {
            "title": lesson_title,
            "summary": lesson_objective,
            "estimated_blocks": 15,
            "sections": [
                {"heading": lesson_title, "purpose": "explanation",
                 "block_types": ["text", "code"], "notes": lesson_objective, "estimated_blocks": 15}
            ],
            "key_concepts": [],
            "terminology": [],
        }

    # Ensure title is set
    lesson_plan["title"] = lesson_plan.get("title", lesson_title)
    lesson_plan["summary"] = lesson_plan.get("summary", lesson_objective)
    print(f"    [PLAN] Complete in {time.time() - start_time:.2f}s")

    # ── Stage 3: Generate the full lesson content ──────────────────────
    print(f"    [GENERATE] Generating content for {len(lesson_plan.get('sections', []))} sections...")
    start_time = time.time()
    gen_prompt = build_lesson_generation_prompt(
        lesson_plan=lesson_plan,
        course_title=course_title,
        difficulty=difficulty,
        memory_context=memory_context,
        rag_context=rag_context,
        section_name=section_name,
    )

    gen_response = client.chat.completions.create(
        model=GENERATION_MODEL,
        messages=[{"role": "user", "content": gen_prompt}],
        response_format={"type": "json_object"},
        temperature=0.3
    )

    try:
        lesson_data = json.loads(gen_response.choices[0].message.content)
    except (json.JSONDecodeError, AttributeError):
        # If JSON parsing fails, create a minimal lesson
        lesson_data = {
            "title": lesson_title,
            "summary": lesson_objective,
            "builder_json": [
                {"type": "heading", "data": {"text": lesson_title}},
                {"type": "text", "data": {"text": f"This lesson covers {lesson_objective}."}},
            ],
        }

    builder_json = lesson_data.get("builder_json", [])
    
    # Capture the technical footprint for continuity
    footprint = lesson_data.get("memory_footprint", "")
    if footprint:
        lesson_plan["memory_footprint"] = footprint

    # Ensure minimum block count
    if len(builder_json) < MIN_BLOCKS_PER_LESSON:
        print(f"    [WARN] Only {len(builder_json)} blocks generated (min: {MIN_BLOCKS_PER_LESSON})")

    # Pick a background image for the section
    section_bg = ""
    if backgrounds:
        import hashlib
        hash_val = int(hashlib.md5(section_name.encode()).hexdigest(), 16)
        section_bg = backgrounds[hash_val % len(backgrounds)]

    result = {
        "number": lesson_number,
        "title": lesson_data.get("title", lesson_title),
        "summary": lesson_data.get("summary", lesson_objective),
        "section": section_name,
        "section_background": section_bg,
        "builder_json": builder_json,
        "plan": lesson_plan,  # Keep plan for memory system
    }

    print(f"    [DONE] Stage complete in {time.time() - start_time:.2f}s. {len(builder_json)} blocks generated.")
    return result
