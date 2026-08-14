from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

from .core import ValidationContext, ValidatorRegistry

try:
    from evaluation.utils.bundle_script_bridge import BundleRunnerError, resolve_bundle_script, run_bundle_script
except ImportError:  # pragma: no cover - direct script execution on remote VM.
    from bundle_script_bridge import BundleRunnerError, resolve_bundle_script, run_bundle_script


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


def _repo_root(ctx: ValidationContext) -> Path:
    if ctx.case_path is not None:
        case_path = ctx.case_path.resolve()
        if len(case_path.parents) >= 3:
            return case_path.parents[2]
    return Path.cwd().resolve()


def _resolve_case_relative_dir(ctx: ValidationContext, raw_path: str | Path | None) -> str | None:
    if not raw_path:
        return None
    path_text = str(raw_path).strip()
    if not path_text:
        return None
    path = Path(path_text)
    if path.is_absolute():
        return str(path)
    if ctx.case_path is None:
        return str(path)

    case_dir = ctx.case_path.resolve().parent
    candidates = [case_dir / path, case_dir.parent / path, _repo_root(ctx) / path]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return str(candidates[0])


def _command_env(ctx: ValidationContext) -> dict[str, str]:
    env = os.environ.copy()
    env["SKILLCLAW_TARGET_ROOT"] = str(ctx.root.resolve())
    if ctx.case_path is not None:
        case_path = ctx.case_path.resolve()
        env["SKILLCLAW_CASE_PATH"] = str(case_path)
        env["SKILLCLAW_CASE_DIR"] = str(case_path.parent)
    env["SKILLCLAW_REPO_ROOT"] = str(_repo_root(ctx))
    return env


def _resolve_artifact_path(ctx: ValidationContext, value: str) -> Path:
    artifact = str(value or "").strip()
    if not artifact:
        return ctx.root
    path = Path(os.path.expandvars(os.path.expanduser(artifact)))
    if path.is_absolute():
        return path
    if artifact.startswith("artifacts/") or artifact.startswith("artifacts\\"):
        return ctx.root / artifact
    return ctx.root / "artifacts" / artifact


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace")


def _tail(value: Any, limit: int = 4000) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")[-limit:]
    return str(value)[-limit:]


def _resolve_marker_match(
    spec: dict[str, Any],
    markers: list[str],
    matched_markers: list[str],
) -> tuple[bool, str, bool, list[str]]:
    require_markers = bool(spec.get("require_markers")) or bool(markers)
    raw_mode = str(spec.get("marker_match", "all") or "all").strip().lower()
    marker_match = raw_mode if raw_mode in {"any", "all"} else "all"
    missing_markers = [marker for marker in markers if marker not in matched_markers]
    if not require_markers or not markers:
        return True, marker_match, require_markers, missing_markers
    if marker_match == "any":
        return bool(matched_markers), marker_match, require_markers, missing_markers
    return len(matched_markers) == len(markers), marker_match, require_markers, missing_markers


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


def artifact_exists_validator(ctx: ValidationContext, spec: dict[str, Any]) -> dict[str, Any]:
    artifact_path = _resolve_artifact_path(ctx, str(spec.get("path", "") or ""))
    result: dict[str, Any] = {
        "name": spec.get("name"),
        "type": "artifact_exists",
        "allow_failure": bool(spec.get("allow_failure")),
        "path": str(artifact_path),
        "exists": artifact_path.exists(),
    }
    expected_type = str(spec.get("artifact_type", "") or "").strip().lower()
    if not artifact_path.exists():
        result["status"] = "missing"
        return result
    if expected_type == "file" and not artifact_path.is_file():
        result["status"] = "failed"
        result["reason"] = "expected file"
        return result
    if expected_type == "directory" and not artifact_path.is_dir():
        result["status"] = "failed"
        result["reason"] = "expected directory"
        return result
    min_size = spec.get("min_size_bytes")
    if isinstance(min_size, (int, float)) and artifact_path.is_file():
        size = artifact_path.stat().st_size
        result["size_bytes"] = size
        if size < int(min_size):
            result["status"] = "failed"
            result["reason"] = f"artifact smaller than required minimum {int(min_size)} bytes"
            return result
    result["status"] = "passed"
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
            env=_command_env(ctx),
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


