# OpenCodex + Kimi Code runbook

Use this when a user wants Codex to call Kimi Code models through OpenCodex while keeping GPT/OpenAI available.

## Model IDs

Prefer the `kimi-code` provider:

- `kimi-code/k3`
- `kimi-code/k3[1m]`
- `kimi-code/kimi-for-coding`

`k3[1m]` may need manual custom registration because live discovery can omit it even when the provider is reachable. Registration does not prove the account has 1M entitlement; the first real model request confirms that.

## Preflight

Run from the skill folder:

```bash
python3 scripts/diagnose_opencodex_kimi.py
```

Optionally include provider metadata call:

```bash
python3 scripts/diagnose_opencodex_kimi.py --provider-test
```

Red flags:

- `api.kimi.com` resolves to `198.18.x.x`: Clash fake-IP is still visible to OpenCodex.
- `~/.codex/auth.json` is very small or shaped like one API key: Codex OAuth may have been overwritten.
- `ocx status` cannot find a running proxy when Codex config points to `127.0.0.1:10100`.
- Catalog lacks the three `kimi-code/...` model IDs after `ocx sync`.

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

## Add the Kimi Code key

Never paste the key into the prompt, command history, notes, or git. Use silent input:

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

If `ocx provider test kimi-code` is connected but the catalog lacks `kimi-code/k3[1m]`, add a custom model:

```bash
ocx models add kimi-code 'k3[1m]' \
  --display-name 'Kimi K3 1M' \
  --context-window 1000000 \
  --modalities text
ocx sync
```

Verify:

```bash
ocx models list-custom
ocx models selected kimi-code
python3 scripts/diagnose_opencodex_kimi.py
```

## Fix Clash fake-IP blocking

OpenCodex checks provider destination addresses before outbound proxy handoff. If Clash DNS returns `198.18.0.0/15`, Kimi can fail before the proxy request is sent.

Check:

```bash
dscacheutil -q host -a name api.kimi.com
```

If the result is `198.18.x.x`, add both domains to Clash fake-IP filters:

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

## Codex UI and CLI switching

Codex Desktop may need a restart or `ocx sync --restart-codex` before its model UI sees a refreshed catalog. Do not run the restart command mid-task unless the user accepts interruption.

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

## Completion checklist

- `ocx provider test kimi-code` is connected.
- `ocx models selected kimi-code` includes `k3`, `k3[1m]`, and `kimi-for-coding`.
- Codex catalog contains `kimi-code/k3`, `kimi-code/k3[1m]`, and `kimi-code/kimi-for-coding`.
- `api.kimi.com` is not `198.18.0.0/15`.
- `ocx status` default provider remains `openai` unless deliberately changed.
- `~/.codex/auth.json` remains an OAuth credential file, not a single Kimi API key.
- Notes, logs, skills, and commits contain no raw API keys or OAuth tokens.
