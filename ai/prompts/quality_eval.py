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
3. EXPLANATION_DEPTH (0-10): Are concepts explained thoroughly with WHY, not just WHAT? Is it detailed?
4. PROFESSIONALISM (0-10): Does it avoid being "childish" or patronizing while remaining simple? (10 = Simple but professional, 0 = Childish/Toy-like)
5. ENGAGEMENT (0-10): Does it feel like a mentor talking, or a boring textbook?
6. PRACTICALITY (0-10): Are code examples and concepts grounded in real-world professional development? (10 = Highly practical, 0 = Toy examples like x=5)
7. CODE_QUALITY (0-10): Are code examples practical and well-commented? Are they followed by a **Mosh-style granular breakdown** (explaining logic, re-writing the code snippet, and breaking down syntax/parameters)?
8. EDUCATIONAL_FLOW (0-10): Does it follow intuition → explanation → example → practice?
9. AI_FEELING (0-10): 10 = feels completely human-written, 0 = obvious AI slop

Return JSON:
{{
  "scores": {{
    "clarity": 0,
    "pacing": 0,
    "explanation_depth": 0,
    "professionalism": 0,
    "engagement": 0,
    "practicality": 0,
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
- overall_score = weighted average (practicality, professionalism, and ai_feeling weighted 1.5x)
- verdict = "PASS" if overall_score >= 7.0, else "NEEDS_IMPROVEMENT"
- Be genuinely critical. AI-generated content often scores too high on self-review.
- Focus weak_sections on the 2-3 worst blocks only.
"""
