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
                "sk-" + "kimi",
            ]
        ):
            out.append("[redacted secret-like line]")
        else:
            out.append(line)
    return "\n".join(out)


def run_cmd(args: list[str], timeout: int) -> dict[str, Any]:
    exe = shutil.which(args[0])
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
    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout": redact(proc.stdout)[-4000:],
        "stderr": redact(proc.stderr)[-2000:],
    }


def read_json(path: pathlib.Path) -> Any | None:
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def dns_check(timeout: int) -> dict[str, Any]:
    if sys.platform == "darwin" and shutil.which("dscacheutil"):
        result = run_cmd(["dscacheutil", "-q", "host", "-a", "name", "api.kimi.com"], timeout)
        ips = [
            line.split(":", 1)[1].strip()
            for line in result.get("stdout", "").splitlines()
            if line.strip().startswith("ip_address:")
        ]
    else:
        result = run_cmd(["getent", "ahosts", "api.kimi.com"], timeout)
        ips = [line.split()[0] for line in result.get("stdout", "").splitlines() if line.split()]

    fake_ips: list[str] = []
    public_ips: list[str] = []
    for raw in ips:
        try:
            ip = ipaddress.ip_address(raw)
        except ValueError:
            continue
        if ip.version == 4 and ipaddress.ip_address("198.18.0.0") <= ip <= ipaddress.ip_address("198.19.255.255"):
            fake_ips.append(raw)
        if ip.is_global:
            public_ips.append(raw)

    return {
        "resolver_ok": result.get("ok", False),
        "ips": ips,
        "has_198_18_fake_ip": bool(fake_ips),
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
    parser.add_argument("--timeout", type=int, default=12, help="Per-command timeout seconds")
    args = parser.parse_args()

    home = pathlib.Path(os.environ.get("HOME", str(pathlib.Path.home())))
    report: dict[str, Any] = {
        "tools": {"ocx": shutil.which("ocx"), "codex": shutil.which("codex")},
        "dns_api_kimi_com": dns_check(args.timeout),
        "codex_auth": codex_auth_check(home),
        "opencodex_config": opencodex_config_check(home),
        "codex_catalog": catalog_check(home),
    }

    if shutil.which("ocx"):
        report["ocx_status"] = run_cmd(["ocx", "status"], args.timeout)
        report["ocx_models_selected_kimi_code"] = run_cmd(["ocx", "models", "selected", "kimi-code"], args.timeout)
        if args.provider_test:
            report["ocx_provider_test_kimi_code"] = run_cmd(["ocx", "provider", "test", "kimi-code"], args.timeout)

    json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
