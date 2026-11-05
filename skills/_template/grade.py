"""Grader for the template skill: grade(response, ctx) -> Grade."""

from aisec.grading.base import Grade, GradeContext
from aisec.grading.presets import grade_injection
from aisec.schema import ModelResponse


def grade(response: ModelResponse, ctx: GradeContext) -> Grade:
    # Use a preset, or combine primitives from aisec.grading.{regex,keywords,canary,exfil,tools}.
    return grade_injection(response, ctx)
