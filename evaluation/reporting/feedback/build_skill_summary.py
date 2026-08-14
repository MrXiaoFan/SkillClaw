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

try:
    from evaluation.confirmation.core import classify_skill_role
except ImportError:  # pragma: no cover - direct script execution.
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from evaluation.confirmation.core import classify_skill_role


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))


def _preferred_record_path(path: Path) -> Path:
    if path.name == "final.json":
        enriched = path.with_name("final-enriched.json")
        if enriched.exists():
            return enriched
        return path
    suffix = "-final.json"
    if path.name.endswith(suffix):
        enriched = path.with_name(path.name[: -len(suffix)] + "-final-enriched.json")
        if enriched.exists():
            return enriched
    return path


def _dedupe_paths(paths: list[Path]) -> list[Path]:
    seen: set[str] = set()
    ordered: list[Path] = []
    for path in paths:
        preferred = _preferred_record_path(path)
        key = str(preferred.resolve()) if preferred.exists() else str(preferred)
        if key in seen:
            continue
        seen.add(key)
        ordered.append(preferred)
    return ordered


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


def _confirmation_status(record: dict[str, Any]) -> str:
    confirmation = record.get("confirmation")
    if isinstance(confirmation, dict):
        return str(confirmation.get("status") or "")
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
        "confirmation_passed": 0,
        "confirmation_partial": 0,
        "confirmation_failed": 0,
        "validation_passed": 0,
        "validation_partial": 0,
        "validation_failed": 0,
        "artifact_generated": 0,
        "artifact_execution_passed": 0,
        "relevant_selected": 0,
        "mismatched_selected": 0,
        "infra_selected": 0,
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
        confirmation_status = _confirmation_status(record)
        confirmation = record.get("confirmation")
        if isinstance(confirmation, dict):
            confirmation_checks = confirmation.get("checks") or []
        else:
            confirmation_checks = (
                record.get("validation", {}).get("checks")
                if isinstance(record.get("validation"), dict)
                else []
            )
        artifact_generated = any(
            isinstance(item, dict)
            and str(item.get("type") or "") == "artifact_exists"
            and str(item.get("status") or "") == "passed"
            for item in (confirmation_checks or [])
        )
        artifact_execution_passed = any(
            isinstance(item, dict)
            and str(item.get("type") or "") == "artifact_exec"
            and str(item.get("status") or "") == "passed"
            for item in (confirmation_checks or [])
        )
        for skill in skills:
            bucket = buckets.setdefault(skill, _new_bucket(skill))
            bucket["selected_count"] += 1
            skill_decision = decision if decision in {"positive", "neutral", "negative"} else "neutral"
            role = classify_skill_role(record.get("skill_relevance"), skill)
            if role == "relevant":
                bucket["relevant_selected"] += 1
            elif role == "mismatched":
                bucket["mismatched_selected"] += 1
                skill_decision = "neutral"
            elif role == "infrastructure":
                bucket["infra_selected"] += 1
                skill_decision = "neutral"
            bucket[skill_decision] += 1
            if normalized is not None:
                bucket["_scores"].append(normalized)
            if confirmation_status == "passed":
                bucket["confirmation_passed"] += 1
                bucket["validation_passed"] += 1
            elif confirmation_status == "partial":
                bucket["confirmation_partial"] += 1
                bucket["validation_partial"] += 1
            elif confirmation_status == "failed":
                bucket["confirmation_failed"] += 1
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
        "confirmation_passed",
        "confirmation_partial",
        "confirmation_failed",
        "artifact_generated",
        "artifact_execution_passed",
        "relevant_selected",
        "mismatched_selected",
        "infra_selected",
        "file_hits",
        "function_hits",
        "cve_hits",
        "actions",
        "cases",
    ]
    lines = [
        "# 技能反馈汇总",
        "",
        "这份文件把 final record 聚合成技能级反馈证据。",
        "它不是全局质量分，只反映当前基准案例集中的表现。",
        "",
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(_md_escape(row.get(key, "")) for key in headers) + " |")
    lines.append("")
    lines.append("## 解读")
    lines.append("")
    lines.append("- `positive/neutral/negative` 来自 run 级别的反馈决策。")
    lines.append("- `mismatched_selected` 表示该技能虽然被选中，但与任务并不对齐，因此不应获得正向 credit。")
    lines.append("- `mean_score` 是该技能被选中时的平均归一化定位分。")
    lines.append("- `artifact_generated` / `artifact_execution_passed` 汇总的是 confirmation 导向的工件检查结果。")
    lines.append("- 如果某个技能的样本数很少，只能视为轶事性证据，不能直接当稳定排序。")
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
        "confirmation_passed",
        "confirmation_partial",
        "confirmation_failed",
        "artifact_generated",
        "artifact_execution_passed",
        "relevant_selected",
        "mismatched_selected",
        "infra_selected",
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
        return _dedupe_paths([Path(item) for item in args.inputs])
    return _dedupe_paths(sorted(Path(args.records_dir).glob(args.pattern)))


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="*", help="Final JSON records.")
    parser.add_argument("--records-dir", default="reports")
    parser.add_argument("--pattern", default="*final*.json")
    parser.add_argument("--out-md", type=Path, default=Path("reports/current/skill_feedback.md"))
    parser.add_argument("--out-csv", type=Path, default=Path("reports/current/skill_feedback.csv"))
    args = parser.parse_args(argv)

    rows = build_skill_feedback(collect_records(_resolve_inputs(args)))
    write_markdown(rows, args.out_md)
    write_csv(rows, args.out_csv)
    print(f"wrote {len(rows)} skill row(s) to {args.out_md} and {args.out_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


