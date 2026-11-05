"""Grader for the system_prompt_leak skill."""

from aisec.grading.base import Grade, GradeContext
from aisec.grading.presets import grade_leak
from aisec.schema import ModelResponse


def grade(response: ModelResponse, ctx: GradeContext) -> Grade:
    return grade_leak(response, ctx)
