---
name: opencodex-kimi-setup
description: Safely install, migrate, configure, diagnose, and verify OpenCodex with Kimi Code models (`kimi-code/k3`, `kimi-code/k3[1m]`, `kimi-code/kimi-for-coding`) while preserving native GPT/OpenAI fallback. Use when replacing or avoiding cc-switch, adding a Kimi Code API key, fixing Clash or Clash Verge fake-IP DNS blocking `api.kimi.com`, registering K3 1M as a custom model, syncing Codex model catalogs, or recovering from broken Codex OAuth/auth after model-switcher experiments.
---

# OpenCodex Kimi Setup

## Overview

Configure OpenCodex as the local Codex provider proxy for Kimi Code without sacrificing native OpenAI/GPT rollback. Treat credentials and Codex OAuth files as protected state: inspect only shape/status, never print secrets.

## Operating rules

1. Start with read-only discovery: `ocx status`, Codex config shape, Kimi model catalog, DNS result for `api.kimi.com`, and whether cc-switch residue exists.
2. Back up before every config change. Preserve `~/.codex/config.toml`, `~/.codex/auth.json`, `~/.opencodex/config.json`, and any Clash Verge YAML touched.
3. Never write, log, commit, or echo API keys, OAuth tokens, or full `auth.json`. Use `read -s` or an existing credential manager for key entry.
4. Do not replace Codex OAuth credentials with Kimi keys. OpenAI/GPT fallback depends on the original Codex OAuth flow remaining intact.
5. Do not use `allowPrivateNetwork: true` as the normal fix for Clash fake-IP. Fix DNS/fake-IP filtering so `api.kimi.com` resolves to public IPs before OpenCodex provider policy runs.
6. Do not restart Codex Desktop, `ocx restore`, `ocx stop`, or uninstall anything unless the user explicitly accepts the interruption or rollback.
7. Prefer `kimi-code` for these model IDs: `k3`, `k3[1m]`, `kimi-for-coding`. Avoid mixing this up with the `moonshot` provider unless the user specifically has a Moonshot Platform key and wants that endpoint.

## Workflow

1. Run the diagnostic script first:

   ```bash
   python3 scripts/diagnose_opencodex_kimi.py
   ```

   Add `--provider-test` only when it is acceptable to call Kimi's provider metadata endpoint.

2. Read `references/runbook.md` for the relevant path:

   - Fresh OpenCodex + Kimi Code setup
   - cc-switch migration or cleanup
   - Clash fake-IP repair
   - K3 1M custom model registration
   - UI/CLI switching and GPT rollback
   - Troubleshooting and verification

3. Apply only the smallest necessary change, then run the diagnostic script again and capture a redacted summary.

## Required verification

Use these checks before claiming success:

- `ocx provider test kimi-code` returns connected, or the failure is clearly explained.
- `ocx models selected kimi-code` includes `k3`, `k3[1m]`, and `kimi-for-coding`.
- Codex catalog contains `kimi-code/k3`, `kimi-code/k3[1m]`, and `kimi-code/kimi-for-coding`.
- `api.kimi.com` does not resolve to `198.18.0.0/15`.
- `ocx status` shows default provider remains `openai` unless the user explicitly changed it.
- Safe rollback commands are available: `ocx restore`, `ocx restore back`, and `ocx stop`.
- No secret-like strings are present in created notes, skills, logs, or commits.

## Resource map

- `scripts/diagnose_opencodex_kimi.py`: read-only local status and catalog diagnostic; safe to share.
- `references/runbook.md`: setup, migration, fake-IP repair, K3 1M registration, usage, rollback, and troubleshooting steps.
