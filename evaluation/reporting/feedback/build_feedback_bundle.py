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

try:
    from evaluation.confirmation.core import classify_skill_role
except ImportError:  # pragma: no cover - direct script execution.
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from evaluation.confirmation.core import classify_skill_role
NO_SKILL_KEY = "__no_skill__"


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


def _matches_case_filter(record: dict[str, Any], allowed_case_ids: set[str] | None) -> bool:
    if not allowed_case_ids:
        return True
    case_id = str(record.get("case_id") or "").strip()
    return case_id in allowed_case_ids


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


def _confirmation(record: dict[str, Any]) -> dict[str, Any]:
    confirmation = record.get("confirmation")
    if isinstance(confirmation, dict) and str(confirmation.get("status") or "").strip():
        return confirmation
    value = record.get("validation")
    return value if isinstance(value, dict) else {}


def _confirmation_checks(record: dict[str, Any]) -> list[dict[str, Any]]:
    confirmation = _confirmation(record)
    checks = confirmation.get("checks")
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


def _record_evidence(record: dict[str, Any]) -> dict[str, Any]:
    confirmation = _confirmation(record)
    feedback = _feedback(record)
    validator_checks = [
        {
            "name": item.get("name"),
            "type": item.get("type"),
            "status": item.get("status"),
            "allow_failure": bool(item.get("allow_failure")),
        }
        for item in _confirmation_checks(record)
    ]
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
        "confirmation_status": confirmation.get("status"),
        "validation_status": confirmation.get("status"),
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
        "validator_checks": validator_checks,
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
            "relevant_selected": 0,
            "mismatched_selected": 0,
            "infra_selected": 0,
            "positive": 0,
            "neutral": 0,
            "negative": 0,
            "mean_score": None,
        },
        "dimensions": {
            "localization_success": 0,
            "cve_success": 0,
            "cve_identity_miss": 0,
            "evidence_success": 0,
            "root_cause_success": 0,
            "validator_passed": 0,
            "validator_failed": 0,
            "dynamic_or_bundle_confirmation_passed": 0,
            "dynamic_or_bundle_validation_passed": 0,
            "artifact_generated": 0,
            "artifact_execution_passed": 0,
        },
        "revision_directives": [],
        "revision_templates": [],
        "cases": [],
        "_scores": [],
    }


def _add_revision_templates(bundle: dict[str, Any]) -> None:
    templates: list[dict[str, Any]] = []
    dimensions = bundle["dimensions"]
    if dimensions["cve_identity_miss"]:
        templates.append(
            {
                "template_id": "cve_identity_miss",
                "title": "把漏洞定位与精确 CVE 归属分开处理",
                "when_to_apply": (
                    "当定位/根因证据已经较强，但预测出的 CVE 缺失、不稳定或反复出错时使用。"
                ),
                "required_changes": [
                    "明确写出：仅靠源码级定位不能直接命名某个 CVE。",
                    "只有在 advisory、patch、commit 或版本范围证据存在时，才能输出精确 CVE ID。",
                    "当只有定位证据而没有身份确认时，必须提供类似“CVE uncertain”的回退表述。",
                    "除非有相反证据，否则应保留已有的强定位与根因指导。",
                ],
                "anti_patterns": [
                    "不要用邻近 CVE 例子代替真正的身份确认依据。",
                    "不要把“定位成功”和“精确识别 CVE”合并成一条判断规则。",
                    "不要因为 CVE 识别失败，就把有价值的 parser/binary/source 指导一起删掉。",
                ],
                "suggested_history_note": (
                    "这次修改只针对 CVE 身份识别，原有定位流程应刻意保留。"
                ),
            }
        )
    bundle["revision_templates"] = templates


def _add_revision_directives(bundle: dict[str, Any]) -> None:
    directives = set(str(item) for item in bundle.get("gate_suggestions") or [] if str(item).strip())
    dimensions = bundle["dimensions"]
    if str(bundle.get("skill") or "").startswith("skillclaw-") and bundle.get("gate_decision") == "demote":
        directives = {
            item
            for item in directives
            if "retrieval" in item.lower() or "not selected" in item.lower() or "internals" in item.lower()
        }
        directives.add("收紧检索范围，让该基础设施类技能只在 SkillClaw 内部或技能目录类任务中被选中。")
        bundle["revision_directives"] = sorted(directives)
        return
    if dimensions["cve_identity_miss"]:
        directives.add(
            "把源码定位与精确 CVE 识别分开；只有在 advisory、patch 或版本范围证据存在时，才能命名 CVE。"
        )
    if bundle["summary"]["negative"]:
        directives.add("检查负向案例，删除或收窄会造成误导的流程步骤。")
    if dimensions["validator_failed"]:
        directives.add("在解释清楚或修复 validator 失败证据前，不要发布或提升该技能。")
    if dimensions["cve_identity_miss"] and dimensions["localization_success"] and not dimensions["cve_success"]:
        directives.add("保留有价值的定位指导，但要补上独立的 CVE 身份识别段落和不确定性回退。")
    bundle["revision_directives"] = sorted(directives)


