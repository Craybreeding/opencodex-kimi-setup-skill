---
name: opencodex-kimi-setup
description: Safely install, migrate, configure, diagnose, and verify OpenCodex with Kimi Code models (`kimi-code/k3`, `kimi-code/k3[1m]`, `kimi-code/kimi-for-coding`) while preserving native GPT/OpenAI fallback, plus DeepSeek as a manual-switch and failover provider. Use when replacing or avoiding cc-switch, adding a Kimi Code API key, fixing Clash or Clash Verge fake-IP DNS blocking `api.kimi.com`/`api.moonshot.cn`, registering K3 1M as a custom model, building combo failover chains (Kimi → DeepSeek → OpenAI), interpreting `ocx provider quota` percentages, fixing DeepSeek tool-schema 400s (`type: null`), or recovering from broken Codex OAuth/auth after model-switcher experiments.
---

# OpenCodex Kimi Setup

## Overview

Configure OpenCodex as the local Codex provider proxy for Kimi Code without sacrificing native OpenAI/GPT rollback. Treat credentials and Codex OAuth files as protected state: inspect only shape/status, never print secrets.

## Operating rules

1. Start with strict read-only discovery: the default diagnostic reads file shape and DNS only; it does not start `ocx` or `codex`. Run `ocx status` or model selection only with `--ocx-cli`, after backing up affected config and acknowledging that some OpenCodex versions can rewrite Codex state.
2. Back up before every config change. Preserve `~/.codex/config.toml`, `~/.codex/auth.json`, `~/.opencodex/config.json`, and any Clash Verge YAML touched.
3. Never write, log, commit, or echo API keys, OAuth tokens, or full `auth.json`. Use `read -s` or an existing credential manager for key entry.
4. Do not replace Codex OAuth credentials with Kimi keys. OpenAI/GPT fallback depends on the original Codex OAuth flow remaining intact.
5. Do not use `allowPrivateNetwork: true` as the normal fix for Clash fake-IP. Fix DNS/fake-IP filtering so `api.kimi.com` resolves to public IPs before OpenCodex provider policy runs.
6. Do not restart Codex Desktop, `ocx restore`, `ocx stop`, or uninstall anything unless the user explicitly accepts the interruption or rollback.
7. Prefer `kimi-code` for these model IDs: `k3`, `k3[1m]`, `kimi-for-coding`. Avoid mixing this up with the `moonshot` provider unless the user specifically has a Moonshot Platform key and wants that endpoint.
8. Treat `kimi-code/k3`, `kimi-code/k3[1m]`, and `kimi-code/kimi-for-coding` as image-capable catalog entries: their `input_modalities` must be `text,image`. A K3 1M custom entry marked only `text` gates image input even if the provider supports it.
9. Treat the running proxy catalog as a separate source of truth: verify `GET /v1/models?client_version=...`, not only `~/.codex/opencodex-catalog.json`. A custom-model edit can update disk state while an already-running proxy keeps stale in-memory modalities; if runtime K3 1M is still `text`, refresh the proxy before testing images.
10. For model self-identification, record the final-route provider, upstream wire model ID, and local selector separately. Do not hard-code the default or expose credentials; a bracketed local selector can map to a different wire ID.
11. For a Codex 0.146 custom agent role, use `developer_instructions` (not `instructions`). A bounded Luna worker must preserve workspace changes, stay within its assigned execution scope, and never replace primary-agent decisions or change the default subagent model.
12. A Codex Desktop or installation-feedback failure at `http://127.0.0.1:10100/v1/responses` with HTTP 502 can be a Desktop realtime/WebSocket-to-proxy compatibility issue. If `ocx provider test kimi-code` is connected and CLI HTTP requests work, do not ask the user to re-enter their Kimi Code key; restore native Codex with `ocx restore` after the required backup, while leaving OpenCodex running. For a connect-time `426 Upgrade Required` from `ws://127.0.0.1:10100/v1/responses` with no successful fallback, first check whether OpenCodex has `websockets: true`; Codex clients that do not implement the 426-to-HTTP fallback need that proxy-side opt-in.
13. On Windows, OpenCodex ACL hardening can fail for non-ASCII user accounts or paths. Use an ASCII `OPENCODEX_HOME` and process-scoped `USERDOMAIN=` plus `USERNAME=*<current-user-SID>`; add the same environment lines to a generated Task Scheduler wrapper before testing autostart. Never bypass the ACL protection by storing keys in an unhardened config.
14. Changing the model picker is not changing the route. A 403 from `127.0.0.1:10100/v1/responses` while a native model (for example `gpt-5.6-luna`) is selected means `openai_base_url` still points at the proxy. Use `ocx restore` to leave the proxy route and `ocx restore back` to return. With `codexAutoStart: true` (the default), OpenCodex re-injects `openai_base_url` and `model_catalog_json` into `~/.codex/config.toml` when Codex launches, so a manual `ocx restore` silently reverts on the next Codex start; check the file, not the picker. Running Codex threads keep the route they started with; only new threads pick up a switch.
15. `ocx provider quota --json` percentages are **used**, not remaining. Kimi Code exposes a 5-hour window and a weekly window; the "usage limit for this billing cycle" 403 (`access_terminated_error`) is typically the 5-hour window, which resets on its own.
16. Combo failover only triggers when the requested model ID exactly matches the combo alias. Aliases allow only letters, numbers, dot, underscore, hyphen, and at most one `/` — so a `k3[1m]` custom entry can never be its own alias; create a separate alias such as `kimi-code/k3-1m`. Combo members are resolved from live-discovered models only: custom models merge later, so a combo whose member is a custom model is omitted from the catalog as "member capabilities are incomplete" until the provider uses static discovery (`ocx provider edit kimi-code --live-models off`). Quota-exhaustion 403 and 502/429/5xx hop to the next target; 400-class validation errors do not.
17. DeepSeek (`api.deepseek.com`) strictly validates function schemas and rejects Codex tools whose `type` is `null` (root or nested), returning `Provider error 400: Invalid schema for function 'codex_app__automation_update'` on every turn, which looks like a hang. Fixed upstream by opencodex PR #933; for 2.10.0 and earlier, apply the local `openai-chat.ts` patch from the runbook and re-check after every `ocx update`. DeepSeek models are text-only (no vision) and slow (~50-100 output tok/s with heavy reasoning); keep effort at the default/high and prefer them as failover targets or bounded small tasks, not as the daily driver. `deepseek-v4-flash` generates very long reasoning traces (several thousand tokens) before answering.
18. Keep the `moonshot` provider (Moonshot Open Platform, pay-per-token balance) distinct from `kimi-code` (Kimi Code subscription quota). Prefer `https://api.moonshot.ai/v1` over `api.moonshot.cn`: the `.cn` hostname can resolve to Clash fake-IP (`198.18.0.0/15`) and be blocked by destination policy even with `allowPrivateNetwork` on, while `.ai` resolves publicly. Do not add provider hosts to `NO_PROXY` to work around fake-IP.

