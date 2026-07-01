#!/usr/bin/env python3
"""Compare two experiment final records and summarize the delta."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _check_hit(record: dict[str, Any], name: str) -> bool:
    checks = record.get("checks")
    if not isinstance(checks, dict):
        return False
    check = checks.get(name)
    return isinstance(check, dict) and bool(check.get("hit"))


def _validation_status(record: dict[str, Any]) -> str:
    validation = record.get("validation")
    if not isinstance(validation, dict):
        return ""
    return str(validation.get("status") or "")


def _validator_check_status(record: dict[str, Any], check_type: str) -> str:
    validation = record.get("validation")
    if not isinstance(validation, dict):
        return ""
    checks = validation.get("checks")
    if not isinstance(checks, list):
        return ""
    for item in checks:
        if isinstance(item, dict) and str(item.get("type") or "") == check_type:
            return str(item.get("status") or "")
    return ""


def _selected_skills(record: dict[str, Any]) -> list[str]:
    skill_injection = record.get("skill_injection")
    if not isinstance(skill_injection, dict):
        return []
    return [str(item) for item in skill_injection.get("selected_skill_names") or [] if str(item)]


def _summary(record: dict[str, Any]) -> dict[str, Any]:
    score = float(record.get("score") or 0.0)
    max_score = float(record.get("max_score") or 0.0)
    return {
        "case_id": str(record.get("case_id") or ""),
        "mode": str(record.get("mode") or ""),
        "model": str(record.get("model") or ""),
        "score": score,
        "max_score": max_score,
        "normalized_score": (score / max_score) if max_score else 0.0,
        "exact_cve_hit": _check_hit(record, "cve"),
        "file_hit": _check_hit(record, "file"),
        "function_hit": _check_hit(record, "function"),
        "evidence_hit": _check_hit(record, "evidence"),
        "root_cause_hit": _check_hit(record, "root_cause"),
        "validation_status": _validation_status(record),
        "artifact_exec_status": _validator_check_status(record, "artifact_exec"),
        "asan_status": _validator_check_status(record, "asan_command"),
        "feedback_decision": str((record.get("feedback") or {}).get("decision") or ""),
        "quality_flags": list((record.get("feedback") or {}).get("quality_flags") or []),
        "session_id": str(record.get("session_id") or ""),
        "session_id_source": str(record.get("session_id_source") or ""),
        "selected_skills": _selected_skills(record),
    }


def _status_changed(before: str, after: str) -> str:
    if before == after:
        return "unchanged"
    return f"{before or '(none)'} -> {after or '(none)'}"


def compare_records(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    before_summary = _summary(before)
    after_summary = _summary(after)
    delta = {
        "score_delta": round(after_summary["score"] - before_summary["score"], 4),
        "normalized_score_delta": round(after_summary["normalized_score"] - before_summary["normalized_score"], 4),
        "exact_cve_improved": (not before_summary["exact_cve_hit"]) and after_summary["exact_cve_hit"],
        "localization_regressed": (
            (before_summary["file_hit"] and not after_summary["file_hit"])
            or (before_summary["function_hit"] and not after_summary["function_hit"])
        ),
        "validation_change": _status_changed(before_summary["validation_status"], after_summary["validation_status"]),
        "artifact_exec_change": _status_changed(before_summary["artifact_exec_status"], after_summary["artifact_exec_status"]),
        "asan_change": _status_changed(before_summary["asan_status"], after_summary["asan_status"]),
        "feedback_change": _status_changed(before_summary["feedback_decision"], after_summary["feedback_decision"]),
        "quality_flags_removed": [flag for flag in before_summary["quality_flags"] if flag not in after_summary["quality_flags"]],
        "quality_flags_added": [flag for flag in after_summary["quality_flags"] if flag not in before_summary["quality_flags"]],
        "selected_skills_added": [item for item in after_summary["selected_skills"] if item not in before_summary["selected_skills"]],
        "selected_skills_removed": [item for item in before_summary["selected_skills"] if item not in after_summary["selected_skills"]],
    }
    return {
        "case_id": after_summary["case_id"] or before_summary["case_id"],
        "before": before_summary,
        "after": after_summary,
        "delta": delta,
    }


def render_markdown(result: dict[str, Any]) -> str:
    before = result["before"]
    after = result["after"]
    delta = result["delta"]
    lines = [
        f"# Experiment Compare: {result.get('case_id') or '(unknown)'}",
        "",
        "| Metric | Before | After |",
        "| --- | --- | --- |",
        f"| Score | `{before['score']}/{before['max_score']}` | `{after['score']}/{after['max_score']}` |",
        f"| Exact CVE | `{before['exact_cve_hit']}` | `{after['exact_cve_hit']}` |",
        f"| File hit | `{before['file_hit']}` | `{after['file_hit']}` |",
        f"| Function hit | `{before['function_hit']}` | `{after['function_hit']}` |",
        f"| Validation | `{before['validation_status']}` | `{after['validation_status']}` |",
        f"| Artifact exec | `{before['artifact_exec_status'] or '(none)'}` | `{after['artifact_exec_status'] or '(none)'}` |",
        f"| ASan | `{before['asan_status'] or '(none)'}` | `{after['asan_status'] or '(none)'}` |",
        f"| Feedback | `{before['feedback_decision'] or '(none)'}` | `{after['feedback_decision'] or '(none)'}` |",
        "",
        "## Delta",
        "",
        f"- score delta: `{delta['score_delta']}`",
        f"- exact CVE improved: `{delta['exact_cve_improved']}`",
        f"- localization regressed: `{delta['localization_regressed']}`",
        f"- validation change: `{delta['validation_change']}`",
        f"- artifact exec change: `{delta['artifact_exec_change']}`",
        f"- asan change: `{delta['asan_change']}`",
        f"- feedback change: `{delta['feedback_change']}`",
        f"- quality flags removed: `{', '.join(delta['quality_flags_removed']) or '(none)'}`",
        f"- quality flags added: `{', '.join(delta['quality_flags_added']) or '(none)'}`",
        f"- selected skills added: `{', '.join(delta['selected_skills_added']) or '(none)'}`",
        f"- selected skills removed: `{', '.join(delta['selected_skills_removed']) or '(none)'}`",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    parser.add_argument("--json-out", type=Path, default=None)
    parser.add_argument("--md-out", type=Path, default=None)
    args = parser.parse_args(argv)

    result = compare_records(_load_json(args.before), _load_json(args.after))
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.md_out:
        args.md_out.parent.mkdir(parents=True, exist_ok=True)
        args.md_out.write_text(render_markdown(result) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