def build_feedback_bundles(
    records: list[tuple[Path, dict[str, Any]]],
    *,
    gate_map: dict[str, dict[str, Any]] | None = None,
    only_skills: set[str] | None = None,
    only_case_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    gate_map = gate_map or {}
    bundles: dict[str, dict[str, Any]] = {}
    for path, record in records:
        if not _matches_case_filter(record, only_case_ids):
            continue
        selected = _selected_skills(record)
        if not selected:
            selected = [NO_SKILL_KEY]
        feedback = _feedback(record)
        decision = str(feedback.get("decision") or "neutral")
        if decision not in {"positive", "neutral", "negative"}:
            decision = "neutral"
        evidence = _record_evidence(record)
        normalized = evidence.get("normalized_score")
        confirmation_status = evidence.get("confirmation_status") or evidence.get("validation_status")
        quality_flags = set(evidence.get("quality_flags") or [])
        dynamic_pass = any(
            item.get("status") == "passed" and str(item.get("type") or "") in {"bundle_script", "asan_command"}
            for item in evidence.get("validator_checks") or []
        )
        artifact_generated = any(
            item.get("status") == "passed" and str(item.get("type") or "") == "artifact_exists"
            for item in evidence.get("validator_checks") or []
        )
        artifact_execution_passed = any(
            item.get("status") == "passed" and str(item.get("type") or "") == "artifact_exec"
            for item in evidence.get("validator_checks") or []
        )
        for skill in selected:
            if only_skills and skill not in only_skills:
                continue
            bundle = bundles.setdefault(skill, _new_bundle(skill, gate_map.get(skill)))
            summary = bundle["summary"]
            dimensions = bundle["dimensions"]
            summary["selected_runs"] += 1
            role = classify_skill_role(record.get("skill_relevance"), skill)
            skill_decision = decision
            if role == "relevant":
                summary["relevant_selected"] += 1
            elif role == "mismatched":
                summary["mismatched_selected"] += 1
                skill_decision = "neutral"
            elif role == "infrastructure":
                summary["infra_selected"] += 1
                skill_decision = "neutral"
            summary[skill_decision] += 1
            if isinstance(normalized, (int, float)):
                bundle["_scores"].append(float(normalized))
            if evidence["hits"]["file"] or evidence["hits"]["function"]:
                dimensions["localization_success"] += 1
            if evidence["hits"]["cve"]:
                dimensions["cve_success"] += 1
            if "cve_identity_miss" in quality_flags:
                dimensions["cve_identity_miss"] += 1
            if evidence["hits"]["evidence"]:
                dimensions["evidence_success"] += 1
            if evidence["hits"]["root_cause"]:
                dimensions["root_cause_success"] += 1
            if confirmation_status == "passed":
                dimensions["validator_passed"] += 1
            elif confirmation_status == "failed":
                dimensions["validator_failed"] += 1
            if dynamic_pass:
                dimensions["dynamic_or_bundle_confirmation_passed"] += 1
                dimensions["dynamic_or_bundle_validation_passed"] += 1
            if artifact_generated:
                dimensions["artifact_generated"] += 1
            if artifact_execution_passed:
                dimensions["artifact_execution_passed"] += 1
            bundle["cases"].append({"record": str(path), **evidence})

    output = []
    for bundle in bundles.values():
        scores = bundle.pop("_scores")
        bundle["summary"]["mean_score"] = round(sum(scores) / len(scores), 3) if scores else None
        _add_revision_directives(bundle)
        _add_revision_templates(bundle)
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
        "relevant",
        "mismatched",
        "infra",
        "mean_score",
        "localization",
        "cve_hit",
        "cve_miss",
        "validator_passed",
        "artifact_generated",
        "artifact_exec",
        "directives",
        "templates",
    ]
    lines = [
        "# 技能反馈 Bundle",
        "",
        "这份文件汇总了可直接供 evolver 消费的、技能级别维度反馈。",
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
            "relevant": summary["relevant_selected"],
            "mismatched": summary["mismatched_selected"],
            "infra": summary["infra_selected"],
            "mean_score": summary["mean_score"],
            "localization": dimensions["localization_success"],
            "cve_hit": dimensions["cve_success"],
            "cve_miss": dimensions["cve_identity_miss"],
            "validator_passed": dimensions["validator_passed"],
            "artifact_generated": dimensions["artifact_generated"],
            "artifact_exec": dimensions["artifact_execution_passed"],
            "directives": bundle["revision_directives"],
            "templates": [item.get("template_id") for item in bundle.get("revision_templates") or []],
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
    parser.add_argument("--records-dir", default="reports")
    parser.add_argument("--pattern", default="*final*.json")
    parser.add_argument("--gate-json", type=Path, default=Path("reports/current/skill_gate.json"))
    parser.add_argument("--out-json", type=Path, default=Path("reports/current/skill_feedback_bundle.json"))
    parser.add_argument("--out-md", type=Path, default=Path("reports/current/skill_feedback_bundle.md"))
    parser.add_argument("--skill", action="append", default=[], help="Only include selected skill(s). Repeatable.")
    parser.add_argument("--case-id", action="append", default=[], help="Only include selected case id(s). Repeatable.")
    args = parser.parse_args(argv)

    bundles = build_feedback_bundles(
        collect_records(_resolve_inputs(args)),
        gate_map=_load_gate_map(args.gate_json),
        only_skills={item for item in args.skill if str(item).strip()} or None,
        only_case_ids={item for item in args.case_id if str(item).strip()} or None,
    )
    write_json(bundles, args.out_json)
    write_markdown(bundles, args.out_md)
    print(f"wrote {len(bundles)} skill feedback bundle(s) to {args.out_json} and {args.out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())




