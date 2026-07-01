#!/usr/bin/env python3
"""Aggregate final experiment records into skill-level feedback evidence.

The ordinary experiment matrix is run-centric. This script answers a different
question: when SkillClaw selected a server-side skill, did the downstream
answer and validators produce positive, neutral, or negative evidence for that
skill?
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _selected_skills(record: dict[str, Any]) -> list[str]:
    injection = record.get("skill_injection")
    if not isinstance(injection, dict):
        return []
    return [str(item) for item in injection.get("selected_skill_names") or [] if str(item).strip()]


def _validation_status(record: dict[str, Any]) -> str:
    validation = record.get("validation")
    if isinstance(validation, dict):
        return str(validation.get("status") or "")
    return ""


def _feedback_decision(record: dict[str, Any]) -> str:
    feedback = record.get("feedback")
    if isinstance(feedback, dict):
        return str(feedback.get("decision") or "")
    score = _as_float(record.get("score"))
    max_score = _as_float(record.get("max_score"))
    if max_score and score / max_score >= 0.8:
        return "positive"
    if max_score and score / max_score < 0.5:
        return "negative"
    return "neutral"


def _feedback_action(record: dict[str, Any]) -> str:
    feedback = record.get("feedback")
    if isinstance(feedback, dict):
        return str(feedback.get("suggested_action") or "")
    return ""


def _hit(record: dict[str, Any], key: str) -> bool:
    checks = record.get("checks")
    if not isinstance(checks, dict):
        return False
    item = checks.get(key)
    return bool(isinstance(item, dict) and item.get("hit"))


def _normalized_score(record: dict[str, Any]) -> float | None:
    score = record.get("score")
    max_score = record.get("max_score")
    if isinstance(score, (int, float)) and isinstance(max_score, (int, float)) and max_score:
        return float(score) / float(max_score)
    return None


def _new_bucket(skill: str) -> dict[str, Any]:
    return {
        "skill": skill,
        "selected_count": 0,
        "positive": 0,
        "neutral": 0,
        "negative": 0,
        "mean_score": None,
        "validation_passed": 0,
        "validation_partial": 0,
        "validation_failed": 0,
        "artifact_generated": 0,
        "artifact_execution_passed": 0,
        "cve_hits": 0,
        "file_hits": 0,
        "function_hits": 0,
        "evidence_hits": 0,
        "root_cause_hits": 0,
        "cases": set(),
        "modes": set(),
        "actions": defaultdict(int),
        "_scores": [],
    }


def build_skill_feedback(records: list[tuple[Path, dict[str, Any]]]) -> list[dict[str, Any]]:
    buckets: dict[str, dict[str, Any]] = {}
    for path, record in records:
        skills = _selected_skills(record)
        if not skills:
            continue
        decision = _feedback_decision(record) or "neutral"
        normalized = _normalized_score(record)
        validation = _validation_status(record)
        validation_checks = (
            record.get("validation", {}).get("checks")
            if isinstance(record.get("validation"), dict)
            else []
        )
        artifact_generated = any(
            isinstance(item, dict)
            and str(item.get("type") or "") == "artifact_exists"
            and str(item.get("status") or "") == "passed"
            for item in (validation_checks or [])
        )
        artifact_execution_passed = any(
            isinstance(item, dict)
            and str(item.get("type") or "") == "artifact_exec"
            and str(item.get("status") or "") == "passed"
            for item in (validation_checks or [])
        )
        for skill in skills:
            bucket = buckets.setdefault(skill, _new_bucket(skill))
            bucket["selected_count"] += 1
            if decision not in {"positive", "neutral", "negative"}:
                decision = "neutral"
            bucket[decision] += 1
            if normalized is not None:
                bucket["_scores"].append(normalized)
            if validation == "passed":
                bucket["validation_passed"] += 1
            elif validation == "partial":
                bucket["validation_partial"] += 1
            elif validation == "failed":
                bucket["validation_failed"] += 1
            if artifact_generated:
                bucket["artifact_generated"] += 1
            if artifact_execution_passed:
                bucket["artifact_execution_passed"] += 1
            for key in ("cve", "file", "function", "evidence", "root_cause"):
                if _hit(record, key):
                    bucket[f"{key}_hits"] += 1
            bucket["cases"].add(str(record.get("case_id") or path.stem))
            bucket["modes"].add(str(record.get("mode") or ""))
            action = _feedback_action(record)
            if action:
                bucket["actions"][action] += 1

    rows = []
    for bucket in buckets.values():
        scores = bucket.pop("_scores")
        actions = bucket["actions"]
        bucket["actions"] = ", ".join(f"{key}:{value}" for key, value in sorted(actions.items()))
        bucket["cases"] = ", ".join(sorted(item for item in bucket["cases"] if item))
        bucket["modes"] = ", ".join(sorted(item for item in bucket["modes"] if item))
        bucket["mean_score"] = round(sum(scores) / len(scores), 3) if scores else None
        rows.append(bucket)
    return sorted(rows, key=lambda item: (item["positive"], item["selected_count"], item["mean_score"] or 0), reverse=True)


def collect_records(paths: list[Path]) -> list[tuple[Path, dict[str, Any]]]:
    records = []
    for path in sorted(paths):
        if not path.is_file():
            continue
        records.append((path, _load_json(path)))
    return records


def _md_escape(value: Any) -> str:
    return str(value if value is not None else "").replace("|", "\\|").replace("\n", " ")


def write_markdown(rows: list[dict[str, Any]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    headers = [
        "skill",
        "selected_count",
        "positive",
        "neutral",
        "negative",
        "mean_score",
        "validation_passed",
        "validation_partial",
        "validation_failed",
        "artifact_generated",
        "artifact_execution_passed",
        "file_hits",
        "function_hits",
        "cve_hits",
        "actions",
        "cases",
    ]
    lines = [
        "# Skill Feedback Summary",
        "",
        "This file aggregates final experiment records into skill-level feedback evidence.",
        "It is not a global quality score; it only reflects the current benchmark cases.",
        "",
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(_md_escape(row.get(key, "")) for key in headers) + " |")
    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append("- `positive/neutral/negative` comes from the run-level feedback decision.")
    lines.append("- `mean_score` is the mean normalized localization score across selected runs.")
    lines.append("- `artifact_generated` / `artifact_execution_passed` summarize confirmation-oriented artifact checks.")
    lines.append("- A skill with few selections should be treated as anecdotal evidence, not a stable ranking.")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_csv(rows: list[dict[str, Any]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "skill",
        "selected_count",
        "positive",
        "neutral",
        "negative",
        "mean_score",
        "validation_passed",
        "validation_partial",
        "validation_failed",
        "artifact_generated",
        "artifact_execution_passed",
        "cve_hits",
        "file_hits",
        "function_hits",
        "evidence_hits",
        "root_cause_hits",
        "actions",
        "cases",
        "modes",
    ]
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def _resolve_inputs(args: argparse.Namespace) -> list[Path]:
    if args.inputs:
        return [Path(item) for item in args.inputs]
    return sorted(Path(args.records_dir).glob(args.pattern))


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="*", help="Final JSON records.")
    parser.add_argument("--records-dir", default="experiment_records")
    parser.add_argument("--pattern", default="*final*.json")
    parser.add_argument("--out-md", type=Path, default=Path("experiment_records/skill_feedback_latest.md"))
    parser.add_argument("--out-csv", type=Path, default=Path("experiment_records/skill_feedback_latest.csv"))
    args = parser.parse_args(argv)

    rows = build_skill_feedback(collect_records(_resolve_inputs(args)))
    write_markdown(rows, args.out_md)
    write_csv(rows, args.out_csv)
    print(f"wrote {len(rows)} skill row(s) to {args.out_md} and {args.out_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
