#!/usr/bin/env python3
"""Build a conservative gate report from skill-level feedback evidence.

This is the first bridge from validator-backed experiment records to skill
evolution policy.  It does not rewrite or publish skills.  It only turns the
current evidence into explicit gate decisions that a human or later evolver can
act on.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any


GATE_DECISIONS = {
    "promote",
    "keep",
    "revise",
    "demote",
    "insufficient_evidence",
}


def _as_int(value: Any) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _as_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _load_feedback_csv(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def _is_infra_skill(skill: str) -> bool:
    return skill.startswith("skillclaw-")


def decide_gate(row: dict[str, Any], *, min_samples: int = 2, promote_samples: int = 3) -> dict[str, Any]:
    skill = str(row.get("skill") or "")
    selected = _as_int(row.get("selected_count"))
    positive = _as_int(row.get("positive"))
    neutral = _as_int(row.get("neutral"))
    negative = _as_int(row.get("negative"))
    mean_score = _as_float(row.get("mean_score"))
    validation_failed = _as_int(row.get("validation_failed"))
    validation_passed = _as_int(row.get("validation_passed"))
    relevant_selected = _as_int(row.get("relevant_selected"))
    mismatched_selected = _as_int(row.get("mismatched_selected"))
    infra_selected = _as_int(row.get("infra_selected"))
    cve_hits = _as_int(row.get("cve_hits"))
    file_hits = _as_int(row.get("file_hits"))
    function_hits = _as_int(row.get("function_hits"))
    evidence_hits = _as_int(row.get("evidence_hits"))
    root_cause_hits = _as_int(row.get("root_cause_hits"))

    reasons: list[str] = []
    suggestions: list[str] = []
    decision = "insufficient_evidence"

    if _is_infra_skill(skill):
        decision = "demote" if selected >= min_samples else "insufficient_evidence"
        reasons.append("infrastructure/self-inspection skill selected during vulnerability-localization runs")
        suggestions.append("tighten retrieval so this skill is not selected unless the user asks about SkillClaw internals")
    elif mismatched_selected >= min_samples and relevant_selected == 0:
        decision = "demote"
        reasons.append(f"{mismatched_selected} mismatched selection(s) and no task-aligned evidence")
        suggestions.append("tighten retrieval or rename the skill so it is not selected for this task family")
    elif selected < min_samples:
        decision = "insufficient_evidence"
        reasons.append(f"only {selected} selected run(s); require at least {min_samples}")
        suggestions.append("collect more benchmark runs before changing publication status")
    elif validation_failed:
        decision = "revise" if positive else "demote"
        reasons.append(f"{validation_failed} validator failure(s)")
        suggestions.append("inspect failing case evidence before promotion")
    elif negative:
        decision = "revise"
        reasons.append(f"{negative} negative feedback run(s)")
        suggestions.append("revise the skill to reduce misleading guidance")
    elif positive >= promote_samples and mean_score >= 0.8 and file_hits >= positive and function_hits >= positive:
        decision = "promote"
        reasons.append(f"{positive} positive run(s), mean_score={mean_score:g}, file/function evidence hit")
        suggestions.append("candidate for broader benchmark evaluation or default retrieval boost if no later evidence gap is found")
    elif positive and mean_score >= 0.65:
        decision = "keep"
        reasons.append(f"{positive} positive run(s), mean_score={mean_score:g}")
        suggestions.append("keep enabled, but require more cases before promotion")
    else:
        decision = "revise"
        reasons.append(f"weak feedback mix: positive={positive}, neutral={neutral}, negative={negative}")
        suggestions.append("rewrite examples and add concrete evidence requirements")

    if selected >= min_samples and cve_hits == 0 and (file_hits or function_hits):
        if decision in {"promote", "keep"}:
            decision = "revise"
            suggestions = [
                item
                for item in suggestions
                if "retrieval boost" not in item and "before promotion" not in item
            ]
            suggestions.append("keep as localization guidance, but revise before promotion")
        reasons.append("localization evidence exists but exact CVE calibration is absent")
        suggestions.append("add guidance to verify exact CVE identity against advisories or patch metadata")
    if selected >= min_samples and evidence_hits < selected:
        reasons.append("not every selected run included required evidence hits")
        suggestions.append("make evidence checklist explicit in the skill")
    if selected >= min_samples and root_cause_hits < selected:
        reasons.append("not every selected run explained root cause")
        suggestions.append("require root-cause explanation tied to source-level evidence")
    if mismatched_selected:
        reasons.append(f"{mismatched_selected} run(s) selected this skill without task alignment")
        suggestions.append("reduce over-selection by adding narrower trigger conditions")
    if infra_selected:
        reasons.append(f"{infra_selected} run(s) selected this skill as infrastructure/context noise")
    if validation_passed:
        reasons.append(f"{validation_passed} validator-passed run(s)")

    assert decision in GATE_DECISIONS
    return {
        "skill": skill,
        "gate_decision": decision,
        "selected_count": selected,
        "positive": positive,
        "neutral": neutral,
        "negative": negative,
        "mean_score": mean_score,
        "cve_hits": cve_hits,
        "file_hits": file_hits,
        "function_hits": function_hits,
        "evidence_hits": evidence_hits,
        "root_cause_hits": root_cause_hits,
        "validation_passed": validation_passed,
        "validation_failed": validation_failed,
        "relevant_selected": relevant_selected,
        "mismatched_selected": mismatched_selected,
        "infra_selected": infra_selected,
        "cases": row.get("cases") or "",
        "modes": row.get("modes") or "",
        "reasons": reasons,
        "suggestions": suggestions,
    }


def build_gate_report(rows: list[dict[str, Any]], *, min_samples: int = 2, promote_samples: int = 3) -> list[dict[str, Any]]:
    decisions = [decide_gate(row, min_samples=min_samples, promote_samples=promote_samples) for row in rows]
    order = {"promote": 0, "keep": 1, "revise": 2, "demote": 3, "insufficient_evidence": 4}
    return sorted(
        decisions,
        key=lambda item: (
            order.get(str(item["gate_decision"]), 99),
            -_as_int(item["selected_count"]),
            str(item["skill"]),
        ),
    )


def _md_escape(value: Any) -> str:
    if isinstance(value, list):
        value = "; ".join(str(item) for item in value)
    return str(value if value is not None else "").replace("|", "\\|").replace("\n", " ")


def write_markdown(rows: list[dict[str, Any]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    headers = [
        "skill",
        "gate_decision",
        "selected_count",
        "positive",
        "neutral",
        "negative",
        "mean_score",
        "cve_hits",
        "file_hits",
        "function_hits",
        "reasons",
        "suggestions",
    ]
    lines = [
        "# Skill Gate Report",
        "",
        "This report converts validator-backed skill feedback into conservative gate decisions.",
        "It does not automatically publish, rewrite, or delete any skill.",
        "",
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(_md_escape(row.get(key, "")) for key in headers) + " |")
    lines.extend(
        [
            "",
            "## Gate Semantics",
            "",
            "- `promote`: strong current evidence; candidate for retrieval boost or broader benchmark evaluation.",
            "- `keep`: useful evidence exists, but more cases are needed before promotion.",
            "- `revise`: localization may help, but evidence gaps, CVE calibration errors, or failures require edits.",
            "- `demote`: selected skill is likely unrelated or harmful for the current task family.",
            "- `insufficient_evidence`: too few selected runs to judge.",
            "",
        ]
    )
    out_path.write_text("\n".join(lines), encoding="utf-8")


def write_json(rows: list[dict[str, Any]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feedback-csv", type=Path, default=Path("experiment_records/skill_feedback_latest.csv"))
    parser.add_argument("--out-md", type=Path, default=Path("experiment_records/skill_gate_report_latest.md"))
    parser.add_argument("--out-json", type=Path, default=Path("experiment_records/skill_gate_report_latest.json"))
    parser.add_argument("--min-samples", type=int, default=2)
    parser.add_argument("--promote-samples", type=int, default=3)
    args = parser.parse_args(argv)

    report = build_gate_report(
        _load_feedback_csv(args.feedback_csv),
        min_samples=args.min_samples,
        promote_samples=args.promote_samples,
    )
    write_markdown(report, args.out_md)
    write_json(report, args.out_json)
    print(f"wrote {len(report)} gate decision(s) to {args.out_md} and {args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
