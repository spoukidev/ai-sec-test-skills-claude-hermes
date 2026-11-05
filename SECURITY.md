# Security Policy

## What this project is

`aisec` is a **defensive evaluation toolkit**. It sends synthetic, educational test prompts to
language models that *you* configure and grades whether the model behaved securely. It does not
contain exploits for software vulnerabilities, and it must only be pointed at models, endpoints
and deployments you own or are explicitly authorized to evaluate.

## Supported versions

| Version | Supported |
|---|---|
| 0.1.x | ✅ |

## Reporting a vulnerability in this toolkit

If you find a security issue **in this codebase** — for example a grader that can be tricked into
reporting a false PASS, a path traversal in fixture loading, accidental secret logging, or a
dependency issue — please report it privately:

1. Use GitHub's **"Report a vulnerability"** (private security advisory) on this repository, or
   contact the maintainers privately via the method listed on the repository profile.
2. Include a description, affected version/commit, reproduction steps (ideally with the offline
   `--mock` client) and the impact you expect.
3. Please do not open a public issue until a fix is available.

We aim to acknowledge reports within 7 days and to publish a fix or mitigation within 30 days
for confirmed issues.

## Findings about model behaviour

Results produced by this toolkit about a **model provider's** model (for example a jailbreak that
works on a specific model version) are not vulnerabilities in this project. Please follow the
provider's own responsible-disclosure process:

- Anthropic: see Anthropic's published responsible disclosure policy on anthropic.com.
- Nous Research / hosting providers (OpenRouter, Together, Fireworks, …): use their published
  security or abuse contact.

Share only the minimum needed to reproduce, and give providers reasonable time to respond before
publishing details.

## Secrets

- API keys are read **only** from environment variables (see `.env.example`). Never commit them.
- Everything in `fixtures/canaries.txt` and every `AISEC-CANARY-*` value is fake.
- If you accidentally commit a real key, revoke it with the provider immediately — rewriting git
  history is not enough.
