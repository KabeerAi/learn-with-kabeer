"""
Prompt template for quality evaluation of generated lessons.

The validator acts as an educational quality auditor, scoring
generated content across multiple dimensions.
"""


def build_quality_eval_prompt(lesson_json: str, lesson_title: str, difficulty: str) -> str:
    """Build prompt for evaluating lesson quality."""

    return f"""You are an expert educational content reviewer. Evaluate this generated programming lesson for quality.

LESSON TITLE: {lesson_title}
TARGET DIFFICULTY: {difficulty}

LESSON CONTENT (builder_json):
{lesson_json}

Score each dimension from 0 to 10 and provide specific feedback:

1. CLARITY (0-10): Is the explanation easy to understand? Are concepts introduced clearly?
2. PACING (0-10): Does the lesson build up gradually? Or does it dump information?
3. EXPLANATION_DEPTH (0-10): Are concepts explained thoroughly with WHY, not just WHAT?
4. ENGAGEMENT (0-10): Does it feel like a mentor talking, or a boring textbook?
5. BEGINNER_FRIENDLINESS (0-10): Would a complete beginner understand this?
6. CODE_QUALITY (0-10): Are code examples practical, well-commented, and explained after?
7. EDUCATIONAL_FLOW (0-10): Does it follow intuition → explanation → example → practice?
8. AI_FEELING (0-10): 10 = feels completely human-written, 0 = obvious AI slop

Return JSON:
{{
  "scores": {{
    "clarity": 0,
    "pacing": 0,
    "explanation_depth": 0,
    "engagement": 0,
    "beginner_friendliness": 0,
    "code_quality": 0,
    "educational_flow": 0,
    "ai_feeling": 0
  }},
  "overall_score": 0.0,
  "verdict": "PASS or NEEDS_IMPROVEMENT",
  "weak_sections": [
    {{
      "block_index": 0,
      "issue": "Description of what's wrong",
      "suggestion": "How to fix it"
    }}
  ],
  "summary": "One paragraph overall assessment"
}}

SCORING GUIDE:
- overall_score = weighted average (engagement and ai_feeling weighted 1.5x)
- verdict = "PASS" if overall_score >= 6.5, else "NEEDS_IMPROVEMENT"
- Be genuinely critical. AI-generated content often scores too high on self-review.
- Focus weak_sections on the 2-3 worst blocks only.
"""
