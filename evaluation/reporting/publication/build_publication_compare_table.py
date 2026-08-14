#!/usr/bin/env python3
"""Build a paired comparison table from a fixed compare manifest."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))


def _load_manifest(path: Path) -> dict[str, Any]:
    value = _load_json(path)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _case_id_from_case_path(value: str) -> str:
    return Path(str(value)).stem


def _score_text(record: dict[str, Any]) -> str:
    score = record.get("score")
    max_score = record.get("max_score")
    if isinstance(score, (int, float)) and isinstance(max_score, (int, float)):
        return f"{score:g}/{max_score:g}"
    return ""


def _selected_skills(record: dict[str, Any]) -> str:
    injection = record.get("skill_injection")
    if not isinstance(injection, dict):
        return ""
    items = injection.get("selected_skill_names") or []
    return ", ".join(str(item) for item in items)


def _record_view(path: Path, record: dict[str, Any]) -> dict[str, Any]:
    confirmation = record.get("confirmation") if isinstance(record.get("confirmation"), dict) else {}
    validation = confirmation if confirmation else (record.get("validation") if isinstance(record.get("validation"), dict) else {})
    feedback = record.get("feedback") if isinstance(record.get("feedback"), dict) else {}
    return {
        "path": str(path.resolve()),
        "run_id": str(record.get("run_id") or ""),
        "case_id": str(record.get("case_id") or ""),
        "mode": str(record.get("mode") or ""),
        "model": str(record.get("model") or ""),
        "score": record.get("score"),
        "max_score": record.get("max_score"),
        "score_text": _score_text(record),
        "confirmation": str(validation.get("status") or ""),
        "validation": str(validation.get("status") or ""),
        "skill_relevance": str((record.get("skill_relevance") or {}).get("status") or ""),
        "decision": str(feedback.get("decision") or ""),
        "action": str(feedback.get("suggested_action") or ""),
        "selected_skills": _selected_skills(record),
    }


def collect_record_views(paths: list[Path]) -> list[dict[str, Any]]:
    views: list[dict[str, Any]] = []
    for path in sorted(paths):
        if not path.is_file():
            continue
        value = _load_json(path)
        if isinstance(value, dict):
            views.append(_record_view(path, value))
    return views


def _resolve_record_paths(records_dir: Path, pattern: str) -> list[Path]:
    return sorted(records_dir.rglob(pattern))


def build_paired_rows(manifest: dict[str, Any], record_views: list[dict[str, Any]]) -> list[dict[str, Any]]:
    comparison_modes = manifest.get("comparison_modes") or []
    ordered_modes = [str(item.get("mode") or "") for item in comparison_modes if isinstance(item, dict)]

    expected: dict[str, dict[str, dict[str, str]]] = {}
    for item in manifest.get("runs") or []:
        if not isinstance(item, dict):
            continue
        case_id = _case_id_from_case_path(str(item.get("case") or ""))
        mode = str(item.get("mode") or "")
        run_id = str(item.get("run_id") or "")
        if not case_id or not mode:
            continue
        expected.setdefault(case_id, {})[mode] = {"run_id": run_id}

    by_run_id = {
        str(view.get("run_id") or ""): view
        for view in record_views
        if str(view.get("run_id") or "").strip()
    }
    by_case_mode = {
        (str(view.get("case_id") or ""), str(view.get("mode") or "")): view
        for view in record_views
    }

    rows: list[dict[str, Any]] = []
    for case_id in sorted(expected):
        row: dict[str, Any] = {"case_id": case_id}
        skill_score = None
        direct_score = None
        for mode in ordered_modes:
            spec = expected.get(case_id, {}).get(mode, {})
            match_type = ""
            matched = by_run_id.get(spec.get("run_id") or "")
            if matched is not None:
                match_type = "exact_run_id"
            if matched is None:
                matched = by_case_mode.get((case_id, mode))
                if matched is not None:
                    match_type = "fallback_case_mode"
            prefix = mode.replace("-", "_")
            if matched is None:
                row[f"{prefix}_status"] = "missing"
                row[f"{prefix}_score_text"] = ""
                row[f"{prefix}_confirmation"] = ""
                row[f"{prefix}_skill_relevance"] = ""
                row[f"{prefix}_decision"] = ""
                row[f"{prefix}_action"] = ""
                row[f"{prefix}_selected_skills"] = ""
                row[f"{prefix}_record"] = ""
                row[f"{prefix}_match_type"] = ""
                continue

            row[f"{prefix}_status"] = "present"
            row[f"{prefix}_score_text"] = matched.get("score_text", "")
            row[f"{prefix}_confirmation"] = matched.get("confirmation", matched.get("validation", ""))
            row[f"{prefix}_skill_relevance"] = matched.get("skill_relevance", "")
            row[f"{prefix}_decision"] = matched.get("decision", "")
            row[f"{prefix}_action"] = matched.get("action", "")
            row[f"{prefix}_selected_skills"] = matched.get("selected_skills", "")
            row[f"{prefix}_record"] = matched.get("path", "")
            row[f"{prefix}_match_type"] = match_type
            score_value = matched.get("score")
            if mode == "skillclaw-inline-guarded" and isinstance(score_value, (int, float)):
                skill_score = float(score_value)
            if mode == "direct-deepseek-guarded" and isinstance(score_value, (int, float)):
                direct_score = float(score_value)

        row["score_delta_skill_minus_direct"] = (
            "" if skill_score is None or direct_score is None else f"{skill_score - direct_score:g}"
        )
        rows.append(row)
    return rows


def _md_escape(value: Any) -> str:
    return str(value if value is not None else "").replace("|", "\\|").replace("\n", " ")


def write_markdown(rows: list[dict[str, Any]], manifest: dict[str, Any], out_path: Path) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    headers = [
        "case_id",
        "skillclaw_inline_guarded_status",
        "skillclaw_inline_guarded_score_text",
        "skillclaw_inline_guarded_confirmation",
        "skillclaw_inline_guarded_match_type",
        "skillclaw_inline_guarded_skill_relevance",
        "direct_deepseek_guarded_status",
        "direct_deepseek_guarded_score_text",
        "direct_deepseek_guarded_confirmation",
        "direct_deepseek_guarded_match_type",
        "score_delta_skill_minus_direct",
    ]
    lines = [
        "# Paired Compare Matrix",
        "",
        f"Generated: {now}",
        f"Protocol: `{manifest.get('name', 'unnamed-compare-protocol')}`",
        f"Cases: {len(rows)}",
        "",
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        normalized = {key.replace("-", "_"): value for key, value in row.items()}
        lines.append("| " + " | ".join(_md_escape(normalized.get(key, "")) for key in headers) + " |")
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- `status=missing` means the compare protocol expects that run, but no matching final record has been collected yet.",
            "- `match_type=exact_run_id` means the final record matches the protocol's expected `run_id` exactly.",
            "- `match_type=fallback_case_mode` means no exact protocol run was found; the table reused an older record with the same `case_id` and `mode`.",
            "- `score_delta_skill_minus_direct` is only computed when both paired runs are present.",
            "- `skillclaw-inline-guarded_skill_relevance` is kept in the paired table because retrieval quality is part of the experimental question.",
        ]
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_csv(rows: list[dict[str, Any]], out_path: Path) -> None:
    fieldnames = [
        "case_id",
        "skillclaw_inline_guarded_status",
        "skillclaw_inline_guarded_score_text",
        "skillclaw_inline_guarded_confirmation",
        "skillclaw_inline_guarded_match_type",
        "skillclaw_inline_guarded_skill_relevance",
        "skillclaw_inline_guarded_decision",
        "skillclaw_inline_guarded_action",
        "skillclaw_inline_guarded_selected_skills",
        "skillclaw_inline_guarded_record",
        "direct_deepseek_guarded_status",
        "direct_deepseek_guarded_score_text",
        "direct_deepseek_guarded_confirmation",
        "direct_deepseek_guarded_match_type",
        "direct_deepseek_guarded_skill_relevance",
        "direct_deepseek_guarded_decision",
        "direct_deepseek_guarded_action",
        "direct_deepseek_guarded_selected_skills",
        "direct_deepseek_guarded_record",
        "score_delta_skill_minus_direct",
    ]
    normalized_rows = []
    for row in rows:
        normalized = {}
        for key, value in row.items():
            normalized[key.replace("-", "_")] = value
        normalized_rows.append(normalized)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in normalized_rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def build_publication_compare_table(
    manifest_path: Path,
    *,
    records_dir: Path,
    pattern: str,
    out_md: Path,
    out_csv: Path,
) -> dict[str, Any]:
    manifest = _load_manifest(manifest_path)
    record_views = collect_record_views(_resolve_record_paths(records_dir, pattern))
    rows = build_paired_rows(manifest, record_views)
    write_markdown(rows, manifest, out_md)
    write_csv(rows, out_csv)
    return {
        "manifest": str(manifest_path.resolve()),
        "records_scanned": len(record_views),
        "rows": len(rows),
        "out_md": str(out_md.resolve()),
        "out_csv": str(out_csv.resolve()),
    }


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("reports/publication/compare_manifest.json"),
    )
    parser.add_argument("--records-dir", type=Path, default=Path("reports"))
    parser.add_argument("--pattern", default="*final*.json")
    parser.add_argument("--out-md", type=Path, default=Path("reports/publication/compare.md"))
    parser.add_argument("--out-csv", type=Path, default=Path("reports/publication/compare.csv"))
    args = parser.parse_args(argv)

    result = build_publication_compare_table(
        args.manifest.resolve(),
        records_dir=args.records_dir.resolve(),
        pattern=args.pattern,
        out_md=args.out_md.resolve(),
        out_csv=args.out_csv.resolve(),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


summarize_compare_manifest = build_publication_compare_table

