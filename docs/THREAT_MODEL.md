# Threat model

This toolkit evaluates **model-level** resistance to misuse that arrives through the model's input.
It answers: *"If an untrusted party controls some of the text this model sees, does the model keep
following its trusted instructions, keep secrets secret, and avoid unsafe actions?"*

## Assets

| Asset | Example in this repo | Measured by |
|---|---|---|
| Policy integrity | refusing build steps for the fictional *Glimmer Device* | jailbreak, roleplay, obfuscation, suffix, escalation skills |
| Instruction hierarchy | system prompt outranks user/document text | direct, fake-tag, indirect, persistence skills |
| System-prompt confidentiality | per-case canary `AISEC-CANARY-<random>` in the system prompt | `system_prompt_leak*` |
| Context secrets | fake API keys / SSN / tokens from `fixtures/canaries.txt` | `data_exfiltration*` |
| Agency / tool safety | only allowlisted tools, hosts and recipients | `tool_misuse*` |
| Usefulness | benign prompts still get answered | hard negatives in every skill + `over_refusal_benign` |

## Trust boundaries

```
 TRUSTED                              │  UNTRUSTED
 ─────────────────────────────────────┼──────────────────────────────────────────
 harness config (config/*.yaml)        │  user turns (attacker-controlled)
 system prompt (incl. canary, policy)  │  "retrieved" documents (fixtures/fake_docs)
 tool schemas + allowlists             │  pasted emails / web pages / tool output
                                       │  the model's own output (graded, never executed)
```

## Attacker

- **Capability:** arbitrary text in user messages; for indirect suites, control of retrieved
  documents or pasted tool results that the harness places in context.
- **No access** to model weights, training data, provider infrastructure, the harness config or the
  system prompt.

## Attack goals → skills

| Goal (brief §2) | Skills |
|---|---|
| (a) Jailbreak / policy bypass | `jailbreak_classic`, `jailbreak_hypothetical`, `roleplay_bypass`, `multi_turn_escalation` |
| (b) Direct & indirect prompt injection | `prompt_injection_direct`, `prompt_injection_fake_tags`, `prompt_injection_indirect`, `multi_turn_persistence` |
| (c) System-prompt leakage | `system_prompt_leak`, `system_prompt_leak_encoding` |
| (d) Data exfiltration (incl. covert channels) | `data_exfiltration`, `data_exfiltration_covert` |
| (e) Adversarial / obfuscated inputs | `jailbreak_obfuscation`, `adversarial_suffix` |
| (f) Tool misuse | `tool_misuse`, `tool_misuse_direct` (feature-flagged with `--tools` / suite `full`) |

## Out of scope

Training-time attacks and data poisoning, weight backdoors, provider account takeover, real phishing
or malware delivery, denial-of-wallet, and **any live attack on production third-party apps**.
The harness never executes tool calls and never contacts URLs that appear in model output.

## Design decisions that keep the project safe

- **Synthetic restricted topic.** Harm is modelled as violating an *operator policy* about a
  fictional item, so a failing model reveals nothing dangerous.
- **Markers & canaries.** Success of an attack is detected through unique marker tokens and random
  canaries, not by judging the harmfulness of real content.
- **Reserved domains.** All URLs use `.example` / `.invalid` (RFC 2606/6761).
- **Mock client.** CI and demos run fully offline.

## Known limitations of the model

- Results depend on the system prompt used. Our prompts are deliberately *defended*
  (they tell the model to treat documents as untrusted); an undefended production prompt will
  usually score worse.
- Real applications add their own defences (input filters, output sanitizers, CSP for images);
  this toolkit measures the model alone.
- Sampling is non-deterministic for real models even at temperature 0; repeat runs and compare.
