#!/usr/bin/env python3
"""Run one vulnerability-localization experiment case end to end.

The runner intentionally composes the smaller experiment scripts instead of
replacing them.  It can either call Claude Code or reuse an existing agent
output for dry-runs and regression tests.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from experiment_scripts.build_result_record import _select_injection, _select_injection_history
    from experiment_scripts.print_case_prompt import get_case_prompt
    from experiment_scripts.score_agent_output import score_output
    from experiment_validation.core import assess_skill_relevance, build_feedback
    from experiment_validation.runner import run_case_validators
except ImportError:  # pragma: no cover - direct script execution from copied folders.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from experiment_scripts.build_result_record import _select_injection, _select_injection_history
    from experiment_scripts.print_case_prompt import get_case_prompt
    from experiment_scripts.score_agent_output import score_output
    from experiment_validation.core import assess_skill_relevance, build_feedback
    from experiment_validation.runner import run_case_validators


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_jsonl(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False) + "\n")


def expand_path(path_text: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(path_text)))


def resolve_root(case: dict[str, Any], override: str | None) -> Path:
    if override:
        return expand_path(override)
    target = case.get("target", {}) if isinstance(case.get("target"), dict) else {}
    return expand_path(str(target.get("source_root") or "."))


def infer_model(settings_path: Path | None = None) -> str:
    settings_path = settings_path or (Path.home() / ".claude" / "settings.json")
    try:
        data = load_json(settings_path)
    except OSError:
        return ""
    env = data.get("env", {}) if isinstance(data.get("env"), dict) else {}
    return str(env.get("ANTHROPIC_MODEL") or "")


def slug(text: str) -> str:
    allowed = []
    for char in str(text):
        if char.isalnum() or char in {"-", "_", "."}:
            allowed.append(char)
        else:
            allowed.append("-")
    value = "".join(allowed).strip("-")
    return value or "run"


def make_run_id(case_id: str, mode: str) -> str:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{slug(case_id)}-{slug(mode)}-{stamp}"


def run_paths(output_dir: Path, run_id: str) -> dict[str, Path]:
    return {
        "prompt": output_dir / f"{run_id}-prompt.txt",
        "raw": output_dir / f"{run_id}-raw.txt",
        "stderr": output_dir / f"{run_id}-stderr.txt",
        "meta": output_dir / f"{run_id}-run.meta",
        "agent_json": output_dir / f"{run_id}-agent.json",
        "score": output_dir / f"{run_id}-score.json",
        "validation": output_dir / f"{run_id}-validation.json",
        "final": output_dir / f"{run_id}-final.json",
    }


def extract_json_object(text: str) -> dict[str, Any] | None:
    stripped = text.lstrip("\ufeff").strip()
    if not stripped:
        return None
    try:
        obj = json.loads(stripped)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        pass

    if "```" in stripped:
        parts = stripped.split("```")
        for idx, part in enumerate(parts):
            candidate = part
            if idx % 2 == 1 and candidate.lstrip().lower().startswith("json"):
                candidate = candidate.lstrip()[4:]
            candidate = candidate.strip()
            if not candidate:
                continue
            try:
                obj = json.loads(candidate)
                if isinstance(obj, dict):
                    return obj
            except json.JSONDecodeError:
                continue

    decoder = json.JSONDecoder()
    for idx, char in enumerate(stripped):
        if char != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(stripped[idx:])
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            return obj
    return None


def run_agent(
    *,
    claude_cmd: str,
    prompt: str,
    cwd: Path,
    raw_path: Path,
    stderr_path: Path,
    timeout_seconds: int,
) -> int:
    command = [
        claude_cmd,
        "-p",
        "--dangerously-skip-permissions",
        "--output-format",
        "text",
    ]
    with raw_path.open("w", encoding="utf-8", errors="replace") as stdout:
        with stderr_path.open("w", encoding="utf-8", errors="replace") as stderr:
            completed = subprocess.run(
                command,
                input=prompt,
                text=True,
                cwd=cwd,
                stdout=stdout,
                stderr=stderr,
                timeout=timeout_seconds,
                check=False,
            )
    return int(completed.returncode)


def load_optional_json(path: Path | None) -> Any:
    if not path or not path.is_file():
        return None
    text = path.read_text(encoding="utf-8-sig", errors="replace").strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        rows = []
        for line in text.splitlines():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return rows


def build_final_record(
    *,
    case: dict[str, Any],
    mode: str,
    model: str,
    session_id: str,
    score: dict[str, Any],
    validation: dict[str, Any],
    injection_json: Path | None,
) -> dict[str, Any]:
    injection_value = load_optional_json(injection_json)
    injection = _select_injection(injection_value, session_id)
    injection_history = _select_injection_history(injection_value, session_id)
    selected_skills = []
    if isinstance(injection, dict):
        selected_skills = list(injection.get("selected_skill_names") or [])
    skill_relevance = assess_skill_relevance(case=case, selected_skills=selected_skills)
    record = {
        "case_id": case.get("case_id"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "model": model,
        "session_id": session_id,
        "score": score.get("score"),
        "max_score": score.get("max_score"),
        "checks": score.get("checks"),
        "predictions": score.get("predictions"),
        "skill_injection": injection,
        "skill_injection_history": injection_history,
        "skill_relevance": skill_relevance,
        "validation": validation,
    }
    record["feedback"] = build_feedback(
        score_result=score,
        validation_result=validation,
        skill_injection=injection,
        skill_relevance=skill_relevance,
    )
    return record


def run_case(args: argparse.Namespace) -> dict[str, Any]:
    case = load_json(args.case)
    case_id = str(case.get("case_id") or args.case.stem)
    run_id = args.run_id or make_run_id(case_id, args.mode)
    output_dir = expand_path(args.output_dir)
    paths = run_paths(output_dir, run_id)
    root = resolve_root(case, args.root)
    prompt = get_case_prompt(case, args.mode)
    model = args.model if args.model != "auto" else infer_model()

    output_dir.mkdir(parents=True, exist_ok=True)
    paths["prompt"].write_text(prompt + "\n", encoding="utf-8")

    meta = {
        "case_id": case_id,
        "run_id": run_id,
        "mode": args.mode,
        "model": model,
        "target_root": str(root),
        "start": datetime.now(timezone.utc).isoformat(),
        "agent_ran": False,
        "status": None,
    }

    if args.agent_output:
        source = expand_path(args.agent_output)
        raw_text = source.read_text(encoding="utf-8-sig", errors="replace")
        paths["raw"].write_text(raw_text, encoding="utf-8")
        paths["stderr"].write_text("", encoding="utf-8")
        meta["status"] = 0
    elif args.no_run_agent:
        paths["raw"].write_text("", encoding="utf-8")
        paths["stderr"].write_text("", encoding="utf-8")
        meta["status"] = "skipped"
    else:
        meta["agent_ran"] = True
        try:
            meta["status"] = run_agent(
                claude_cmd=args.claude_cmd,
                prompt=prompt,
                cwd=root,
                raw_path=paths["raw"],
                stderr_path=paths["stderr"],
                timeout_seconds=args.timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            meta["status"] = "timeout"
            paths["stderr"].write_text(
                f"timeout after {args.timeout_seconds} seconds\n",
                encoding="utf-8",
            )

    meta["end"] = datetime.now(timezone.utc).isoformat()
    write_json(paths["meta"], meta)

    raw_text = paths["raw"].read_text(encoding="utf-8-sig", errors="replace")
    agent_json = extract_json_object(raw_text)
    score_input_text = raw_text
    if agent_json is not None:
        write_json(paths["agent_json"], agent_json)
        score_input_text = json.dumps(agent_json, ensure_ascii=False)

    score = score_output(case, score_input_text)
    score["mode"] = args.mode
    write_json(paths["score"], score)

    validation = run_case_validators(
        case,
        root,
        case_path=args.case,
        agent_output_path=paths["agent_json"] if agent_json is not None else paths["raw"],
        skip_commands=args.skip_commands,
    )
    write_json(paths["validation"], validation)

    final = build_final_record(
        case=case,
        mode=args.mode,
        model=model,
        session_id=args.session_id,
        score=score,
        validation=validation,
        injection_json=args.injection_json,
    )
    final["run_id"] = run_id
    final["run"] = meta
    final["artifacts"] = {key: str(value) for key, value in paths.items()}
    write_json(paths["final"], final)
    if args.final_records:
        append_jsonl(expand_path(args.final_records), final)
    return final


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", type=Path, help="Path to experiment case JSON.")
    parser.add_argument("--mode", default="skillclaw-inline")
    parser.add_argument("--root", default=None, help="Override target source root.")
    parser.add_argument("--output-dir", default="results")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--model", default="auto")
    parser.add_argument("--session-id", default="")
    parser.add_argument("--injection-json", type=Path, default=None)
    parser.add_argument("--agent-output", default="", help="Reuse an existing agent output file.")
    parser.add_argument("--no-run-agent", action="store_true", help="Only write prompt and run post-processing.")
    parser.add_argument("--claude-cmd", default="claude")
    parser.add_argument("--timeout-seconds", type=int, default=2700)
    parser.add_argument("--skip-commands", action="store_true")
    parser.add_argument("--final-records", default="results/final_records.jsonl")
    parser.add_argument("--strict-exit", action="store_true")
    args = parser.parse_args(argv)

    final = run_case(args)
    print(json.dumps(final, ensure_ascii=False, indent=2))
    if args.strict_exit and final.get("validation", {}).get("status") == "failed":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
