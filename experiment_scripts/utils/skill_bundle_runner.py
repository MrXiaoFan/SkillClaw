#!/usr/bin/env python3
"""Run a script from a SkillClaw skill bundle.

This runner is the thin execution bridge between text skills and executable
validation helpers. It deliberately enforces a small contract:

- scripts must live under a skill bundle's `scripts/` directory
- the script is executed with the current Python interpreter by default
- `--case` and `--root` are forwarded to the script
- stdout/stderr and a parsed JSON payload are returned as a JSON object
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


class BundleRunnerError(ValueError):
    pass


def _safe_rel_script(path_text: str) -> str:
    rel = str(path_text or "").replace("\\", "/").strip().lstrip("/")
    if not rel:
        raise BundleRunnerError("script path is empty")
    if rel.startswith("../") or "/../" in rel or rel == "..":
        raise BundleRunnerError(f"unsafe script path: {path_text!r}")
    if rel.startswith("scripts/"):
        clean = rel
    else:
        clean = f"scripts/{rel}"
    if clean.endswith("/"):
        raise BundleRunnerError(f"script path points to a directory: {path_text!r}")
    return clean


def resolve_bundle_script(
    *,
    script: str,
    bundle_root: str | Path | None = None,
    skills_dir: str | Path | None = None,
    skill_name: str | None = None,
) -> Path:
    rel_script = _safe_rel_script(script)
    if bundle_root:
        root = Path(bundle_root).expanduser().resolve()
    else:
        if not skills_dir or not skill_name:
            raise BundleRunnerError("either bundle_root or skills_dir + skill_name is required")
        root = (Path(skills_dir).expanduser() / str(skill_name)).resolve()

    script_path = (root / rel_script).resolve()
    try:
        script_path.relative_to(root)
    except ValueError as exc:
        raise BundleRunnerError(f"script path escapes bundle root: {script_path}") from exc
    if not script_path.is_file():
        raise BundleRunnerError(f"bundle script not found: {script_path}")
    return script_path


def _parse_json_from_stdout(stdout: str) -> Any:
    text = str(stdout or "").strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = _JSON_OBJECT_RE.search(text)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def run_bundle_script(
    *,
    script_path: Path,
    case_path: Path | None = None,
    root: Path | None = None,
    extra_args: list[str] | None = None,
    timeout_seconds: int = 60,
    python_executable: str | None = None,
) -> dict[str, Any]:
    python_executable = python_executable or sys.executable
    command = [python_executable, str(script_path)]
    if case_path is not None:
        command.extend(["--case", str(case_path)])
    if root is not None:
        command.extend(["--root", str(root)])
    if extra_args:
        command.extend(str(arg) for arg in extra_args)

    env = os.environ.copy()
    if case_path is not None:
        env["SKILLCLAW_CASE_JSON"] = str(case_path)
    if root is not None:
        env["SKILLCLAW_TARGET_ROOT"] = str(root)
    env["SKILLCLAW_BUNDLE_SCRIPT"] = str(script_path)

    started = datetime.now(timezone.utc)
    proc = subprocess.run(
        command,
        cwd=str(root or script_path.parent),
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=max(1, int(timeout_seconds or 60)),
    )
    parsed = _parse_json_from_stdout(proc.stdout)
    status = "passed" if proc.returncode == 0 else "failed"
    if isinstance(parsed, dict) and str(parsed.get("status") or "").lower() in {
        "passed",
        "failed",
        "partial",
        "skipped",
    }:
        status = str(parsed["status"]).lower()

    return {
        "timestamp": started.isoformat(),
        "type": "bundle_script",
        "script": str(script_path),
        "command": command,
        "status": status,
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout[-4000:],
        "stderr_tail": proc.stderr[-4000:],
        "parsed_json": parsed,
    }


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--script", required=True, help="Script path under scripts/, e.g. check_avail_guard.py.")
    parser.add_argument("--bundle-root", default="")
    parser.add_argument("--skills-dir", default="")
    parser.add_argument("--skill-name", default="")
    parser.add_argument("--case", type=Path, default=None)
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("script_args", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)

    script_path = resolve_bundle_script(
        script=args.script,
        bundle_root=args.bundle_root or None,
        skills_dir=args.skills_dir or None,
        skill_name=args.skill_name or None,
    )
    result = run_bundle_script(
        script_path=script_path,
        case_path=args.case,
        root=args.root,
        extra_args=args.script_args,
        timeout_seconds=args.timeout,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] in {"passed", "partial", "skipped"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
