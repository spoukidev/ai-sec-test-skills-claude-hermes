# Contributing

Thanks for helping make LLM security testing more accessible!

1. `make install` (or `uv venv && uv pip install -e ".[dev]"`).
2. Add or change a skill — see [docs/ADDING_A_SKILL.md](docs/ADDING_A_SKILL.md).
3. `make lint test validate` must pass. Tests run fully offline with the mock client.
4. Open a pull request describing what the skill measures and how it is graded.

## Payload rules (non-negotiable)

- **Synthetic only.** "Disallowed" requests must target the fictional *Glimmer Device* (or a
  similarly fake placeholder declared restricted in the trusted system prompt), never real-world
  harmful topics.
- **Fake secrets only.** Use `{{canary}}` and `{{secret:NAME}}` from `fixtures/canaries.txt`.
- **No live third-party targets.** URLs must use reserved domains such as `*.example`,
  `*.invalid` or `localhost`.
- Paraphrase public jailbreak templates and credit the source in the payload's `source` field.
- Every new skill should include at least one **hard negative** (benign prompt that looks
  imperative) so we measure over-refusal too.
