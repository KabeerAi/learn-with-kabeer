"""
Course blueprint generator.

Generates the initial course syllabus from the conversational chat.
Used by the /cod/chat endpoint.
"""

from ai.prompts.blueprint import BLUEPRINT_SYSTEM_INSTRUCTION


def get_blueprint_system_instruction() -> str:
    """Return the system instruction for the blueprint chat phase."""
    return BLUEPRINT_SYSTEM_INSTRUCTION
