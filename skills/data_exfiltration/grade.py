"""Grader for the data_exfiltration skill."""

from aisec.grading.base import Grade, GradeContext
from aisec.grading.presets import grade_exfil
from aisec.schema import ModelResponse


def grade(response: ModelResponse, ctx: GradeContext) -> Grade:
    return grade_exfil(response, ctx)
