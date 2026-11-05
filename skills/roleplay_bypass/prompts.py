"""Role-play jailbreaks from payloads/jailbreaks.jsonl (family=roleplay)."""

from aisec.skill_helpers import POLICY_SYSTEM, REFUSAL_CRITERIA, cases_from_payloads


def get_cases():
    return cases_from_payloads(
        "jailbreaks",
        family="roleplay",
        system=POLICY_SYSTEM,
        extra_expect={"judge_criteria": REFUSAL_CRITERIA},
    )
