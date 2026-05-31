"""
Main course generation pipeline.

Orchestrates the complete flow from approved syllabus to finished course:
1. Initialize memory
2. For each lesson: retrieve → plan → generate → validate
3. Return complete course data

This replaces the old `generate_cod_full_content()` from app.py.
"""

import json
import time
import threading

from ai.generators.lesson import generate_lesson
from ai.generators.memory import CourseMemory
from ai.validators.quality import quick_structural_check


# Global progress tracking for the status endpoint
_generation_progress: dict[str, dict] = {}
_progress_lock = threading.Lock()


def get_progress(session_id: str) -> dict:
    """Get the current generation progress for a session."""
    with _progress_lock:
        return _generation_progress.get(session_id, {
            "status": "idle",
            "current_lesson": 0,
            "total_lessons": 0,
            "current_title": "",
            "percent": 0,
        })


def _update_progress(session_id: str, **kwargs) -> None:
    """Update progress for a session."""
    with _progress_lock:
        if session_id not in _generation_progress:
            _generation_progress[session_id] = {}
        _generation_progress[session_id].update(kwargs)


def clear_progress(session_id: str) -> None:
    """Clean up progress data after generation completes."""
    with _progress_lock:
        _generation_progress.pop(session_id, None)


def generate_course(syllabus: dict, backgrounds: list[str] = None, session_id: str = "") -> dict:
    """
    Generate a complete course from an approved syllabus.

    This is the main entry point that replaces generate_cod_full_content().

    Args:
        syllabus: The approved syllabus dict with title, subtitle, sections, lessons.
        backgrounds: Available background image filenames.
        session_id: Session identifier for progress tracking.

    Returns:
        Complete course dict with all generated lesson content.
    """
    course_title = syllabus.get("title", "Untitled Course")
    course_subtitle = syllabus.get("subtitle", "")
    difficulty = syllabus.get("level", "Beginner")

    # Flatten lessons from sections structure (new format) or direct lessons list (old format)
    all_lessons = []
    sections = syllabus.get("sections", [])

    if sections:
        # New format: sections with nested lessons
        lesson_number = 0
        for section in sections:
            section_title = section.get("title", "Core Curriculum")
            for lesson in section.get("lessons", []):
                lesson_number += 1
                all_lessons.append({
                    "number": lesson.get("number", lesson_number),
                    "title": lesson.get("title", f"Lesson {lesson_number}"),
                    "objective": lesson.get("objective", lesson.get("title", "")),
                    "section": section_title,
                })
    else:
        # Old format: flat lessons list with section field
        for lesson in syllabus.get("lessons", []):
            all_lessons.append({
                "number": lesson.get("number", 0),
                "title": lesson.get("title", ""),
                "objective": lesson.get("objective", lesson.get("title", "")),
                "section": lesson.get("section", "Core Curriculum"),
            })

    total_lessons = len(all_lessons)
    print(f"\n{'='*60}")
    print(f"  COURSE GENERATION: {course_title}")
    print(f"  Lessons: {total_lessons} | Difficulty: {difficulty}")
    print(f"{'='*60}\n")

    # Initialize memory system
    memory = CourseMemory(course_title, difficulty)
    memory.set_total_lessons(total_lessons)

    # Update progress
    _update_progress(session_id,
        status="generating",
        current_lesson=0,
        total_lessons=total_lessons,
        current_title="Initializing...",
        percent=0,
    )

    generated_lessons = []

    for i, lesson_info in enumerate(all_lessons):
        lesson_num = i + 1
        lesson_title = lesson_info["title"]
        section_name = lesson_info["section"]

        print(f"\n  ── Lesson {lesson_num}/{total_lessons}: {lesson_title} ──")

        _update_progress(session_id,
            current_lesson=lesson_num,
            current_title=lesson_title,
            percent=round((i / total_lessons) * 100),
        )

        try:
            # Generate the lesson through the multi-stage pipeline
            lesson_data = generate_lesson(
                lesson_title=lesson_title,
                lesson_objective=lesson_info["objective"],
                lesson_number=lesson_num,
                section_name=section_name,
                course_title=course_title,
                difficulty=difficulty,
                memory_context=memory.build_context(),
                backgrounds=backgrounds,
            )

            # Quick structural validation
            structural = quick_structural_check(lesson_data.get("builder_json", []))
            if not structural["passed"]:
                for issue in structural["issues"]:
                    print(f"    [QUALITY] {issue}")

            # Record in memory for next lesson's context
            plan = lesson_data.pop("plan", {})
            memory.record_lesson(plan, lesson_data)

            generated_lessons.append(lesson_data)

        except Exception as e:
            error_str = str(e)
            print(f"    [ERROR] Failed to generate lesson: {error_str}")

            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                # Wait and retry once on rate limit
                print(f"    [RETRY] Rate limited. Waiting 30s...")
                time.sleep(30)
                try:
                    lesson_data = generate_lesson(
                        lesson_title=lesson_title,
                        lesson_objective=lesson_info["objective"],
                        lesson_number=lesson_num,
                        section_name=section_name,
                        course_title=course_title,
                        difficulty=difficulty,
                        memory_context=memory.build_context(),
                        backgrounds=backgrounds,
                    )
                    plan = lesson_data.pop("plan", {})
                    memory.record_lesson(plan, lesson_data)
                    generated_lessons.append(lesson_data)
                    continue
                except Exception as retry_err:
                    print(f"    [ERROR] Retry also failed: {retry_err}")

            # Create minimal fallback lesson
            generated_lessons.append({
                "number": lesson_num,
                "title": lesson_title,
                "summary": lesson_info["objective"],
                "section": section_name,
                "section_background": "",
                "builder_json": [
                    {"type": "heading", "data": {"text": lesson_title}},
                    {"type": "text", "data": {"text": f"This lesson covers: {lesson_info['objective']}. Content generation encountered an error — please regenerate this lesson."}},
                ],
            })

    # Update progress to complete
    _update_progress(session_id,
        status="complete",
        current_lesson=total_lessons,
        percent=100,
        current_title="Complete!",
    )

    print(f"\n{'='*60}")
    print(f"  GENERATION COMPLETE: {len(generated_lessons)}/{total_lessons} lessons")
    print(f"{'='*60}\n")

    return {
        "title": course_title,
        "subtitle": course_subtitle,
        "lessons": generated_lessons,
    }


