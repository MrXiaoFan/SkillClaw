from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

from .core import ValidationContext, ValidatorRegistry

try:
    from experiment_scripts.skill_bundle_runner import BundleRunnerError, resolve_bundle_script, run_bundle_script
except ImportError:  # pragma: no cover - direct script execution on remote VM.
    from skill_bundle_runner import BundleRunnerError, resolve_bundle_script, run_bundle_script


DEFAULT_SANITIZER_MARKERS = [
    "AddressSanitizer",
    "UndefinedBehaviorSanitizer",
    "ERROR: AddressSanitizer",
    "heap-buffer-overflow",
    "stack-buffer-overflow",
    "global-buffer-overflow",
    "use-after-free",
    "runtime error:",
    "SEGV",
]


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace")


def _tail(value: Any, limit: int = 4000) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")[-limit:]
    return str(value)[-limit:]


def _ground_truth_patterns(case: dict[str, Any]) -> list[str]:
    truth = case.get("ground_truth", {}) if isinstance(case.get("ground_truth"), dict) else {}
    patterns: list[str] = []
    for key in ("cves", "files", "functions", "required_evidence"):
        value = truth.get(key)
        if isinstance(value, list):
            patterns.extend(str(item) for item in value if str(item).strip())
    root_cause = str(truth.get("root_cause", "") or "").strip()
    if root_cause:
        patterns.extend(term for term in root_cause.replace(",", " ").split() if len(term) >= 6)
    return list(dict.fromkeys(patterns))


def _ground_truth_stack_patterns(case: dict[str, Any]) -> list[str]:
    truth = case.get("ground_truth", {}) if isinstance(case.get("ground_truth"), dict) else {}
    patterns: list[str] = []
    for key in ("files", "functions"):
        value = truth.get(key)
        if isinstance(value, list):
            patterns.extend(str(item) for item in value if str(item).strip())
    return list(dict.fromkeys(patterns))


def content_match_validator(ctx: ValidationContext, spec: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "name": spec.get("name"),
        "type": "content_match",
        "allow_failure": bool(spec.get("allow_failure")),
        "source": spec.get("source", "agent_output"),
    }
    if ctx.agent_output_path is None:
        result["status"] = "skipped"
        result["reason"] = "no agent output path provided"
        return result
    if not ctx.agent_output_path.is_file():
        result["status"] = "missing"
        result["path"] = str(ctx.agent_output_path)
        return result

    text = _read_text(ctx.agent_output_path)
    patterns = [str(item) for item in spec.get("patterns", []) if str(item).strip()]
    if spec.get("use_ground_truth", True):
        patterns.extend(_ground_truth_patterns(ctx.case))
    patterns = list(dict.fromkeys(patterns))
    match_mode = str(spec.get("match", "any") or "any").lower()
    hits = [{"pattern": pattern, "hit": pattern.lower() in text.lower()} for pattern in patterns]
    hit_count = sum(1 for item in hits if item["hit"])
    if not patterns:
        status = "skipped"
    elif match_mode == "all":
        status = "passed" if hit_count == len(patterns) else "failed"
    else:
        status = "passed" if hit_count else "failed"
    result.update(
        {
            "status": status,
            "path": str(ctx.agent_output_path),
            "match": match_mode,
            "hit_count": hit_count,
            "total_patterns": len(patterns),
            "patterns": hits,
        }
    )
    return result


def source_contains_validator(ctx: ValidationContext, spec: dict[str, Any]) -> dict[str, Any]:
    rel_file = str(spec.get("file", "") or "")
    path = ctx.root / rel_file
    patterns = [str(item) for item in spec.get("patterns", [])]
    result: dict[str, Any] = {
        "name": spec.get("name"),
        "type": "source_contains",
        "allow_failure": bool(spec.get("allow_failure")),
        "file": rel_file,
        "path": str(path),
        "exists": path.is_file(),
        "patterns": [],
    }
    if not path.is_file():
        result["status"] = "missing"
        return result

    text = _read_text(path)
    all_hit = True
    for pattern in patterns:
        hit = pattern in text
        result["patterns"].append({"pattern": pattern, "hit": hit})
        all_hit = all_hit and hit
    result["status"] = "passed" if all_hit else "failed"
    return result


