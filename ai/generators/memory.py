"""
Educational memory system.

Tracks concepts, terminology, and progression across lessons
to ensure consistency and prevent repetition within a course.
"""


class CourseMemory:
    """
    Maintains awareness of what has been taught across lessons
    in a single course generation session.
    """

    def __init__(self, course_title: str, difficulty: str):
        self.course_title = course_title
        self.difficulty = difficulty
        self.lessons_generated: list[dict] = []
        self.concepts_taught: list[str] = []
        self.terminology: set[str] = set()
        self.current_lesson_number: int = 0
        self.total_lessons: int = 0

    def set_total_lessons(self, total: int) -> None:
        self.total_lessons = total

    def record_lesson(self, lesson_plan: dict, lesson_content: dict) -> None:
        """Record a generated lesson's key info for future context."""
        self.current_lesson_number += 1

        summary = {
            "number": self.current_lesson_number,
            "title": lesson_plan.get("title", ""),
            "summary": lesson_plan.get("summary", ""),
            "key_concepts": lesson_plan.get("key_concepts", []),
            "terminology": lesson_plan.get("terminology", []),
        }
        self.lessons_generated.append(summary)

        # Track cumulative concepts
        for concept in lesson_plan.get("key_concepts", []):
            if concept not in self.concepts_taught:
                self.concepts_taught.append(concept)

        # Track terminology
        for term in lesson_plan.get("terminology", []):
            self.terminology.add(term)

    def build_context(self) -> str:
        """
        Build a memory context string for injection into generation prompts.

        This tells the AI what has already been taught so it doesn't repeat
        explanations or introduce inconsistent terminology.
        """
        if not self.lessons_generated:
            return self._build_first_lesson_context()

        lines = []
        lines.append("═" * 50)
        lines.append("LESSON MEMORY (what has already been taught)")
        lines.append("═" * 50)
        lines.append("")

        # Progress info
        lines.append(f"This is lesson {self.current_lesson_number + 1} of {self.total_lessons}.")
        progress_pct = round((self.current_lesson_number / self.total_lessons) * 100)
        lines.append(f"Course progress: {progress_pct}%")
        lines.append("")

        # Difficulty progression guidance
        if self.total_lessons > 0:
            position = self.current_lesson_number / self.total_lessons
            if position < 0.3:
                lines.append("PACING: We are EARLY in the course. Be extra gentle and thorough.")
                lines.append("Explain everything from scratch. Assume minimal knowledge.")
            elif position < 0.7:
                lines.append("PACING: We are in the MIDDLE of the course. Student has foundations.")
                lines.append("You can reference previously taught concepts without re-explaining.")
            else:
                lines.append("PACING: We are in the LATER part of the course. Student is experienced.")
                lines.append("Build on everything taught before. Introduce advanced patterns.")
        lines.append("")

        # Previous lessons summary
        lines.append("PREVIOUS LESSONS:")
        for lesson in self.lessons_generated[-5:]:  # Last 5 lessons for context
            lines.append(f"  Lesson {lesson['number']}: {lesson['title']}")
            lines.append(f"    Summary: {lesson['summary']}")
            if lesson.get("key_concepts"):
                lines.append(f"    Taught: {', '.join(lesson['key_concepts'])}")
        lines.append("")

        # Cumulative concepts
        if self.concepts_taught:
            lines.append(f"ALL CONCEPTS TAUGHT SO FAR: {', '.join(self.concepts_taught)}")
            lines.append("DO NOT re-explain these concepts. You can REFERENCE them.")
            lines.append("")

        # Terminology consistency
        if self.terminology:
            lines.append(f"ESTABLISHED TERMINOLOGY: {', '.join(sorted(self.terminology))}")
            lines.append("Use these exact terms consistently. Don't introduce synonyms.")
            lines.append("")

        return "\n".join(lines)

    def _build_first_lesson_context(self) -> str:
        """Context for the very first lesson in a course."""
        lines = []
        lines.append("═" * 50)
        lines.append("LESSON MEMORY")
        lines.append("═" * 50)
        lines.append("")
        lines.append(f"This is the FIRST lesson (1 of {self.total_lessons}).")
        lines.append("The student is brand new. Assume zero prior knowledge of this topic.")
        lines.append("Be extra welcoming, patient, and thorough in your explanations.")
        lines.append("Establish clear terminology that will be used throughout the course.")
        lines.append("")
        return "\n".join(lines)
