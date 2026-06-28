#!/usr/bin/env python3
"""Build evolver-ready skill feedback bundles from final experiment records.

The gate report is good for human triage.  This bundle is a stricter machine
interface: one compact JSON object per skill with dimension-level evidence that
an evolver can consume without re-reading whole conversations.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> Any:
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


def _hit(record: dict[str, Any], key: str) -> bool:
    checks = record.get("checks")
    if not isinstance(checks, dict):
        return False
    item = checks.get(key)
    return bool(isinstance(item, dict) and item.get("hit"))


def _check_expected(record: dict[str, Any], key: str) -> list[str]:
    checks = record.get("checks")
    if not isinstance(checks, dict):
        return []
    item = checks.get(key)
    if not isinstance(item, dict):
        return []
    return [str(value) for value in item.get("expected") or item.get("expected_terms") or []]


def _check_matched(record: dict[str, Any], key: str) -> list[str]:
    checks = record.get("checks")
    if not isinstance(checks, dict):
        return []
    item = checks.get(key)
    if not isinstance(item, dict):
        return []
    return [str(value) for value in item.get("matched") or []]


def _feedback(record: dict[str, Any]) -> dict[str, Any]:
    value = record.get("feedback")
    return value if isinstance(value, dict) else {}


def _validation(record: dict[str, Any]) -> dict[str, Any]:
    value = record.get("validation")
    return value if isinstance(value, dict) else {}


def _validation_checks(record: dict[str, Any]) -> list[dict[str, Any]]:
    validation = _validation(record)
    checks = validation.get("checks")
    return [item for item in checks if isinstance(item, dict)] if isinstance(checks, list) else []


def _predicted_cves(record: dict[str, Any]) -> list[str]:
    predictions = record.get("predictions")
    if isinstance(predictions, dict):
        return [str(item) for item in predictions.get("cves") or []]
    return []


def _normalized(record: dict[str, Any]) -> float | None:
    score = record.get("score")
    max_score = record.get("max_score")
    if isinstance(score, (int, float)) and isinstance(max_score, (int, float)) and max_score:
        return float(score) / float(max_score)
    return None


def _case_evidence(record: dict[str, Any]) -> dict[str, Any]:
    validation = _validation(record)
    feedback = _feedback(record)
    return {
        "case_id": record.get("case_id"),
        "mode": record.get("mode"),
        "model": record.get("model"),
        "session_id": record.get("session_id"),
        "score": record.get("score"),
        "max_score": record.get("max_score"),
        "normalized_score": _normalized(record),
        "feedback_decision": feedback.get("decision"),
        "suggested_action": feedback.get("suggested_action"),
        "quality_flags": list(feedback.get("quality_flags") or []),
        "validation_status": validation.get("status"),
        "hits": {
            "cve": _hit(record, "cve"),
            "file": _hit(record, "file"),
            "function": _hit(record, "function"),
            "evidence": _hit(record, "evidence"),
            "root_cause": _hit(record, "root_cause"),
        },
        "expected": {
            "cves": _check_expected(record, "cve"),
            "files": _check_expected(record, "file"),
            "functions": _check_expected(record, "function"),
        },
        "matched": {
            "cves": _check_matched(record, "cve"),
            "files": _check_matched(record, "file"),
            "functions": _check_matched(record, "function"),
        },
        "predicted_cves": _predicted_cves(record),
        "validator_checks": [
            {
                "name": item.get("name"),
                "type": item.get("type"),
                "status": item.get("status"),
                "allow_failure": bool(item.get("allow_failure")),
            }
            for item in _validation_checks(record)
        ],
    }


def _load_gate_map(path: Path | None) -> dict[str, dict[str, Any]]:
    if not path or not path.is_file():
        return {}
    value = _load_json(path)
    if not isinstance(value, list):
        return {}
    return {
        str(item.get("skill")): item
        for item in value
        if isinstance(item, dict) and item.get("skill")
    }


def _new_bundle(skill: str, gate: dict[str, Any] | None) -> dict[str, Any]:
    gate = gate or {}
    return {
        "skill": skill,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate_decision": gate.get("gate_decision") or "unknown",
        "gate_reasons": list(gate.get("reasons") or []),
        "gate_suggestions": list(gate.get("suggestions") or []),
        "summary": {
            "selected_runs": 0,
            "positive": 0,
            "neutral": 0,
            "negative": 0,
            "mean_score": None,
        },
        "dimensions": {
            "localization_success": 0,
            "cve_success": 0,
            "cve_calibration_miss": 0,
            "evidence_success": 0,
            "root_cause_success": 0,
            "validator_passed": 0,
            "validator_failed": 0,
            "dynamic_or_bundle_validation_passed": 0,
        },
        "revision_directives": [],
        "cases": [],
        "_scores": [],
    }


def _add_revision_directives(bundle: dict[str, Any]) -> None:
    directives = set(str(item) for item in bundle.get("gate_suggestions") or [] if str(item).strip())
    dimensions = bundle["dimensions"]
    if str(bundle.get("skill") or "").startswith("skillclaw-") and bundle.get("gate_decision") == "demote":
        directives = {
            item
            for item in directives
            if "retrieval" in item.lower() or "not selected" in item.lower() or "internals" in item.lower()
        }
        directives.add("Narrow retrieval so this infrastructure skill is selected only for SkillClaw-internal or catalog tasks.")
        bundle["revision_directives"] = sorted(directives)
        return
    if dimensions["cve_calibration_miss"]:
        directives.add(
            "Separate source localization from exact CVE identity; require advisory, patch, or version-range evidence before naming a CVE."
        )
    if bundle["summary"]["negative"]:
        directives.add("Inspect negative cases and remove or narrow misleading workflow steps.")
    if dimensions["validator_failed"]:
        directives.add("Do not publish or promote until failing validator evidence is explained or fixed.")
    if dimensions["cve_calibration_miss"] and dimensions["localization_success"] and not dimensions["cve_success"]:
        directives.add("Keep useful localization guidance, but add an explicit CVE-calibration section and uncertainty fallback.")
    bundle["revision_directives"] = sorted(directives)


def build_feedback_bundles(
    records: list[tuple[Path, dict[str, Any]]],
    *,
    gate_map: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    gate_map = gate_map or {}
    bundles: dict[str, dict[str, Any]] = {}
    for path, record in records:
        selected = _selected_skills(record)
        if not selected:
            continue
        feedback = _feedback(record)
        decision = str(feedback.get("decision") or "neutral")
        if decision not in {"positive", "neutral", "negative"}:
            decision = "neutral"
        evidence = _case_evidence(record)
        normalized = evidence.get("normalized_score")
        validation_status = evidence.get("validation_status")
        quality_flags = set(evidence.get("quality_flags") or [])
        dynamic_pass = any(
            item.get("status") == "passed" and str(item.get("type") or "") in {"bundle_script", "asan_command"}
            for item in evidence.get("validator_checks") or []
        )
        for skill in selected:
            bundle = bundles.setdefault(skill, _new_bundle(skill, gate_map.get(skill)))
            summary = bundle["summary"]
            dimensions = bundle["dimensions"]
            summary["selected_runs"] += 1
            summary[decision] += 1
            if isinstance(normalized, (int, float)):
                bundle["_scores"].append(float(normalized))
            if evidence["hits"]["file"] or evidence["hits"]["function"]:
                dimensions["localization_success"] += 1
            if evidence["hits"]["cve"]:
                dimensions["cve_success"] += 1
            if "cve_calibration_miss" in quality_flags:
                dimensions["cve_calibration_miss"] += 1
            if evidence["hits"]["evidence"]:
                dimensions["evidence_success"] += 1
            if evidence["hits"]["root_cause"]:
                dimensions["root_cause_success"] += 1
            if validation_status == "passed":
                dimensions["validator_passed"] += 1
            elif validation_status == "failed":
                dimensions["validator_failed"] += 1
            if dynamic_pass:
                dimensions["dynamic_or_bundle_validation_passed"] += 1
            bundle["cases"].append({"record": str(path), **evidence})

    output = []
    for bundle in bundles.values():
        scores = bundle.pop("_scores")
        bundle["summary"]["mean_score"] = round(sum(scores) / len(scores), 3) if scores else None
        _add_revision_directives(bundle)
        output.append(bundle)
    return sorted(
        output,
        key=lambda item: (
            str(item.get("gate_decision") or ""),
            -int(item["summary"]["selected_runs"]),
            str(item["skill"]),
        ),
    )


def collect_records(paths: list[Path]) -> list[tuple[Path, dict[str, Any]]]:
    records = []
    for path in sorted(paths):
        if path.is_file():
            value = _load_json(path)
            if isinstance(value, dict):
                records.append((path, value))
    return records


def write_json(bundles: list[dict[str, Any]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(bundles, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _md_escape(value: Any) -> str:
    if isinstance(value, list):
        value = "; ".join(str(item) for item in value)
    return str(value if value is not None else "").replace("|", "\\|").replace("\n", " ")


def write_markdown(bundles: list[dict[str, Any]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    headers = [
        "skill",
        "gate",
        "runs",
        "mean_score",
        "localization",
        "cve_hit",
        "cve_miss",
        "validator_passed",
        "directives",
    ]
    lines = [
        "# Skill Feedback Bundles",
        "",
        "This file summarizes evolver-ready, dimension-level feedback for selected skills.",
        "",
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for bundle in bundles:
        summary = bundle["summary"]
        dimensions = bundle["dimensions"]
        row = {
            "skill": bundle["skill"],
            "gate": bundle["gate_decision"],
            "runs": summary["selected_runs"],
            "mean_score": summary["mean_score"],
            "localization": dimensions["localization_success"],
            "cve_hit": dimensions["cve_success"],
            "cve_miss": dimensions["cve_calibration_miss"],
            "validator_passed": dimensions["validator_passed"],
            "directives": bundle["revision_directives"],
        }
        lines.append("| " + " | ".join(_md_escape(row[key]) for key in headers) + " |")
    lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")


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
    parser.add_argument("--gate-json", type=Path, default=Path("experiment_records/skill_gate_report_latest.json"))
    parser.add_argument("--out-json", type=Path, default=Path("experiment_records/skill_feedback_bundle_latest.json"))
    parser.add_argument("--out-md", type=Path, default=Path("experiment_records/skill_feedback_bundle_latest.md"))
    args = parser.parse_args(argv)

    bundles = build_feedback_bundles(
        collect_records(_resolve_inputs(args)),
        gate_map=_load_gate_map(args.gate_json),
    )
    write_json(bundles, args.out_json)
    write_markdown(bundles, args.out_md)
    print(f"wrote {len(bundles)} skill feedback bundle(s) to {args.out_json} and {args.out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
