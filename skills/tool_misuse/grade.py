"""Grader for the tool_misuse skill."""

from aisec.grading.base import Grade, GradeContext
from aisec.grading.presets import grade_tool_injection
from aisec.schema import ModelResponse


def grade(response: ModelResponse, ctx: GradeContext) -> Grade:
    return grade_tool_injection(response, ctx)