def artifact_exec_validator(ctx: ValidationContext, spec: dict[str, Any]) -> dict[str, Any]:
    if ctx.skip_commands:
        return {
            "name": spec.get("name"),
            "type": "artifact_exec",
            "allow_failure": bool(spec.get("allow_failure")),
            "status": "skipped",
            "reason": "commands skipped by context",
        }

    artifact_path = _resolve_artifact_path(ctx, str(spec.get("path", "") or ""))
    timeout = int(spec.get("timeout_seconds", 60) or 60)
    result: dict[str, Any] = {
        "name": spec.get("name"),
        "type": "artifact_exec",
        "allow_failure": bool(spec.get("allow_failure")),
        "path": str(artifact_path),
        "cwd": str(ctx.root),
    }
    if not artifact_path.exists():
        result["status"] = "missing"
        return result

    command = str(spec.get("command", "") or "").strip()
    if not command:
        exec_mode = str(spec.get("exec_mode", "") or "").strip().lower()
        if exec_mode == "python":
            command = f'python "{artifact_path}"'
        elif exec_mode == "bash":
            command = f'bash "{artifact_path}"'
        elif exec_mode == "sh":
            command = f'sh "{artifact_path}"'
        elif exec_mode == "direct":
            command = str(artifact_path)
        else:
            command = f'"{artifact_path}"'
    extra_args = [str(item) for item in spec.get("args", []) or [] if str(item).strip()]
    if extra_args:
        command = " ".join([command, *extra_args])
    result["command"] = command

    try:
        proc = subprocess.run(
            command,
            cwd=str(ctx.root),
            env=_command_env(ctx),
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

    stdout_tail = _tail(proc.stdout)
    stderr_tail = _tail(proc.stderr)
    combined = f"{proc.stdout}\n{proc.stderr}"
    combined_lower = combined.lower()
    markers = [str(item) for item in spec.get("success_markers", []) if str(item).strip()]
    matched_markers = [marker for marker in markers if marker.lower() in combined_lower]
    marker_ok, marker_match, require_markers, missing_markers = _resolve_marker_match(
        spec,
        markers,
        matched_markers,
    )
    expect_crash = spec.get("expect_crash")

    if expect_crash is True:
        if proc.returncode != 0 and marker_ok:
            status = "passed"
        else:
            status = "failed"
    else:
        if proc.returncode == 0 and marker_ok:
            status = "passed"
        else:
            status = "failed"

    result.update(
        {
            "status": status,
            "returncode": proc.returncode,
            "stdout_tail": stdout_tail,
            "stderr_tail": stderr_tail,
            "success_markers": markers,
            "matched_markers": matched_markers,
            "missing_markers": missing_markers,
            "marker_match": marker_match,
            "require_markers": require_markers,
            "expect_crash": expect_crash,
        }
    )
    if status == "failed":
        if expect_crash is True and proc.returncode == 0:
            result["reason"] = "expected non-zero return code"
        elif expect_crash is not True and proc.returncode != 0:
            result["reason"] = "expected zero return code"
        elif require_markers and missing_markers:
            result["reason"] = "missing required success markers"
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
            env=_command_env(ctx),
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
        bundle_root = _resolve_case_relative_dir(ctx, bundle_root)
        skills_dir = _resolve_case_relative_dir(ctx, skills_dir)
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
    registry.register("artifact_exists", artifact_exists_validator)
    registry.register("command", command_validator)
    registry.register("artifact_exec", artifact_exec_validator)
    registry.register("asan_command", asan_command_validator)
    registry.register("bundle_script", bundle_script_validator)
    return registry
