import json

from aisec.cli import load_dotenv, main
from aisec.config import load_config
from aisec.harness.rate_limit import RateLimiter, is_retryable, with_retries
from aisec.harness.runner import Runner, RunOptions
from aisec.harness.session import Session
from aisec.models.mock import MockClient
from aisec.report.aggregate import load_records, summarize
from aisec.report.html import render_html
from aisec.report.markdown import render_markdown
from aisec.schema import Message
from aisec.skills import discover_skills


def test_session_alternates_roles_and_records_tool_calls():
    m = MockClient(comply_rate=1.0, vague_rate=0.0)
    from aisec.tool_catalog import get_tools

    s = Session(m, "sys", get_tools(["send_email"]), meta={"case_id": "x"})
    s.run(["call send_email please", "and again"])
    roles = [h.role for h in s.history]
    assert roles == ["user", "assistant", "user", "assistant"]
    assert "[requested tool calls: send_email" in s.history[1].content
    assert len(m.calls) == 2 and len(m.calls[1]["messages"]) == 3


def test_rate_limiter_spaces_calls():
    t = [0.0]
    slept = []
    rl = RateLimiter(60, clock=lambda: t[0], sleep=lambda d: slept.append(d))
    rl.wait()
    rl.wait()
    assert slept == [1.0]
    assert RateLimiter(0).wait() == 0.0


def test_with_retries():
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("429 rate_limit")
        return "ok"

    assert with_retries(flaky, retries=3, sleep=lambda _d: None) == "ok"
    assert is_retryable(RuntimeError("Overloaded")) and not is_retryable(ValueError("bad request"))


def test_runner_end_to_end_with_mock(tmp_path):
    cfg = load_config()
    opts = RunOptions(targets=["claude", "hermes"], suite="full", mock=True, judge=True, output_dir=tmp_path)
    result = Runner(cfg, discover_skills(), opts).run()
    n_cases = sum(len(s.cases) for s in discover_skills())
    assert len(result.records) == 2 * n_cases
    lines = (tmp_path / "latest.jsonl").read_text().splitlines()
    assert len(lines) == 2 * n_cases
    rec = json.loads(lines[0])
    assert {
        "verdict",
        "score",
        "evidence",
        "latency_ms",
        "input_tokens",
        "model_id",
        "skill_id",
        "timestamp",
    } <= set(rec)
    verdicts = {r.verdict for r in result.records}
    assert "pass" in verdicts and "fail" in verdicts
    assert all(r.mock for r in result.records)


def test_suite_filters_tools_and_ci_limits(tmp_path):
    cfg = load_config()
    skills = discover_skills()
    r = Runner(cfg, skills, RunOptions(targets=["claude"], suite="default", mock=True, output_dir=tmp_path))
    assert not any(s.meta.requires_tools for s in r.skills)
    r = Runner(cfg, skills, RunOptions(targets=["claude"], suite="ci", mock=True, output_dir=tmp_path))
    res = r.run()
    assert len(res.records) == sum(min(3, len(s.cases)) for s in skills)


def test_report_markdown_and_html(tmp_path):
    cfg = load_config()
    Runner(
        cfg,
        discover_skills(),
        RunOptions(targets=["claude", "hermes"], suite="ci", mock=True, output_dir=tmp_path),
    ).run()
    s = summarize(load_records(tmp_path / "latest.jsonl"))
    md = render_markdown(s)
    assert "SYNTHETIC DATA" in md and "Pass rate by category" in md and "| `claude` |" in md
    html = render_html(s)
    assert "<svg" in html and 'id="cases"' in html


def test_cli_list_run_report(tmp_path, capsys):
    assert main(["list"]) == 0
    out = capsys.readouterr().out
    assert "system_prompt_leak" in out and "hard negatives" in out
    assert main(["run", "--models", "claude,hermes", "--suite", "ci", "--mock", "-o", str(tmp_path)]) == 0
    md = tmp_path / "r.md"
    html = tmp_path / "r.html"
    assert main(["report", str(tmp_path / "latest.jsonl"), "-o", str(md), "--html", str(html)]) == 0
    assert md.read_text().startswith("# AI Security Test Report")
    assert html.exists()
    assert main(["validate"]) == 0


def test_cli_run_without_keys_fails_cleanly(tmp_path, capsys):
    assert main(["run", "--models", "claude", "--skill", "system_prompt_leak", "-o", str(tmp_path)]) == 2
    assert "ANTHROPIC_API_KEY" in capsys.readouterr().err


def test_cli_unknown_target_and_skill(tmp_path):
    assert main(["run", "--models", "nope", "--mock", "-o", str(tmp_path)]) == 2
    assert main(["run", "--models", "claude", "--skill", "nope", "--mock", "-o", str(tmp_path)]) == 2


def test_dotenv_does_not_override(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("# c\nAISEC_T1=from_file\nexport AISEC_T2='quoted'\nAISEC_T3=\n")
    monkeypatch.setenv("AISEC_T1", "from_env")
    monkeypatch.delenv("AISEC_T2", raising=False)
    assert load_dotenv(env) == 1
    import os

    assert os.environ["AISEC_T1"] == "from_env" and os.environ["AISEC_T2"] == "quoted"
    monkeypatch.delenv("AISEC_T2")


def test_message_model():
    assert Message(role="user", content="x").role == "user"
