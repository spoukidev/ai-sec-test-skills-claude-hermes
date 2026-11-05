"""Grader for the prompt_injection_indirect skill."""

from aisec.grading.base import Grade, GradeContext
from aisec.grading.presets import grade_injection
from aisec.schema import ModelResponse


def grade(response: ModelResponse, ctx: GradeContext) -> Grade:
    return grade_injection(response, ctx)
