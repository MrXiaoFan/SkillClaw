#!/usr/bin/env python3
"""Check whether a VM/workspace is ready to run an experiment case.

This script is deliberately lightweight: it does not call an LLM and does not
run validators that may execute target binaries.  It catches the common setup
mistakes before a long Claude Code run starts: wrong source root, missing
binary, missing ground-truth files, wrong Claude provider, or an unavailable
SkillClaw proxy.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))


def expand_path(path_text: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(path_text)))


def resolve_root(case: dict[str, Any], override: str | None) -> Path:
    if override:
        return expand_path(override)
    target = case.get("target", {}) if isinstance(case.get("target"), dict) else {}
    return expand_path(str(target.get("source_root") or "."))


def infer_claude_provider(settings_path: Path) -> dict[str, Any]:
    try:
        data = load_json(settings_path)
    except OSError as exc:
        return {
            "settings_path": str(settings_path),
            "status": "missing",
            "error": str(exc),
            "provider": "unknown",
        }
    except json.JSONDecodeError as exc:
        return {
            "settings_path": str(settings_path),
            "status": "invalid_json",
            "error": str(exc),
            "provider": "unknown",
        }

    env = data.get("env", {}) if isinstance(data.get("env"), dict) else {}
    base_url = str(env.get("ANTHROPIC_BASE_URL") or "")
    model = str(env.get("ANTHROPIC_MODEL") or "")
    provider = "unknown"
    lowered = base_url.lower()
    if "skillclaw" in lowered or ":30000" in lowered:
        provider = "skillclaw"
    elif "deepseek" in lowered:
        provider = "deepseek"
    return {
        "settings_path": str(settings_path),
        "status": "ok",
        "provider": provider,
        "base_url": base_url,
        "model": model,
    }


def _http_json(url: str, headers: dict[str, str] | None, timeout: float) -> tuple[int, Any]:
    request = Request(url, headers=headers or {})
    with urlopen(request, timeout=timeout) as response:  # noqa: S310 - explicit user-provided lab URL.
        status = int(response.status)
        raw = response.read().decode("utf-8", errors="replace")
    try:
        return status, json.loads(raw)
    except json.JSONDecodeError:
        return status, raw


def check_skillclaw(url: str, key: str | None, expected_count: int | None, timeout: float) -> dict[str, Any]:
    base = url.rstrip("/")
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    result: dict[str, Any] = {"url": base, "status": "ok"}
    try:
        health_status, health = _http_json(f"{base}/healthz", None, timeout)
        result["healthz"] = {"http_status": health_status, "body": health}
        skills_status, skills = _http_json(f"{base}/v1/skills", headers, timeout)
        count = skills.get("count") if isinstance(skills, dict) else None
        result["skills"] = {"http_status": skills_status, "count": count}
        if expected_count is not None and count != expected_count:
            result["status"] = "failed"
            result["error"] = f"expected {expected_count} skills, got {count}"
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        result["status"] = "failed"
        result["error"] = str(exc)
    return result


def _check_path(name: str, path: Path, *, required: bool = True) -> dict[str, Any]:
    exists = path.exists()
    status = "ok" if exists else ("failed" if required else "missing_optional")
    return {"name": name, "path": str(path), "exists": exists, "status": status}


def check_case_environment(
    *,
    case_path: Path,
    root_override: str | None = None,
    settings_path: Path | None = None,
    expected_provider: str | None = None,
    skillclaw_url: str | None = None,
    skillclaw_key: str | None = None,
    expected_skill_count: int | None = None,
    timeout: float = 5.0,
) -> dict[str, Any]:
    case = load_json(case_path)
    root = resolve_root(case, root_override)
    target = case.get("target", {}) if isinstance(case.get("target"), dict) else {}
    truth = case.get("ground_truth", {}) if isinstance(case.get("ground_truth"), dict) else {}

    checks: list[dict[str, Any]] = [
        {"name": "case_json", "path": str(case_path), "status": "ok", "exists": True},
        _check_path("source_root", root),
    ]

    binary = str(target.get("binary") or "").strip()
    if binary:
        checks.append(_check_path("target_binary", root / binary))

    for rel_file in truth.get("files", []) or []:
        if str(rel_file).strip():
            checks.append(_check_path("ground_truth_file", root / str(rel_file)))

    claude: dict[str, Any] | None = None
    if settings_path:
        claude = infer_claude_provider(settings_path)
        if expected_provider and claude.get("provider") != expected_provider:
            claude["status"] = "failed"
            claude["error"] = f"expected provider {expected_provider!r}, got {claude.get('provider')!r}"

    skillclaw: dict[str, Any] | None = None
    if skillclaw_url:
        skillclaw = check_skillclaw(skillclaw_url, skillclaw_key, expected_skill_count, timeout)

    failed = [item for item in checks if item.get("status") == "failed"]
    if claude and claude.get("status") == "failed":
        failed.append({"name": "claude_settings", **claude})
    if skillclaw and skillclaw.get("status") == "failed":
        failed.append({"name": "skillclaw_proxy", **skillclaw})

    return {
        "case_id": case.get("case_id") or case_path.stem,
        "case_path": str(case_path),
        "root": str(root),
        "status": "failed" if failed else "passed",
        "checks": checks,
        "claude": claude,
        "skillclaw": skillclaw,
    }


def _default_settings_path() -> Path:
    return Path.home() / ".claude" / "settings.json"


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", type=Path, help="Path to an experiment case JSON.")
    parser.add_argument("--root", help="Override target source root.")
    parser.add_argument(
        "--settings",
        type=Path,
        default=_default_settings_path(),
        help="Claude Code settings.json path. Use --no-claude-settings to skip.",
    )
    parser.add_argument("--no-claude-settings", action="store_true", help="Skip Claude settings check.")
    parser.add_argument("--expected-provider", choices=["skillclaw", "deepseek", "unknown"])
    parser.add_argument("--skillclaw-url", help="SkillClaw proxy URL, for example http://10.12.189.47:30000.")
    parser.add_argument("--skillclaw-key", help="Bearer token for /v1/skills.")
    parser.add_argument("--expected-skill-count", type=int)
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--json", action="store_true", help="Print full JSON result.")
    args = parser.parse_args(argv)

    result = check_case_environment(
        case_path=args.case,
        root_override=args.root,
        settings_path=None if args.no_claude_settings else args.settings,
        expected_provider=args.expected_provider,
        skillclaw_url=args.skillclaw_url,
        skillclaw_key=args.skillclaw_key,
        expected_skill_count=args.expected_skill_count,
        timeout=args.timeout,
    )

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"{result['case_id']}: {result['status']}")
        for item in result["checks"]:
            marker = "OK" if item.get("status") == "ok" else "FAIL"
            print(f"{marker} {item.get('name')}: {item.get('path')}")
        if result.get("claude"):
            claude = result["claude"]
            marker = "OK" if claude.get("status") == "ok" else "FAIL"
            print(f"{marker} claude_settings: provider={claude.get('provider')} model={claude.get('model', '')}")
        if result.get("skillclaw"):
            skillclaw = result["skillclaw"]
            marker = "OK" if skillclaw.get("status") == "ok" else "FAIL"
            count = (skillclaw.get("skills") or {}).get("count") if isinstance(skillclaw.get("skills"), dict) else None
            print(f"{marker} skillclaw_proxy: url={skillclaw.get('url')} skills={count}")

    return 0 if result.get("status") == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
