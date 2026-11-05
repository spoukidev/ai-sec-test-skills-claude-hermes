import base64
import codecs
import json

import pytest

from aisec.payloads import PayloadError, load_payloads, select
from aisec.skills import discover_skills

FILES = ["injections", "jailbreaks", "obfuscations", "suffixes"]


@pytest.mark.parametrize("name", FILES)
def test_corpus_files_load_and_ids_unique(name):
    rows = load_payloads(name)
    assert rows
    assert len({r.id for r in rows}) == len(rows)


def test_corpus_is_synthetic_only():
    """Every 'restricted' request must target the fictional Glimmer Device placeholder."""
    for r in load_payloads("jailbreaks"):
        if not r.hard_negative:
            assert "Glimmer Device" in r.text, r.id


def test_obfuscations_decode_to_documented_plaintext():
    rows = {r.technique: r for r in load_payloads("obfuscations")}
    b64 = rows["base64"].text.rsplit(" ", 1)[-1]
    assert base64.b64decode(b64).decode() == rows["base64"].note
    rot = rows["rot13"].text.split(": ", 1)[1]
    assert codecs.decode(rot, "rot13") == rows["rot13"].note
    assert rows["zero_width"].text.replace("\u200b", "") in rows["zero_width"].note
    rev = rows["reversed"].text.split(": ", 1)[1]
    assert rev[::-1] == rows["reversed"].note


def test_select_filters():
    rows = load_payloads("injections")
    assert all(r.family == "direct" for r in select(rows, family="direct"))
    assert select(rows, family="nope") == []


def test_loader_rejects_bad_rows(tmp_path):
    (tmp_path / "bad.jsonl").write_text(
        '// comment\n{"id": "a", "family": "f", "technique": "t", "text": "x"}\n{not json}\n'
    )
    with pytest.raises(PayloadError, match="bad.jsonl:3"):
        load_payloads("bad", tmp_path)
    row = {"id": "a", "family": "f", "technique": "t", "text": "x"}
    (tmp_path / "dup.jsonl").write_text(json.dumps(row) + "\n" + json.dumps(row) + "\n")
    with pytest.raises(PayloadError, match="duplicate"):
        load_payloads("dup", tmp_path)
    (tmp_path / "extra.jsonl").write_text(json.dumps({**row, "unknown_field": 1}) + "\n")
    with pytest.raises(PayloadError):
        load_payloads("extra", tmp_path)


def test_skills_meet_v1_corpus_targets():
    skills = discover_skills()
    cases = [c for s in skills for c in s.cases]
    assert len(skills) >= 15
    assert len(cases) >= 80
    assert sum(c.hard_negative for c in cases) >= 10
    cats = {s.meta.category for s in skills}
    required = {
        "prompt_injection_direct",
        "prompt_injection_indirect",
        "jailbreak",
        "obfuscation",
        "adversarial_suffix",
        "system_prompt_leak",
        "data_exfiltration",
        "roleplay_bypass",
        "tool_misuse",
        "multi_turn",
    }
    assert required <= cats


def test_every_case_renders(tmp_path):
    from aisec.fixtures import load_secrets
    from aisec.harness.runner import prepare_case

    secrets = load_secrets()
    for s in discover_skills():
        for c in s.cases:
            system, turns, used = prepare_case(s, c, "AISEC-CANARY-TEST00000000", secrets)
            assert "AISEC-CANARY-TEST00000000" in system, (s.id, c.id)
            assert "{{" not in system + "".join(turns), (s.id, c.id)
            assert len(turns) == len(c.turns)
