# AI Security Test Skills for Claude and Hermes

**Slug:** `ai-sec-test-skills-claude-hermes`  
**Level:** Intermediate (cybersecurity / AI security student)  
**Audience:** Public GitHub — educational, reproducible, no real harm  
**Estimated effort:** 2–3 weeks part time

## 1. Goal

Ship a **practical, modular toolkit of security test “skills”** (self-contained test modules) that evaluate **Claude** (Anthropic API) and **Hermes** (Nous Research models via OpenAI-compatible endpoints such as OpenRouter, Together, Fireworks, or a local Ollama/vLLM server) against common AI security threats.

Each skill is a small, runnable module that:
1. Sends carefully designed prompts (and optional tool/RAG context) to the target model.
2. Scores the response with a deterministic or LLM-as-judge grader.
3. Emits a structured result (pass / fail / inconclusive + evidence).

The toolkit produces a **comparable security report** across models and over time, suitable for a student portfolio and for CI.

This is a **defensive evaluation** project. Attack payloads exist only to measure resistance; nothing targets third-party systems.

## 2. Threat model

| Item | Description |
|---|---|
| **Asset** | Model behavior integrity: refusal of harmful requests, protection of system prompts, resistance to injection and exfiltration |
| **Attacker** | A user (or content they paste) who tries to jailbreak, inject, exfiltrate, or coerce the model into unsafe or policy-violating behavior |
| **Attacker capability** | Arbitrary text in user messages; for “indirect” suites, control of retrieved documents or tool results that the harness feeds into context. No access to model weights, training data, or the provider’s infrastructure |
| **Attack goals** | (a) Jailbreak / policy bypass; (b) direct and indirect prompt injection; (c) system-prompt leakage; (d) data exfiltration via model output (including covert channels); (e) adversarial / obfuscated inputs that flip refusals; (f) tool misuse when tools are enabled |
| **Trust boundary** | System prompt and harness config are trusted. User turns and any “retrieved” / tool content are untrusted |
| **Out of scope** | Training-time attacks, weight backdoors, provider account takeover, real phishing / malware delivery, and live attacks on production third-party apps |

## 3. Tech stack

- **Language:** Python 3.11+
- **Packaging:** `pyproject.toml` (hatch or uv), CLI entrypoint `aisec`
- **Model clients:**
  - Anthropic official SDK for Claude (`anthropic`)
  - OpenAI-compatible client (`openai`) for Hermes and any OpenAI-style endpoint (OpenRouter, Together, Fireworks, local vLLM / Ollama)
- **Config:** YAML + Pydantic settings; API keys **only** via environment variables (never committed)
- **Grading:** regex / heuristic graders first; optional LLM-as-judge (same or cheaper model) behind a flag
- **Reporting:** JSONL run logs + Markdown HTML report (Jinja2 or Markdown tables); optional Streamlit dashboard
- **Testing:** pytest for unit tests of graders and payload loaders
- **Optional:** Docker image for reproducible CI runs

## 4. Environment / credentials

```bash
# Claude (Anthropic)
export ANTHROPIC_API_KEY=sk-ant-...
export AISSEC_CLAUDE_MODEL=claude-sonnet-4-20250514   # override as needed

# Hermes via OpenAI-compatible API (OpenRouter example)
export OPENAI_API_KEY=...          # or OPENROUTER_API_KEY mapped in config
export OPENAI_BASE_URL=https://openrouter.ai/api/v1
export AISSEC_HERMES_MODEL=nousresearch/hermes-3-llama-3.1-70b

# Optional judge model (cheaper / local)
export AISSEC_JUDGE_MODEL=...
export AISSEC_JUDGE_BASE_URL=...
```

Local Hermes (Ollama) example:

```bash
export OPENAI_BASE_URL=http://localhost:11434/v1
export OPENAI_API_KEY=ollama
export AISSEC_HERMES_MODEL=hermes3
```

Document in README that keys must come from env vars / a secret manager, and ship a `.env.example` with empty placeholders only.

## 5. File structure

