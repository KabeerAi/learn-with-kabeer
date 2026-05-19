"""
Intelligent educational content chunker.

Parses transformed course JSON files and splits content into semantically
meaningful chunks that preserve educational context. Unlike naive text
splitting, this chunker understands lesson structure and groups related
components together (e.g., a heading + explanation + code example stay as
one unit).
"""

import json
import re
from typing import Any


def chunk_course(course_data: dict, source_file: str = "") -> list[dict]:
    """
    Parse a transformed course JSON and produce educational chunks.

    Each chunk contains:
      - content: the text of the chunk
      - metadata: rich educational metadata for retrieval filtering

    Returns a list of chunk dicts.
    """
    course_info = course_data.get("course", {})
    course_title = course_info.get("title", "Unknown Course")
    difficulty = course_info.get("difficulty_level", "Beginner")
    chapters = course_info.get("chapters", [])

    all_chunks = []
    global_lesson_order = 0

    for chapter in chapters:
        chapter_title = chapter.get("chapter_title", "")
        lessons = chapter.get("lessons", [])

        for lesson in lessons:
            global_lesson_order += 1
            lesson_title = lesson.get("lesson_title", "")
            components = lesson.get("components", [])

            # Chunk the lesson components intelligently
            lesson_chunks = _chunk_lesson_components(
                components=components,
                course_title=course_title,
                chapter_title=chapter_title,
                lesson_title=lesson_title,
                difficulty=difficulty,
                lesson_order=global_lesson_order,
                source_file=source_file,
            )
            all_chunks.extend(lesson_chunks)

    return all_chunks


def _chunk_lesson_components(
    components: list[dict],
    course_title: str,
    chapter_title: str,
    lesson_title: str,
    difficulty: str,
    lesson_order: int,
    source_file: str,
) -> list[dict]:
    """
    Intelligently group lesson components into chunks.

    Strategy:
      1. Standalone chunks for: analogy, exercise, recap, quiz
      2. Teaching blocks: heading + following paragraphs/code/info until
         the next heading or standalone type
    """
    chunks = []
    current_group: list[dict] = []
    standalone_types = {"analogy", "exercise", "recap", "quiz"}

    def _flush_group():
        """Convert the current group of components into a chunk."""
        nonlocal current_group
        if not current_group:
            return

        content_parts = []
        component_types = []
        topic = ""

        for comp in current_group:
            ctype = comp.get("type", "paragraph")
            ctext = comp.get("content", "")
            component_types.append(ctype)

            if ctype == "heading" and not topic:
                topic = ctext
            elif ctype == "code":
                content_parts.append(f"```\n{ctext}\n```")
            elif ctype in ("info_box", "warning_box", "note"):
                content_parts.append(f"[{ctype.upper()}] {ctext}")
            else:
                content_parts.append(ctext)

        content = "\n\n".join(content_parts)
        if not content.strip():
            current_group = []
            return

        chunk_type = _classify_chunk_type(component_types)
        teaching_style = _detect_teaching_style(current_group)

        chunks.append({
            "content": content,
            "metadata": {
                "course_title": course_title,
                "chapter_title": chapter_title,
                "lesson_title": lesson_title,
                "topic": topic or lesson_title,
                "difficulty": difficulty,
                "component_types": ",".join(component_types),
                "teaching_style": teaching_style,
                "chunk_type": chunk_type,
                "lesson_order": lesson_order,
                "source_file": source_file,
            },
        })
        current_group = []

    for comp in components:
        ctype = comp.get("type", "paragraph")

        # Standalone types get their own chunk
        if ctype in standalone_types:
            _flush_group()
            # Create standalone chunk
            ctext = comp.get("content", "")
            if ctext.strip():
                chunks.append({
                    "content": ctext,
                    "metadata": {
                        "course_title": course_title,
                        "chapter_title": chapter_title,
                        "lesson_title": lesson_title,
                        "topic": lesson_title,
                        "difficulty": difficulty,
                        "component_types": ctype,
                        "teaching_style": _detect_teaching_style([comp]),
                        "chunk_type": ctype,
                        "lesson_order": lesson_order,
                        "source_file": source_file,
                    },
                })
            continue

        # Heading starts a new group (flush previous)
        if ctype == "heading" and current_group:
            _flush_group()

        current_group.append(comp)

    # Flush remaining
    _flush_group()

    return chunks


def _classify_chunk_type(component_types: list[str]) -> str:
    """Classify what kind of educational chunk this is."""
    types_set = set(component_types)

    if "code" in types_set and len(types_set) <= 2:
        return "code_example"
    if "code" in types_set and "paragraph" in types_set:
        return "explained_code"
    if types_set & {"info_box", "warning_box", "note"}:
        return "callout"
    if "heading" in types_set and "paragraph" in types_set:
        return "explanation"
    return "explanation"


def _detect_teaching_style(components: list[dict]) -> str:
    """Detect the teaching style used in a group of components."""
    types = [c.get("type", "") for c in components]
    all_text = " ".join(c.get("content", "") for c in components).lower()

    styles = []

    if "analogy" in types:
        styles.append("analogy-driven")
    elif any(phrase in all_text for phrase in ["think of", "imagine", "like a", "just like"]):
        styles.append("analogy-driven")

    if "code" in types:
        styles.append("code-first")

    if "exercise" in types:
        styles.append("practice-oriented")

    if any(phrase in all_text for phrase in ["step 1", "step 2", "first,", "second,", "next,"]):
        styles.append("step-by-step")

    if any(phrase in all_text for phrase in ["why", "because", "the reason"]):
        styles.append("conceptual")

    return ",".join(styles) if styles else "expository"


def load_course_json(filepath: str) -> dict | None:
    """Load and validate a transformed course JSON file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "course" not in data:
            print(f"  [WARN] {filepath}: missing 'course' key, skipping.")
            return None
        return data
    except (json.JSONDecodeError, IOError) as e:
        print(f"  [ERROR] {filepath}: {e}")
        return None
