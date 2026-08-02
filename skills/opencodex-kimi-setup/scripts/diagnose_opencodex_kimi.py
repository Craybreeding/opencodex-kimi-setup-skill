#!/usr/bin/env python3
"""Read-only OpenCodex + Kimi Code diagnostic.

The script reports only credential shape/status. It never prints API keys,
OAuth token values, or full config files.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import pathlib
import shutil
import subprocess
import sys
from typing import Any


TARGET_MODELS = [
    "kimi-code/k3",
    "kimi-code/k3[1m]",
    "kimi-code/kimi-for-coding",
]

COMMON_TOOL_PATHS = {
    "ocx": [
        ".local/share/npm-global/bin/ocx",
        "/opt/homebrew/bin/ocx",
    ],
    "codex": [
        ".local/share/npm-global/bin/codex",
        "/opt/homebrew/bin/codex",
    ],
    "bun": [
        ".bun/bin/bun",
    ],
}

FAKE_IP_V4_NETWORK = ipaddress.ip_network("198.18.0.0/15")
FAKE_IP_V6_NETWORK = ipaddress.ip_network("fdfe:dcba:9876::/48")
IPV6_ULA_NETWORK = ipaddress.ip_network("fc00::/7")


def redact(text: str) -> str:
    out: list[str] = []
    for line in text.splitlines():
        lower = line.lower()
        if any(
            marker in lower
            for marker in [
                "apikey",
                "api_key",
                "authorization",
                "bearer ",
                "oauth",
                "refresh_token",
                "access_token",
                "token",
                "secret",
                "credential",
                "cookie",
                "session",
                "sk-" + "kimi",
            ]
        ):
            out.append("[redacted secret-like line]")
        else:
            out.append(line)
    return "\n".join(out)


def find_tool(name: str, home: pathlib.Path) -> str | None:
    """Find a tool even when a non-interactive SSH session has a minimal PATH."""
    candidates: list[pathlib.Path] = []
    in_path = shutil.which(name)
    if in_path:
        candidates.append(pathlib.Path(in_path))
    for raw_path in COMMON_TOOL_PATHS[name]:
        candidates.append(home / raw_path if not raw_path.startswith("/") else pathlib.Path(raw_path))

    for candidate in candidates:
        try:
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return str(candidate)
        except OSError:
            continue
    return None


def run_cmd(args: list[str], timeout: int, executable: str | None = None) -> dict[str, Any]:
    exe = executable or shutil.which(args[0])
    if not exe:
        return {"ok": False, "missing": True, "argv_head": args[:2]}
    try:
        proc = subprocess.run(
            [exe, *args[1:]],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "timeout": True, "argv_head": args[:2]}
    combined = f"{proc.stdout}\n{proc.stderr}".lower()
    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout": redact(proc.stdout)[-4000:],
        "stderr": redact(proc.stderr)[-2000:],
        "signals": {
            "mentions_v1_responses": "/v1/responses" in combined,
            "mentions_websocket": "websocket" in combined or "ws://127.0.0.1:10100" in combined,
            "mentions_401": " 401" in combined or "status 401" in combined or "http error: 401" in combined,
            "mentions_426_upgrade_required": "426" in combined and "upgrade required" in combined,
            "mentions_502_bad_gateway": "502" in combined or "bad gateway" in combined,
        },
    }


def read_json(path: pathlib.Path) -> Any | None:
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def dns_check(timeout: int) -> dict[str, Any]:
    if sys.platform == "darwin" and shutil.which("dscacheutil"):
        result = run_cmd(["dscacheutil", "-q", "host", "-a", "name", "api.kimi.com"], timeout)
        ipv4_addresses = []
        ipv6_addresses = []
        for line in result.get("stdout", "").splitlines():
            stripped = line.strip()
            if stripped.startswith("ip_address:"):
                ipv4_addresses.append(stripped.split(":", 1)[1].strip())
            elif stripped.startswith("ipv6_address:"):
                ipv6_addresses.append(stripped.split(":", 1)[1].strip())
    else:
        result = run_cmd(["getent", "ahosts", "api.kimi.com"], timeout)
        ips = [line.split()[0] for line in result.get("stdout", "").splitlines() if line.split()]
        ipv4_addresses = []
        ipv6_addresses = []
        for raw in ips:
            try:
                if ipaddress.ip_address(raw).version == 4:
                    ipv4_addresses.append(raw)
                else:
                    ipv6_addresses.append(raw)
            except ValueError:
                continue

    ips = ipv4_addresses + ipv6_addresses

    fake_ipv4_addresses: list[str] = []
    fake_ipv6_addresses: list[str] = []
    ula_ipv6_addresses: list[str] = []
    non_global_ips: list[str] = []
    public_ips: list[str] = []
    for raw in ips:
        try:
            ip = ipaddress.ip_address(raw)
        except ValueError:
            continue
        if ip.version == 4 and ip in FAKE_IP_V4_NETWORK:
            fake_ipv4_addresses.append(raw)
        if ip.version == 6 and ip in FAKE_IP_V6_NETWORK:
            fake_ipv6_addresses.append(raw)
        if ip.version == 6 and ip in IPV6_ULA_NETWORK:
            ula_ipv6_addresses.append(raw)
        if ip.is_global:
            public_ips.append(raw)
        else:
            non_global_ips.append(raw)

    return {
        "resolver_ok": result.get("ok", False),
        "ips": ips,
        "ipv4_addresses": ipv4_addresses,
        "ipv6_addresses": ipv6_addresses,
        "non_global_ips": non_global_ips,
        "has_non_global_ip": bool(non_global_ips),
        "fake_ipv4_addresses": fake_ipv4_addresses,
        "fake_ipv6_addresses": fake_ipv6_addresses,
        "ula_ipv6_addresses": ula_ipv6_addresses,
        "has_198_18_fake_ip": bool(fake_ipv4_addresses),
        "has_fdfe_dcba_9876_fake_ip": bool(fake_ipv6_addresses),
        "has_ipv6_ula": bool(ula_ipv6_addresses),
        "has_public_ip": bool(public_ips),
    }


def catalog_check(home: pathlib.Path) -> dict[str, Any]:
    path = home / ".codex" / "opencodex-catalog.json"
    data = read_json(path)
    blob = json.dumps(data, ensure_ascii=False) if data is not None else ""
    return {
        "path": str(path),
        "exists": path.exists(),
        "valid_json": data is not None,
        "models": {model: model in blob for model in TARGET_MODELS},
    }


def opencodex_config_check(home: pathlib.Path) -> dict[str, Any]:
    path = home / ".opencodex" / "config.json"
    data = read_json(path)
    provider = data.get("providers", {}).get("kimi-code", {}) if isinstance(data, dict) else {}
    return {
        "path": str(path),
        "exists": path.exists(),
        "valid_json": data is not None,
        "kimi_code_configured": bool(provider),
        "kimi_code_has_key_shape": bool(provider.get("apiKey") or provider.get("apiKeyPool")),
        "kimi_code_selected_models": provider.get("selectedModels", []),
        "kimi_code_declared_models": provider.get("models", []),
        "default_provider": data.get("defaultProvider") if isinstance(data, dict) else None,
    }


def codex_auth_check(home: pathlib.Path) -> dict[str, Any]:
    path = home / ".codex" / "auth.json"
    size = path.stat().st_size if path.exists() else None
    data = read_json(path)
    keys = sorted(data.keys()) if isinstance(data, dict) else []
    return {
        "path": str(path),
        "exists": path.exists(),
        "size_bytes": size,
        "valid_json": data is not None,
        "top_level_keys": keys[:20],
        "looks_too_small_for_oauth": bool(size is not None and size < 500),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only OpenCodex + Kimi Code diagnostic")
    parser.add_argument("--provider-test", action="store_true", help="Run `ocx provider test kimi-code`")
    parser.add_argument(
        "--responses-canary",
        action="store_true",
        help=(
            "Run a real, billable Codex /v1/responses request; it can expose 502 or 401 failures"
        ),
    )
    parser.add_argument(
        "--responses-model",
        default="gpt-5.5",
        help="Model for --responses-canary (default: gpt-5.5)",
    )
    parser.add_argument("--timeout", type=int, default=12, help="Per-command timeout seconds")
    args = parser.parse_args()

    home = pathlib.Path(os.environ.get("HOME", str(pathlib.Path.home())))
    tools = {name: find_tool(name, home) for name in COMMON_TOOL_PATHS}
    report: dict[str, Any] = {
        "tools": tools,
        "dns_api_kimi_com": dns_check(args.timeout),
        "codex_auth": codex_auth_check(home),
        "opencodex_config": opencodex_config_check(home),
        "codex_catalog": catalog_check(home),
        "responses_canary": {
            "requested": args.responses_canary,
            "ran": False,
            "model": args.responses_model,
            "billable_real_model_call": args.responses_canary,
        },
    }

    if tools["ocx"]:
        report["ocx_status"] = run_cmd(["ocx", "status"], args.timeout, tools["ocx"])
        report["ocx_models_selected_kimi_code"] = run_cmd(
            ["ocx", "models", "selected", "kimi-code"], args.timeout, tools["ocx"]
        )
        if args.provider_test:
            report["ocx_provider_test_kimi_code"] = run_cmd(
                ["ocx", "provider", "test", "kimi-code"], args.timeout, tools["ocx"]
            )

    if args.responses_canary:
        canary = run_cmd(
            [
                "codex",
                "exec",
                "--ephemeral",
                "--skip-git-repo-check",
                "-s",
                "read-only",
                "-m",
                args.responses_model,
                "Reply exactly: native-ok",
            ],
            max(args.timeout, 60),
            tools["codex"],
        )
        report["responses_canary"] = {
            "requested": True,
            "ran": not canary.get("missing", False),
            "model": args.responses_model,
            "billable_real_model_call": True,
            "result": canary,
        }

    json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