def command_validator(ctx: ValidationContext, spec: dict[str, Any]) -> dict[str, Any]:
    vtype = str(spec.get("type", "command") or "command")
    if ctx.skip_commands:
        return {
            "name": spec.get("name"),
            "type": vtype,
            "allow_failure": bool(spec.get("allow_failure")),
            "status": "skipped",
            "reason": "commands skipped by context",
        }

    command = str(spec.get("command", "") or "")
    timeout = int(spec.get("timeout_seconds", 30) or 30)
    result: dict[str, Any] = {
        "name": spec.get("name"),
        "type": vtype,
        "allow_failure": bool(spec.get("allow_failure")),
        "command": command,
        "cwd": str(ctx.root),
    }
    if not command:
        result["status"] = "skipped"
        result["reason"] = "empty command"
        return result

    try:
        proc = subprocess.run(
            command,
            cwd=str(ctx.root),
            shell=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        result.update(
            {
                "status": "failed",
                "error": f"command timed out after {timeout}s",
                "stdout_tail": _tail(exc.stdout),
                "stderr_tail": _tail(exc.stderr),
            }
        )
        return result
    result.update(
        {
            "status": "passed" if proc.returncode == 0 else "failed",
            "returncode": proc.returncode,
            "stdout_tail": _tail(proc.stdout),
            "stderr_tail": _tail(proc.stderr),
        }
    )
    return result


def asan_command_validator(ctx: ValidationContext, spec: dict[str, Any]) -> dict[str, Any]:
    if ctx.skip_commands:
        return {
            "name": spec.get("name"),
            "type": "asan_command",
            "allow_failure": bool(spec.get("allow_failure")),
            "status": "skipped",
            "reason": "commands skipped by context",
        }

    command = str(spec.get("command", "") or "")
    timeout = int(spec.get("timeout_seconds", 30) or 30)
    result: dict[str, Any] = {
        "name": spec.get("name"),
        "type": "asan_command",
        "allow_failure": bool(spec.get("allow_failure")),
        "command": command,
        "cwd": str(ctx.root),
    }
    if not command:
        result["status"] = "skipped"
        result["reason"] = "empty command"
        return result

    try:
        proc = subprocess.run(
            command,
            cwd=str(ctx.root),
            shell=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
        stdout_tail = _tail(proc.stdout)
        stderr_tail = _tail(proc.stderr)
        combined = f"{proc.stdout}\n{proc.stderr}"
        returncode = proc.returncode
        timeout_error = ""
    except subprocess.TimeoutExpired as exc:
        stdout_tail = _tail(exc.stdout)
        stderr_tail = _tail(exc.stderr)
        combined = f"{stdout_tail}\n{stderr_tail}"
        returncode = None
        timeout_error = f"command timed out after {timeout}s"

    markers = [str(item) for item in spec.get("sanitizer_markers", []) or DEFAULT_SANITIZER_MARKERS]
    expected_stack_patterns = [
        str(item) for item in spec.get("expected_stack_patterns", []) or _ground_truth_stack_patterns(ctx.case)
    ]
    expected_stack_patterns = list(dict.fromkeys(item for item in expected_stack_patterns if item.strip()))

    combined_lower = combined.lower()
    matched_markers = [marker for marker in markers if marker.lower() in combined_lower]
    matched_stack_patterns = [pattern for pattern in expected_stack_patterns if pattern.lower() in combined_lower]
    stack_match = str(spec.get("stack_match", "any") or "any").lower()
    if expected_stack_patterns:
        if stack_match == "all":
            stack_hit = len(matched_stack_patterns) == len(expected_stack_patterns)
        else:
            stack_hit = bool(matched_stack_patterns)
    else:
        stack_hit = True

    marker_hit = bool(matched_markers)
    crash_observed = returncode not in (0, None) or bool(timeout_error)
    expect_crash = bool(spec.get("expect_crash", True))
    if expect_crash:
        if marker_hit and stack_hit:
            status = "passed"
        elif marker_hit or (crash_observed and stack_hit):
            status = "partial"
        else:
            status = "failed"
    else:
        if returncode == 0 and not marker_hit:
            status = "passed"
        elif marker_hit:
            status = "failed"
        else:
            status = "partial"

    result.update(
        {
            "status": status,
            "returncode": returncode,
            "expect_crash": expect_crash,
            "crash_observed": crash_observed,
            "sanitizer_marker_hit": marker_hit,
            "matched_markers": matched_markers,
            "stack_match": stack_match,
            "stack_hit": stack_hit,
            "matched_stack_patterns": matched_stack_patterns,
            "expected_stack_patterns": expected_stack_patterns,
            "stdout_tail": stdout_tail,
            "stderr_tail": stderr_tail,
        }
    )
    if timeout_error:
        result["error"] = timeout_error
    return result


def bundle_script_validator(ctx: ValidationContext, spec: dict[str, Any]) -> dict[str, Any]:
    if ctx.skip_commands:
        return {
            "name": spec.get("name"),
            "type": "bundle_script",
            "allow_failure": bool(spec.get("allow_failure")),
            "status": "skipped",
            "reason": "commands skipped by context",
        }

    result: dict[str, Any] = {
        "name": spec.get("name"),
        "type": "bundle_script",
        "allow_failure": bool(spec.get("allow_failure")),
        "skill_name": spec.get("skill_name"),
        "script": spec.get("script"),
    }
    try:
        bundle_root = spec.get("bundle_root") or None
        skills_dir = spec.get("skills_dir") or None
        if ctx.case_path is not None:
            case_dir = ctx.case_path.resolve().parent
            if bundle_root and not Path(str(bundle_root)).is_absolute():
                bundle_root = str(case_dir / str(bundle_root))
            if skills_dir and not Path(str(skills_dir)).is_absolute():
                skills_dir = str(case_dir / str(skills_dir))
        script_path = resolve_bundle_script(
            script=str(spec.get("script", "") or ""),
            bundle_root=bundle_root,
            skills_dir=skills_dir,
            skill_name=spec.get("skill_name") or None,
        )
        run_result = run_bundle_script(
            script_path=script_path,
            case_path=ctx.case_path.resolve() if ctx.case_path is not None else None,
            root=ctx.root,
            extra_args=[str(arg) for arg in spec.get("args", []) or []],
            timeout_seconds=int(spec.get("timeout_seconds", 60) or 60),
        )
        result.update(run_result)
    except (BundleRunnerError, subprocess.TimeoutExpired, OSError, ValueError) as exc:
        result["status"] = "failed"
        result["error"] = str(exc)
    return result


def default_registry() -> ValidatorRegistry:
    registry = ValidatorRegistry()
    registry.register("content_match", content_match_validator)
    registry.register("source_contains", source_contains_validator)
    registry.register("command", command_validator)
    registry.register("asan_command", asan_command_validator)
    registry.register("bundle_script", bundle_script_validator)
    return registry