## Workflow

1. Run the diagnostic script first:

   ```bash
   python3 scripts/diagnose_opencodex_kimi.py
   ```

   Add `--provider-test` only when it is acceptable to call Kimi's provider metadata endpoint. Add `--ocx-cli` only after the relevant backup to run `ocx status` and model selection; neither flag is part of the strict default.

2. Read `references/runbook.md` for the relevant path:

   - **Get a Kimi Code API Key (Token)** before a fresh OpenCodex setup: where to create it, what to copy, and the `kimi-code` provider to use
   - Fresh OpenCodex + Kimi Code setup
   - cc-switch migration or cleanup
   - Clash fake-IP repair
   - K3 1M custom model registration
   - Kimi catalog image modalities, runtime catalog refresh, model-identity verification, and Codex 0.146 agent roles
   - UI/CLI switching and GPT rollback
   - Desktop `502` troubleshooting and verification
   - DeepSeek provider setup, combo failover chains, quota semantics, and the DeepSeek tool-schema 400 patch

3. Apply only the smallest necessary change, then run the diagnostic script again and capture a redacted summary.

## Required verification

Use these checks before claiming success:

- `ocx provider test kimi-code` returns connected, or the failure is clearly explained.
- `ocx models selected kimi-code` includes `k3`, `k3[1m]`, and `kimi-for-coding`.
- Only while Codex is routed through OpenCodex (for example, after `ocx restore back`), its catalog contains `kimi-code/k3`, `kimi-code/k3[1m]`, and `kimi-code/kimi-for-coding`. Native Codex after `ocx restore` can intentionally omit them; use `ocx opencode` for Kimi unless the user explicitly switches back.
- The diagnostic's structured `codex_catalog.model_modalities` reports every target's `input_modalities` and `image_capable`; repair a K3 1M custom entry that reports only `text` before testing image input.
- The diagnostic's `runtime_catalog.model_modalities` also reports the live proxy response. If it is `stale_runtime_metadata` while the disk catalog is correct, refresh/restart only the OpenCodex proxy after the required interruption approval, then recheck before touching Codex Desktop.
- `api.kimi.com` resolves only to public IPs; `198.18.0.0/15`, `fdfe:dcba:9876::/48`, IPv6 ULA, private, loopback, or other non-global answers are all blockers for OpenCodex provider destination checks.
- `ocx status` shows default provider remains `openai` unless the user explicitly changed it.
- Safe rollback commands are available: `ocx restore`, `ocx restore back`, and `ocx stop`.
- If combo failover is configured, `ocx combo list` shows the alias, the alias appears in the routed catalog after `ocx sync`, and a real request through the alias returns `status: completed` from the first target.
- If DeepSeek is enabled, `ocx provider test deepseek` returns connected, and a tool-bearing request (a function whose `parameters` root `type` is `null`) completes without a schema 400.
- When Desktop reports a `127.0.0.1:10100/v1/responses` 502, run `python3 scripts/diagnose_opencodex_kimi.py --responses-canary --responses-model gpt-5.5`; native `codex exec -s read-only -m gpt-5.5` should work after `ocx restore`, and the OpenCodex proxy should remain available for `ocx opencode` or a deliberate `ocx restore back` switch.
- No secret-like strings are present in created notes, skills, logs, or commits.

## Resource map

- `scripts/diagnose_opencodex_kimi.py`: strict read-only default diagnostic; `--ocx-cli`, `--provider-test`, and `--responses-canary` are explicit opt-ins.
- `references/runbook.md`: **Kimi Code API Key (Token) application and safe entry**, setup, migration, fake-IP repair, K3 1M registration, usage, rollback, and troubleshooting steps.
