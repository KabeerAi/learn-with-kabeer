"""
Context builder for RAG-based lesson generation.

Takes retrieved educational chunks and formats them into structured
context that gets injected into generation prompts. Extracts teaching
patterns and builds a "teaching reference" section.
"""


def build_generation_context(references: dict, topic: str) -> str:
    """
    Build the RAG context block that gets injected into generation prompts.

    Args:
        references: Dict from search.search_all_references()
        topic: The lesson topic being generated

    Returns:
        Formatted context string (stays within ~4000 token budget)
    """
    sections = []

    # Teaching examples — how similar concepts are explained
    teaching = references.get("teaching_examples", [])
    if teaching:
        section = "## TEACHING REFERENCE EXAMPLES\n"
        section += "Study these examples of how similar concepts are taught. "
        section += "Mirror the explanation depth, pacing, and conversational tone — "
        section += "but generate ORIGINAL content, never copy.\n\n"
        for i, ref in enumerate(teaching[:3], 1):
            meta = ref.get("metadata", {})
            section += f"### Reference {i} (from: {meta.get('lesson_title', 'Unknown')})\n"
            section += f"Topic: {meta.get('topic', 'N/A')} | "
            section += f"Style: {meta.get('teaching_style', 'N/A')}\n"
            section += f"```\n{_truncate(ref['content'], 600)}\n```\n\n"
        sections.append(section)

    # Analogies — how similar concepts are made relatable
    analogies = references.get("analogies", [])
    if analogies:
        section = "## ANALOGY EXAMPLES\n"
        section += "These show how real-world analogies are used to explain abstract concepts. "
        section += "Create your OWN analogies inspired by these patterns.\n\n"
        for ref in analogies[:2]:
            meta = ref.get("metadata", {})
            section += f"- [{meta.get('lesson_title', '')}]: {_truncate(ref['content'], 300)}\n"
        sections.append(section)

    # Exercise patterns
    exercises = references.get("exercises", [])
    if exercises:
        section = "## EXERCISE STYLE REFERENCE\n"
        section += "These show how exercises are structured — "
        section += "practical, achievable, with clear instructions.\n\n"
        for ref in exercises[:2]:
            section += f"- {_truncate(ref['content'], 250)}\n"
        sections.append(section)

    # Code explanation patterns
    code_examples = references.get("code_examples", [])
    if code_examples:
        section = "## CODE EXPLANATION STYLE\n"
        section += "Study how code is introduced and explained — "
        section += "context first, then code, then line-by-line explanation.\n\n"
        for ref in code_examples[:2]:
            meta = ref.get("metadata", {})
            section += f"From '{meta.get('lesson_title', '')}': "
            section += f"{_truncate(ref['content'], 400)}\n\n"
        sections.append(section)

    if not sections:
        return ""

    context = "═" * 60 + "\n"
    context += "EDUCATIONAL DATASET REFERENCES (DO NOT COPY — USE AS STYLE GUIDE)\n"
    context += "═" * 60 + "\n\n"
    context += "\n".join(sections)
    context += "\n" + "═" * 60 + "\n"

    return context


def extract_teaching_patterns(references: dict) -> str:
    """
    Extract high-level teaching patterns from retrieved references.

    Returns a concise summary of patterns the AI should follow.
    """
    patterns = []

    teaching = references.get("teaching_examples", [])
    for ref in teaching:
        meta = ref.get("metadata", {})
        style = meta.get("teaching_style", "")
        components = meta.get("component_types", "")

        if "analogy-driven" in style:
            patterns.append("Uses real-world analogies to explain abstract concepts")
        if "step-by-step" in style:
            patterns.append("Breaks complex processes into numbered steps")
        if "code-first" in style:
            patterns.append("Shows code early, then explains it")
        if "conceptual" in style:
            patterns.append("Explains WHY before HOW")
        if "warning_box" in components or "info_box" in components:
            patterns.append("Highlights common mistakes and pro tips in callout boxes")
        if "exercise" in components:
            patterns.append("Ends sections with hands-on exercises")
        if "recap" in components:
            patterns.append("Includes recap summaries at key transition points")

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for p in patterns:
        if p not in seen:
            seen.add(p)
            unique.append(p)

    if not unique:
        return ""

    result = "TEACHING PATTERNS TO FOLLOW:\n"
    for p in unique[:8]:
        result += f"  • {p}\n"

    return result


def _truncate(text: str, max_chars: int) -> str:
    """Truncate text to max_chars, adding ellipsis if needed."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0] + "..."
