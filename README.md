# OpenCodex Kimi Setup Skill

A Codex skill for safely configuring [OpenCodex](https://github.com/lidge-jun/opencodex) with Kimi Code models while preserving native GPT/OpenAI fallback.

It captures the failure mode where model switchers or DNS/proxy setups break Codex auth and Kimi routing:

- `cc-switch`-style tooling can overwrite Codex provider/auth state if used incorrectly.
- Clash fake-IP DNS can make `api.kimi.com` resolve to `198.18.0.0/15`, causing OpenCodex destination-policy failures before the outbound proxy is used.
- Kimi Code live discovery can omit `k3[1m]`, so OpenCodex may need a custom model registration.

The skill is designed for agents and humans who need a repeatable, auditable setup path.

## Platforms

Validated on macOS and Windows. Windows setup includes a non-ASCII account ACL workaround and Task Scheduler persistence notes; Codex Desktop `502`/`426` compatibility has a proxy-side WebSocket opt-in documented in the runbook.

## What it supports

- Kimi Code API key setup without printing secrets.
- OpenCodex model selection for:
  - `kimi-code/k3`
  - `kimi-code/k3[1m]`
  - `kimi-code/kimi-for-coding`
- DeepSeek (`deepseek-v4-flash` / `deepseek-v4-pro`) as a manual picker entry and as a combo failover target, including its tool-schema `type: null` 400 fix (upstream PR #933) and its throughput/effort caveats.
- Combo failover chains (Kimi → DeepSeek → native OpenAI) with alias-matching and live-discovery rules.
- Quota semantics (`ocx provider quota` reports used percentages) and route switching (`ocx restore` / `restore back` vs `codexAutoStart` re-injection).
- Clash / Clash Verge Rev fake-IP repair for `api.kimi.com`.
- Manual K3 1M custom model registration.
- K3, K3 1M, and kimi-for-coding image-input catalog metadata (`text,image`).
- Runtime model-identity checks that distinguish Kimi provider, upstream wire model ID, and local selector.
- Codex 0.146 bounded Luna worker-role guidance using `developer_instructions`.
- Codex Desktop and CLI switching guidance.
- Windows non-ASCII account ACL compatibility with ASCII `OPENCODEX_HOME`, process-scoped SID identity, and Task Scheduler service guidance.
- Codex Desktop `502`/`426` Responses transport repair through OpenCodex `websockets: true`.
- GPT/OpenAI rollback with `ocx restore`, `ocx restore back`, and `ocx stop`.
- Read-only diagnostics that redact secret-like output.

## Install

Copy the skill into your Codex skills directory:

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
cp -R skills/opencodex-kimi-setup "${CODEX_HOME:-$HOME/.codex}/skills/"
```

Restart Codex so it discovers the skill.

Then invoke it with:

```text
Use $opencodex-kimi-setup to configure OpenCodex with Kimi Code and keep GPT fallback.
```

## Run diagnostics

From the repository root:

```bash
python3 skills/opencodex-kimi-setup/scripts/diagnose_opencodex_kimi.py
```

Optionally call Kimi provider metadata:

```bash
python3 skills/opencodex-kimi-setup/scripts/diagnose_opencodex_kimi.py --provider-test
```

The default diagnostic is strict read-only: it does not start `ocx` or `codex`, and it does not print API keys or OAuth token values. After backing up the relevant configuration and knowingly accepting the OpenCodex CLI side effect risk, explicitly request status/model inspection with:

```bash
python3 skills/opencodex-kimi-setup/scripts/diagnose_opencodex_kimi.py --ocx-cli
```

The default report includes `codex_catalog.model_modalities` for `kimi-code/k3`, `kimi-code/k3[1m]`, and `kimi-code/kimi-for-coding`. Each must be `text,image` and `image_capable: true`; a K3 1M custom entry with only `text` needs the runbook's minimal registration repair before any paid image test.

It also checks the running proxy at `GET /v1/models?client_version=diagnostic`. If the disk catalog is correct but `runtime_catalog.status` is `stale_runtime_metadata`, the proxy process has an old in-memory model catalog; refresh the proxy and rerun the check. The plain OpenAI-shaped `/v1/models` response is an availability list and may omit capability metadata, so do not use it to decide image support.

The runbook also documents how to verify model self-identification without conflating the local selector (such as `k3[1m]`) with the upstream wire model (such as `k3`), and the Codex 0.146 `developer_instructions` schema for the bounded `gpt-5.6-luna` worker role.

## Safety boundaries

- Do not paste API keys into prompts, notes, commits, shell history, or issue comments.
- Do not replace `~/.codex/auth.json` with a provider API key.
- Back up `~/.codex/config.toml`, `~/.codex/auth.json`, `~/.opencodex/config.json`, and touched Clash YAML files before changes.
- Do not use `allowPrivateNetwork: true` as the default fake-IP workaround.
- Do not restart Codex Desktop, `ocx restore`, or `ocx stop` unless the user accepts the interruption.

## Repository layout

```text
skills/opencodex-kimi-setup/
├── SKILL.md
├── agents/openai.yaml
├── references/runbook.md
└── scripts/diagnose_opencodex_kimi.py
```

## Validate

If you have Codex's skill validation script locally:

```bash
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/opencodex-kimi-setup
python3 -B -c 'from pathlib import Path; p=Path("skills/opencodex-kimi-setup/scripts/diagnose_opencodex_kimi.py"); compile(p.read_bytes(), str(p), "exec")'
```

## License

MIT
