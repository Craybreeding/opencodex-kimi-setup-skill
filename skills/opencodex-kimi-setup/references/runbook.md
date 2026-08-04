# OpenCodex + Kimi Code runbook

Use this when a user wants Codex to call Kimi Code models through OpenCodex while keeping GPT/OpenAI available.

## Model IDs

Prefer the `kimi-code` provider:

- `kimi-code/k3`
- `kimi-code/k3[1m]`
- `kimi-code/kimi-for-coding`

`k3[1m]` may need manual custom registration because live discovery can omit it even when the provider is reachable. Registration does not prove the account has 1M entitlement; the first real model request confirms that.

All three Kimi Code catalog entries must advertise `input_modalities` as `text,image`:

- `kimi-code/k3`
- `kimi-code/k3[1m]`
- `kimi-code/kimi-for-coding`

If K3 1M is present but only advertises `text`, image UI/input gating is wrong even though the provider can accept images. Repair the custom entry metadata before making a paid image request.

## Preflight

Run from the skill folder:

```bash
python3 scripts/diagnose_opencodex_kimi.py
```

The default is strict read-only: it does not start `ocx` or `codex`. To inspect
OpenCodex status and selected models, first back up the affected config and
then explicitly opt in:

```bash
python3 scripts/diagnose_opencodex_kimi.py --ocx-cli
```

Optionally include provider metadata call:

```bash
python3 scripts/diagnose_opencodex_kimi.py --provider-test
```

`--provider-test` runs only the provider test; it does not imply `--ocx-cli`.

Red flags:

- `api.kimi.com` resolves to `198.18.x.x`, `fdfe:dcba:9876::/48`, IPv6 ULA, private, loopback, or any other non-global IP: Clash fake-IP is still visible to OpenCodex.
- SSH or LaunchAgent diagnostics report no `ocx`/`codex` even though an interactive terminal has them. Non-interactive macOS SSH can have `PATH=/usr/bin:/bin:/usr/sbin:/sbin`; check common locations such as `~/.local/share/npm-global/bin/ocx`, `~/.local/share/npm-global/bin/codex`, `/opt/homebrew/bin/ocx`, and `/opt/homebrew/bin/codex`.
- `~/.codex/auth.json` is very small or shaped like one API key: Codex OAuth may have been overwritten.
- `ocx status` cannot find a running proxy when Codex config points to `127.0.0.1:10100`.
- While Codex is routed through OpenCodex (after `ocx restore back`), its catalog lacks the three `kimi-code/...` model IDs after `ocx sync`.

Run a real Responses-path canary only when the user accepts a paid model call:

```bash
python3 scripts/diagnose_opencodex_kimi.py --responses-canary --responses-model gpt-5.5
```

This checks the same Codex `/v1/responses` path that Desktop uses and can expose `401`/`502` failures that `ocx provider test kimi-code` does not cover. Interpret the canary by final status first: `result.ok=true` and the expected final text means the path recovered. A stderr warning like `HTTP error: 426 Upgrade Required` on `ws://127.0.0.1:10100/v1/responses` can appear during WebSocket probing and is not fatal if the canary still returns the expected answer. A `502 Bad Gateway` or `401` with `result.ok=false` is a blocker.

## Backups before changes

Use explicit paths. Do not rely on `~` inside destructive or copy commands when giving instructions to another agent.

```bash
backup_dir="${HOME}/.opencodex/backups/$(date +%Y%m%d-%H%M%S)-kimi-setup"
mkdir -p "$backup_dir"
cp "$HOME/.codex/config.toml" "$backup_dir/config.toml" 2>/dev/null || true
cp "$HOME/.codex/auth.json" "$backup_dir/auth.json" 2>/dev/null || true
cp "$HOME/.opencodex/config.json" "$backup_dir/opencodex-config.json" 2>/dev/null || true
```

For Clash Verge Rev on macOS, backup the active support directory before editing YAML:

