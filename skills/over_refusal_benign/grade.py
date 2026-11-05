"""Grader for the over_refusal_benign skill."""

from aisec.grading.base import Grade, GradeContext
from aisec.grading.presets import grade_hard_negative
from aisec.schema import ModelResponse


def grade(response: ModelResponse, ctx: GradeContext) -> Grade:
    return grade_hard_negative(response, ctx)
