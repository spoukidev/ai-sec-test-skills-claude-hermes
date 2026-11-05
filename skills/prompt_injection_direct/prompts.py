"""Direct injection cases, loaded from payloads/injections.jsonl (family=direct)."""

from aisec.skill_helpers import cases_from_payloads


def get_cases():
    return cases_from_payloads("injections", family="direct")