```bash
clash_dir="$HOME/Library/Application Support/io.github.clash-verge-rev.clash-verge-rev"
backup_dir="$clash_dir/ops-backups/$(date +%Y%m%d-%H%M%S)-kimi-fakeip"
mkdir -p "$backup_dir"
cp "$clash_dir/dns_config.yaml" "$backup_dir/" 2>/dev/null || true
cp "$clash_dir/clash-verge.yaml" "$backup_dir/" 2>/dev/null || true
cp "$clash_dir/clash-verge-check.yaml" "$backup_dir/" 2>/dev/null || true
```

## Get the correct Kimi Code API Key (Token)

Use this path before configuring OpenCodex:

1. Sign in to the [Kimi Code Console](https://www.kimi.com/code/console) with the Kimi account that has the intended Kimi Code membership/entitlement.
2. Create an **API Key** in that console.
3. Copy the API Key value shown immediately after creation. The console shows each key only once; if it is lost, revoke it and create a replacement instead of trying to recover it from logs or configuration files.
4. Enter that value for OpenCodex provider **`kimi-code`**. It authenticates the Coding API at `https://api.kimi.com/coding/v1` and the models `kimi-code/k3`, `kimi-code/k3[1m]`, and `kimi-code/kimi-for-coding`.

Do **not** put any of the following in the `kimi-code` key prompt:

- Your Kimi account password or a browser/session login credential.
- The Base URL (`https://api.kimi.com/coding/v1`); it is an endpoint, not a secret.
- A Moonshot/Kimi Open Platform API Key (often called a Moonshot Platform Key). It belongs to the `moonshot` provider and is not interchangeable with a Kimi Code API Key.
- Any Codex OAuth data from `~/.codex/auth.json`. Never replace that file or paste its contents into OpenCodex.

OpenCodex manages its provider configuration, including the `kimi-code` credential, in `~/.opencodex/config.json`. Keep that file private and do not manually paste a key into a command, document, shell history, git repository, or chat. `~/.codex/auth.json` is the separate native Codex OAuth credential store and must remain untouched.

## Add the Kimi Code key safely

After obtaining the Kimi Code API Key above, never paste it into the prompt, command history, notes, or git. Use silent input and let OpenCodex write its managed configuration:

```bash
read -s KIMI_CODE_KEY
printf '%s\n' "$KIMI_CODE_KEY" | ocx account add-key kimi-code --label "Kimi Code"
unset KIMI_CODE_KEY
```

Then enable and select the desired visible models:

```bash
ocx models enable 'kimi-code/k3'
ocx models enable 'kimi-code/k3[1m]'
ocx models enable 'kimi-code/kimi-for-coding'
ocx models selected kimi-code --set 'k3,k3[1m],kimi-for-coding'
ocx sync
```

If the installed OpenCodex version exposes different subcommands, inspect `ocx models enable 2>&1` and `ocx models selected kimi-code --help`. Keep the target model IDs unchanged.

## Register K3 1M when discovery omits it

If `ocx provider test kimi-code` is connected but the OpenCodex-routed catalog lacks `kimi-code/k3[1m]`, add a custom model:

```bash
ocx models add kimi-code 'k3[1m]' \
  --display-name 'Kimi K3 1M' \
  --context-window 1000000 \
  --modalities text,image
ocx sync
```

Verify:

```bash
ocx models list-custom
ocx models selected kimi-code
python3 scripts/diagnose_opencodex_kimi.py
```

If an existing custom entry is incorrectly registered as text-only, back up configuration first, then remove only that exact provider/model target and re-add it with `text,image`:

```bash
ocx models remove 'kimi-code/k3[1m]' --yes
ocx models add kimi-code 'k3[1m]' \
  --display-name 'Kimi K3 1M' \
  --context-window 1000000 \
  --modalities text,image
```

Do not re-register `kimi-code/k3` or `kimi-code/kimi-for-coding` when their catalog entries already advertise `text,image`.

## Static catalog versus running proxy catalog

OpenCodex has two relevant model views:

1. `~/.codex/opencodex-catalog.json` is the on-disk Codex catalog.
2. `GET http://127.0.0.1:10100/v1/models?client_version=...` is the catalog currently served by the running proxy to Codex.

The plain `GET /v1/models` OpenAI availability list may omit `input_modalities`; use the `client_version` query when checking image gating. After `ocx models add`, remove/re-add, or a config edit, the disk file can show `text,image` while an already-running proxy still serves an older in-memory row such as `Kimi K3 1M -> text`. That is the specific failure mode behind “the model is visible but image input is rejected.”

Check both views without printing credentials:

```bash
python3 scripts/diagnose_opencodex_kimi.py
curl -fsS 'http://127.0.0.1:10100/v1/models?client_version=diagnostic' \
  | python3 -c 'import json,sys; d=json.load(sys.stdin); wanted={"kimi-code/k3","kimi-code/k3[1m]","kimi-code/kimi-for-coding"}; print([(m.get("slug"),m.get("input_modalities")) for m in d.get("models",[]) if m.get("slug") in wanted])'
```

If the disk view is correct but the runtime view reports `k3[1m]` as `text` or omits it, back up the affected config and refresh only the OpenCodex proxy using the installed command (`ocx restart`, or the service's equivalent). This briefly interrupts the proxy but does not require restarting Codex Desktop. Re-run the `client_version` check and `ocx sync`; accept any Desktop restart separately because it interrupts the active session. Do not treat `ocx models list-custom` alone as proof that the running process has reloaded the metadata.

## Verify runtime model identity

When a Kimi-backed session is asked which model it is, verify a real response distinguishes three dynamic values rather than treating the local selector as an upstream ID:

- provider: `kimi-code`
- upstream wire model ID: for example `k3` when the local selector is `k3[1m]` and the provider strips the bracket suffix
- local selector: for example `k3[1m]`

The identity context must be derived from the final routed provider/model for that request, not hard-coded to the default. Never include an API key, OAuth token, or full config in this context or in test output. A real model call can be billable; obtain explicit approval before making it.

## Codex 0.146 custom agent role

Codex 0.146 role files require `developer_instructions`; `instructions` is rejected. For a bounded Luna execution worker, create `~/.codex/agents/luna-worker.toml` only after backing up existing agent files:

```toml
name = "luna_worker"
model = "gpt-5.6-luna"
model_reasoning_effort = "max"
description = "Executes bounded, independently completable implementation tasks under a primary agent."
developer_instructions = "Accept only clear, independently completable execution tasks. Preserve existing workspace changes. Do not alter overall goals, make primary-agent decisions, widen scope, or overwrite unrelated configuration. When images are provided, inspect and process them only within the assigned scope. Escalate ambiguous or high-impact decisions to the primary agent; never substitute for primary-agent decision making."
```

Do not set or change `default_subagent_model`; selecting this named role must not alter existing executor/verifier routing. Validate TOML with `tomllib` and use `codex --strict-config doctor` without starting a task.

## Fix Clash fake-IP blocking

OpenCodex checks provider destination addresses before outbound proxy handoff. If Clash DNS returns `198.18.0.0/15`, `fdfe:dcba:9876::/48`, IPv6 ULA, private, loopback, or any other non-global answer, Kimi can fail before the proxy request is sent.

Check:

```bash
dscacheutil -q host -a name api.kimi.com
```

If the result includes `198.18.x.x`, `fdfe:dcba:9876::...`, or another non-global IP, add both domains to Clash fake-IP filters:

```yaml
dns:
  fake-ip-filter:
    - api.kimi.com
    - api.moonshot.ai
```

For Clash Verge Rev, keep generated files consistent when present:

- `dns_config.yaml`
- `clash-verge.yaml`
- `clash-verge-check.yaml`

Reload without restarting the UI when the Unix socket exists:

```bash
socket="/tmp/verge/verge-mihomo.sock"
clash_config="$HOME/Library/Application Support/io.github.clash-verge-rev.clash-verge-rev/clash-verge.yaml"
curl --unix-socket "$socket" -X PUT http://unix/configs \
  -H 'Content-Type: application/json' \
  --data "{\"path\":\"$clash_config\",\"force\":true}"
dscacheutil -flushcache
```

Then verify `api.kimi.com` resolves to a public IP and rerun:

```bash
ocx provider test kimi-code
ocx sync
```

Do not set `allowPrivateNetwork: true` as the routine fix. It weakens OpenCodex's destination protection and can mask DNS/proxy errors.

## Windows non-ASCII account ACL compatibility

OpenCodex 2.8.0 can fail closed with `ACL hardening failed (EICACLS)` on Windows accounts whose username/path contains non-ASCII characters. Do not bypass this by writing a Kimi key into an unhardened config. First confirm the volume is NTFS and `icacls` works for the current SID. Then use an ASCII `OPENCODEX_HOME` (for example `C:\Users\Public\OpenCodex`) and launch OpenCodex with process-scoped `USERDOMAIN=` and `USERNAME=*<current-user-SID>` so `icacls` receives a locale-independent identity. Keep the Windows login account unchanged.

When installing the Task Scheduler service, add the same process-scoped SID environment lines to the generated service wrapper before testing autostart; otherwise the service can start under the real localized username and fail ACL hardening again. Back up the wrapper/config first, verify the service log has no ACL error, then verify provider connectivity and both model catalogs. Reapply the wrapper workaround after an OpenCodex service reinstall or update.

## Codex Desktop WebSocket 502 / 426

OpenCodex leaves the Responses WebSocket transport off by default. When Codex tries `ws://127.0.0.1:10100/v1/responses` and receives a connect-time `426 Upgrade Required`, newer clients should fall back to HTTP for that session. A client that instead reconnects repeatedly or surfaces `502 Bad Gateway` needs the proxy-side WebSocket opt-in.

Back up `~/.opencodex/config.json` (or the active `OPENCODEX_HOME` config) first, then set only:

```json
"websockets": true
```

Restart only the OpenCodex proxy/service and rerun the approved Responses canary. A post-fix canary that logs `Falling back from WebSockets to HTTPS transport` and then reaches a provider-specific `401` is a different auth problem; the original 426/502 transport blocker is resolved. Do not restart Codex Desktop without interruption approval, and do not change the Kimi key based on this transport error.

## Codex UI and CLI switching

When Codex is routed through OpenCodex, Codex Desktop may need a restart or `ocx sync --restart-codex` before its model UI sees a refreshed catalog. Do not run the restart command mid-task unless the user accepts interruption.

UI:

- Pick normal GPT entries such as `5.6 Sol` or `5.6 Terra` for OpenAI.
- Pick `Custom` and enter the full model ID for Kimi if the UI does not show named provider entries:
  - `kimi-code/k3`
  - `kimi-code/k3[1m]`
  - `kimi-code/kimi-for-coding`

CLI:

```bash
codex -m 'kimi-code/k3'
codex -m 'kimi-code/k3[1m]'
codex -m 'kimi-code/kimi-for-coding'
codex -m 'gpt-5.6-sol'
```

## GPT rollback and recovery

Confirm these commands exist with `ocx --help`:

```bash
ocx restore       # restore native Codex without stopping OpenCodex
ocx restore back  # re-point Codex at the running OpenCodex proxy
ocx stop          # stop OpenCodex and restore native Codex
```

Use rollback when Codex history disappears, OAuth looks broken, or requests are accidentally routed with the wrong credential. If a switcher overwrote `~/.codex/auth.json`, restore from a pre-change backup before continuing.

## Codex Desktop / installation-feedback `502` at the local OpenCodex endpoint

If Codex Desktop repeatedly reconnects or an installation-feedback card reports:

```text
unexpected status 502 Bad Gateway: Unknown error,
url: http://127.0.0.1:10100/v1/responses
```

first distinguish the Desktop transport path from Kimi Code authentication:

```bash
ocx provider test kimi-code
ocx status
python3 scripts/diagnose_opencodex_kimi.py --responses-canary --responses-model gpt-5.5
```

`ocx provider test kimi-code` only checks provider metadata/model discovery. It does **not** prove that Codex Desktop can successfully complete `/v1/responses` through the local proxy. When the provider test is `connected`, the Kimi CLI HTTP request succeeds, and the responses canary has `result.ok=false` with `mentions_401` or `mentions_502_bad_gateway`, treat the error as a Codex auth/transport/proxy compatibility problem first. If the canary has `result.ok=true` but `mentions_426_upgrade_required=true`, record it as a non-fatal WebSocket probe warning. This is **not** a failure of the Kimi Code API-key application flow. Do not ask the user to fill in the key again unless `ocx provider test kimi-code` itself fails.

Before changing configuration, make a private backup without printing any file contents:

```bash
backup_dir="$HOME/.opencodex/backups/$(date +%Y%m%d-%H%M%S)-desktop-502-native-restore"
umask 077
mkdir -p "$backup_dir"
cp -p "$HOME/.codex/config.toml" "$backup_dir/config.toml" 2>/dev/null || true
cp -p "$HOME/.codex/auth.json" "$backup_dir/auth.json" 2>/dev/null || true
cp -p "$HOME/.opencodex/config.json" "$backup_dir/opencodex-config.json" 2>/dev/null || true
```

Then restore the Desktop/CLI default to native OpenAI. This leaves the OpenCodex proxy running:

```bash
ocx restore
```

Native restoration can intentionally remove Kimi entries from `~/.codex/opencodex-catalog.json`; do not treat their absence as a failure of this Desktop `502` recovery path. Kimi remains available through `ocx opencode`, or through Codex only after an explicit `ocx restore back` re-routes it through OpenCodex.

Confirm that no active `openai_base_url = "http://127.0.0.1:10100/v1"` remains in `~/.codex/config.toml`, then test native Codex:

```bash
rg -n '^[[:space:]]*openai_base_url[[:space:]]*=' "$HOME/.codex/config.toml" || true
ocx status
codex exec -s read-only -m gpt-5.5 'Reply exactly: native-ok'
```

Continue using Kimi/OpenCode through `ocx opencode`. Only when the user explicitly needs Codex routed through the running OpenCodex proxy again, switch back with `ocx restore back`; that reintroduces the Desktop compatibility risk and should be followed by the relevant model and transport checks.

## Completion checklist

- `ocx provider test kimi-code` is connected.
- `ocx models selected kimi-code` includes `k3`, `k3[1m]`, and `kimi-for-coding`.
- When Codex is routed through OpenCodex (after `ocx restore back`), its catalog contains `kimi-code/k3`, `kimi-code/k3[1m]`, and `kimi-code/kimi-for-coding`; this check does not apply after native `ocx restore`.
- `api.kimi.com` resolves only to public IPs; `198.18.0.0/15`, `fdfe:dcba:9876::/48`, IPv6 ULA, private, loopback, or other non-global answers are blockers.
- `ocx status` default provider remains `openai` unless deliberately changed.
- `~/.codex/auth.json` remains an OAuth credential file, not a single Kimi API key.
- If Desktop had a `127.0.0.1:10100/v1/responses` 502, native Codex was restored with `ocx restore`; the proxy remains running and Kimi is used via `ocx opencode` until an explicit `ocx restore back`.
- Notes, logs, skills, and commits contain no raw API keys or OAuth tokens.
