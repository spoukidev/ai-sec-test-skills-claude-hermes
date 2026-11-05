"""Grader for the adversarial_suffix skill."""

from aisec.grading.base import Grade, GradeContext
from aisec.grading.presets import grade_jailbreak
from aisec.schema import ModelResponse


def grade(response: ModelResponse, ctx: GradeContext) -> Grade:
    return grade_jailbreak(response, ctx)
