"""Fake-tag injection cases, loaded from payloads/injections.jsonl (family=fake_tags)."""

from aisec.skill_helpers import cases_from_payloads


def get_cases():
    return cases_from_payloads("injections", family="fake_tags")