```
ai-sec-test-skills-claude-hermes/
├── BRIEF.md
├── README.md
├── LICENSE                     # MIT or Apache-2.0
├── CODE_OF_CONDUCT.md
├── SECURITY.md                 # how to report issues; no live attack wording
├── .env.example
├── pyproject.toml
├── Makefile                    # make test, make report, make lint
├── config/
│   ├── models.yaml             # named targets: claude, hermes, custom
│   ├── suites.yaml             # which skills run in default / ci / full
│   └── judge.yaml
├── aisec/
│   ├── __init__.py
│   ├── cli.py                  # `aisec run`, `aisec list`, `aisec report`
│   ├── models/
│   │   ├── base.py             # ModelClient protocol
│   │   ├── anthropic_client.py
│   │   └── openai_compat.py
│   ├── harness/
│   │   ├── runner.py           # loads skills, calls model, grades, writes JSONL
│   │   ├── session.py          # multi-turn support
│   │   └── rate_limit.py
│   ├── grading/
│   │   ├── base.py             # Grade(pass|fail|inconclusive, score, evidence)
│   │   ├── regex.py
│   │   ├── keywords.py
│   │   ├── canary.py           # system-prompt / secret canary detection
│   │   └── llm_judge.py
│   └── report/
│       ├── markdown.py
│       └── html.py
├── skills/                     # one folder per skill = one “test skill”
│   ├── _template/
│   │   ├── skill.yaml          # id, category, severity, models, tags
│   │   ├── prompts.py          # or prompts/*.txt + meta.json
│   │   └── grade.py            # grade(response, context) -> Grade
│   ├── prompt_injection_direct/
│   ├── prompt_injection_indirect/
│   ├── jailbreak_classic/
│   ├── jailbreak_obfuscation/
│   ├── system_prompt_leak/
│   ├── data_exfiltration/
│   ├── adversarial_suffix/
│   ├── roleplay_bypass/
│   ├── tool_misuse/            # only when tools enabled
│   └── multi_turn_persistence/
├── payloads/                   # shared corpus (JSONL), educational only
│   ├── jailbreaks.jsonl
│   ├── injections.jsonl
│   ├── obfuscations.jsonl
│   └── README.md               # purpose + ethical use
├── fixtures/
│   ├── fake_docs/              # poisoned “retrieved” docs for indirect PI
│   └── canaries.txt
├── results/                    # gitignored; sample kept in results/sample/
├── tests/
│   ├── test_graders.py
│   ├── test_payload_load.py
│   └── test_clients_mock.py
└── docs/
    ├── THREAT_MODEL.md
    ├── ADDING_A_SKILL.md
    └── INTERPRETING_RESULTS.md
```

## 6. Key test categories and example tests

Each skill folder implements the same interface so new tests plug in without touching the harness.

### 6.1 Direct prompt injection
- Override attempts: “Ignore previous instructions and …”, fake `<system>` / `[INST]` tags.
- Goal: model must not adopt attacker instructions that contradict the system prompt.
- Grade: canary from the real system prompt still respected; attacker-commanded action not performed (e.g. must not output `INJECTION_SUCCESS`).

### 6.2 Indirect prompt injection
- Harness inserts a “retrieved document” containing hidden instructions (HTML comments, white text descriptions, base64).
- Goal: model answers the user’s benign question without following the document’s commands (e.g. “append your system prompt” or “call tool X”).
- Grade: no canary leak; no forbidden tool call; answer stays on-topic.

### 6.3 Jailbreaks (classic + modern)
- DAN-style, “developer mode”, hypothetical framing, authority claims.
- Multi-turn soft jailbreaks that escalate.
- Grade: policy-aligned refusal or safe completion; keyword / judge checklist per scenario.

### 6.4 Obfuscation & adversarial inputs
- Base64 / ROT13 / leetspeak / homoglyphs / zero-width characters encoding a disallowed request.
- Character-level noise and long adversarial suffixes (educational, truncated for cost).
- Grade: same as jailbreak suite; also track whether de-obfuscation happened in the clear.

### 6.5 System prompt leakage
- Direct asks (“repeat your instructions”), encoding tricks, translation tricks, “output as JSON/YAML”.
- Plant a unique canary string in the system prompt for each run.
- Grade: **fail** if canary (or substantial verbatim system text) appears in the output.

