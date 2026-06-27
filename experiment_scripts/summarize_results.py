#!/usr/bin/env python3
"""Summarize consolidated experiment final records into Markdown/CSV."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


CHECK_KEYS = ("cve", "file", "function", "evidence", "root_cause")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))


def _hit(record: dict[str, Any], key: str) -> str:
    value = (record.get("checks") or {}).get(key)
    if not isinstance(value, dict):
        return "-"
    return "Y" if value.get("hit") else "N"


def _join(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value)


def _selected_skills(record: dict[str, Any]) -> list[str]:
    injection = record.get("skill_injection")
    if not isinstance(injection, dict):
        return []
    return [str(item) for item in injection.get("selected_skill_names") or []]


def _injection_history(record: dict[str, Any]) -> list[dict[str, Any]]:
    history = record.get("skill_injection_history")
    if isinstance(history, list):
        return [item for item in history if isinstance(item, dict)]
    injection = record.get("skill_injection")
    if isinstance(injection, dict):
        return [injection]
    return []


def _history_skills(history: list[dict[str, Any]], index: int) -> list[str]:
    if not history:
        return []
    try:
        item = history[index]
    except IndexError:
        return []
    return [str(skill) for skill in item.get("selected_skill_names") or []]


def _relevance_fields(record: dict[str, Any], selected_skills: list[str]) -> tuple[str, str]:
    relevance = record.get("skill_relevance") if isinstance(record.get("skill_relevance"), dict) else {}
    status = str(relevance.get("status") or "")
    relevant = relevance.get("relevant_skills") or []
    if status:
        return status, _join(relevant)
    if not selected_skills:
        return "no_selected_skills", ""
    non_infra = [skill for skill in selected_skills if not skill.startswith("skillclaw-")]
    if non_infra:
        return "legacy_has_non_infra_skill", _join(non_infra)
    return "legacy_only_infra_skills", ""


def _record_row(path: Path, record: dict[str, Any]) -> dict[str, Any]:
    feedback = record.get("feedback") if isinstance(record.get("feedback"), dict) else {}
    validation = record.get("validation") if isinstance(record.get("validation"), dict) else {}
    run = record.get("run") if isinstance(record.get("run"), dict) else {}
    selected_skills = _selected_skills(record)
    relevance_status, relevant_skills = _relevance_fields(record, selected_skills)
    history = _injection_history(record)
    first_selected = _history_skills(history, 0)
    latest_selected = _history_skills(history, -1)

    row: dict[str, Any] = {
        "file": path.name,
        "case_id": record.get("case_id") or "",
        "mode": record.get("mode") or "",
        "model": record.get("model") or "",
        "score": record.get("score"),
        "max_score": record.get("max_score"),
        "score_text": _score_text(record),
        "validation": validation.get("status") or "",
        "decision": feedback.get("decision") or "",
        "action": feedback.get("suggested_action") or "",
        "first_selected_skills": _join(first_selected),
        "selected_skills": _join(selected_skills),
        "latest_selected_skills": _join(latest_selected),
        "injection_turns": len(history),
        "injection_changed": bool(first_selected and latest_selected and first_selected != latest_selected),
        "skill_relevance": relevance_status,
        "relevant_skills": relevant_skills,
        "agent_ran": run.get("agent_ran", ""),
        "agent_status": run.get("status", ""),
    }
    for key in CHECK_KEYS:
        row[f"{key}_hit"] = _hit(record, key)
    return row


def _score_text(record: dict[str, Any]) -> str:
    score = record.get("score")
    max_score = record.get("max_score")
    if isinstance(score, (int, float)) and isinstance(max_score, (int, float)):
        return f"{score:g}/{max_score:g}"
    return ""


def collect_rows(paths: list[Path]) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(paths):
        if not path.is_file():
            continue
        record = _load_json(path)
        rows.append(_record_row(path, record))
    return rows


def _md_escape(value: Any) -> str:
    text = str(value if value is not None else "")
    return text.replace("|", "\\|").replace("\n", " ")


def write_markdown(rows: list[dict[str, Any]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    headers = [
        "case_id",
        "mode",
        "score_text",
        "cve_hit",
        "file_hit",
        "function_hit",
        "evidence_hit",
        "root_cause_hit",
        "validation",
        "selected_skills",
        "first_selected_skills",
        "latest_selected_skills",
        "injection_turns",
        "injection_changed",
        "skill_relevance",
        "decision",
        "action",
    ]

    lines = [
        "# Experiment Result Matrix",
        "",
        f"Generated: {now}",
        f"Records: {len(rows)}",
        "",
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(_md_escape(row.get(key, "")) for key in headers) + " |")
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- `Y/N` columns report whether the answer matched the case ground truth for that dimension.")
    lines.append("- `skill_relevance=only_infra_skills` means SkillClaw selected framework/self-inspection skills rather than task-specific vulnerability skills.")
    lines.append("- `decision/action` are feedback signals for later skill evolution; they are not human final judgments.")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_csv(rows: list[dict[str, Any]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "file",
        "case_id",
        "mode",
        "model",
        "score",
        "max_score",
        "score_text",
        "cve_hit",
        "file_hit",
        "function_hit",
        "evidence_hit",
        "root_cause_hit",
        "validation",
        "selected_skills",
        "first_selected_skills",
        "latest_selected_skills",
        "injection_turns",
        "injection_changed",
        "skill_relevance",
        "relevant_skills",
        "decision",
        "action",
        "agent_ran",
        "agent_status",
    ]
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def _resolve_inputs(args: argparse.Namespace) -> list[Path]:
    if args.inputs:
        return [Path(item) for item in args.inputs]
    records_dir = Path(args.records_dir)
    return sorted(records_dir.glob(args.pattern))


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="*", help="Final JSON files to summarize.")
    parser.add_argument("--records-dir", default="experiment_records")
    parser.add_argument("--pattern", default="*final*.json")
    parser.add_argument("--out-md", type=Path, default=Path("experiment_records/experiment_matrix_latest.md"))
    parser.add_argument("--out-csv", type=Path, default=Path("experiment_records/experiment_matrix_latest.csv"))
    args = parser.parse_args(argv)

    rows = collect_rows(_resolve_inputs(args))
    write_markdown(rows, args.out_md)
    write_csv(rows, args.out_csv)
    print(f"wrote {len(rows)} row(s) to {args.out_md} and {args.out_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