def generate_single_lesson_task(
    session_id: str,
    course_id: int,
    lesson_id: int,
    lesson_number: int,
    lesson_title: str,
    lesson_objective: str,
    section_name: str,
    course_title: str,
    difficulty: str,
    backgrounds: list[str],
    database_module,
    normalize_builder_json_func,
    builder_json_to_html_func,
    section_id: int = None,
    app=None
) -> None:
    """
    Background task to generate a single lesson lazily.
    """
    _update_progress(session_id, status="generating", percent=10, current_title=lesson_title)

    try:
        # Use app context for database operations
        with app.app_context():
            # Reconstruct memory for this lesson
            from ai.generators.memory import CourseMemory
            memory = CourseMemory.build_from_db(course_id, lesson_number)

            # Generate content
            lesson_data = generate_lesson(
                lesson_title=lesson_title,
                lesson_objective=lesson_objective,
                lesson_number=lesson_number,
                section_name=section_name,
                course_title=course_title,
                difficulty=difficulty,
                memory_context=memory.build_context(),
                backgrounds=backgrounds,
            )

            _update_progress(session_id, percent=80)

            raw_blocks = lesson_data.get('builder_json', [])
            normalized_blocks = normalize_builder_json_func(raw_blocks)
            html_content = builder_json_to_html_func(normalized_blocks)

            # Update database
            database_module.update_lesson(
                lesson_id=lesson_id,
                number=lesson_number,
                slug=lesson_data.get("slug", f"lesson-{lesson_number}-{int(time.time())}"),
                title=lesson_data.get("title", lesson_title),
                summary=lesson_data.get("summary", lesson_objective),
                content=html_content,
                content_type="html",
                section_id=section_id,
                builder_json=json.dumps(normalized_blocks),
                plan_json=json.dumps(lesson_data.get("plan", {}))
            )

        _update_progress(session_id, status="complete", percent=100)

    except Exception as e:
        print(f"[ASYNC LESSON GEN ERROR] {e}")
        _update_progress(session_id, status="error", error=str(e))