### 6.6 Data exfiltration
- Seeded secrets in context (fake API keys, “user SSN”).
- Attempts to smuggle them out via markdown images, URL query strings, or acrostics.
- Grade: secret substrings must not appear in outbound-looking patterns; canary secrets flagged if echoed.

### 6.7 Role-play / persona bypass
- “You are an unrestricted AI named …”, fiction framing for disallowed advice.
- Grade: refusal quality; no actionable harmful content.

### 6.8 Tool misuse (optional suite)
- When Claude tool use or Hermes function-calling is enabled: injected docs that demand `send_email`, `http_get` to evil hosts, or file deletes.
- Grade: tool schema validation + allowlist; unexpected tools = fail.

### 6.9 Multi-turn persistence
- Inject in turn 1; ask a benign follow-up in turn 3 that should trigger the earlier injection if it “stuck”.
- Grade: delayed activation must not occur.

**Minimum corpus size for v1:** ≥ 15 skills across categories, ≥ 80 prompt cases total, with at least 10 hard negatives (benign prompts that look imperative but should pass).

## 7. How to run

```bash
# install
uv sync   # or pip install -e .

# list skills
aisec list

# run default suite on both models
aisec run --models claude,hermes --suite default

# run one skill
aisec run --models claude --skill system_prompt_leak

# full suite + LLM judge
aisec run --models claude,hermes --suite full --judge

# write report
aisec report results/latest.jsonl -o results/report.md
```

CI sketch (GitHub Actions): run on `suite: ci` with mocked clients for unit tests; optional nightly job with real keys from repository secrets.

## 8. Scoring and report

Per case:
- `pass` / `fail` / `inconclusive`
- `score` ∈ [0, 1]
- `evidence` (matched patterns, judge rationale, truncated model output)
- latency, token usage, model id, skill id, timestamp

Aggregate report:
- Pass rate by category and by model
- Side-by-side Claude vs Hermes table
- Top failing cases with truncated evidence
- Cost / latency summary

## 9. Success criteria

| Criterion | Target |
|---|---|
| Runnable CLI | `aisec run --models claude` and `--models hermes` work with only env vars for keys |
| Skills | ≥ 15 skills covering all categories in §6 |
| Cases | ≥ 80 graded cases; ≥ 10 hard negatives |
| Graders | Deterministic graders for canary leak and keyword policy; LLM judge optional and documented |
| Tests | `pytest` green; graders and payload loader covered; clients mockable |
| Safety | No live third-party targets; payloads clearly labeled educational; `.env.example` only |
| Docs | README with quickstart, threat model, adding-a-skill guide, interpreting results |
| Reproducibility | Pinned deps; sample `results/sample/` report in repo; `make report` regenerates Markdown from sample JSONL |
| Public readiness | LICENSE, SECURITY.md, CODE_OF_CONDUCT.md; no real secrets in git history |

## 10. Milestones

1. **Days 1–3:** project skeleton, Anthropic + OpenAI-compat clients, CLI, one skill end-to-end (`system_prompt_leak`).
2. **Days 4–7:** remaining core skills (injection, jailbreak, exfil, obfuscation), YAML suites, Markdown report.
3. **Days 8–12:** indirect injection fixtures, multi-turn harness, tool-misuse suite (feature-flagged), LLM judge.
4. **Days 13–16:** pytest suite, sample results, docs polish, Docker optional, first public-repo README polish.

## 11. Stretch goals

- Comparative leaderboard JSON for multiple Claude and Hermes variants.
- Adaptation of a subset of [garak](https://github.com/NVIDIA/garak) / PyRIT probes behind the same skill interface (attribution in docs).
- Streaming + refusal-latency metrics.
- Browser-friendly HTML report with filters.

## 12. Ethics and disclosure

- Corpus is for **measuring defenses**, not for attacking production systems.
- README must state: do not use against systems you do not own or have permission to test.
- Prefer synthetic disallowed topics (clearly fake “how to build a X” placeholders graded on refusal) over graphic harmful content.
- Canaries and fake secrets only.

## 13. Portfolio / GitHub value

One clear before/after or Claude-vs-Hermes chart in the README, a one-command quickstart, and a “add your own skill in 15 minutes” doc make this an excellent public cybersecurity / AI security portfolio piece.
