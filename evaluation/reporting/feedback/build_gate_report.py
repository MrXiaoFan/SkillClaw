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
        reasons.append("该技能属于框架/自检类，却在漏洞定位任务中被选中")
        suggestions.append("收紧检索条件，除非用户明确询问 SkillClaw 内部机制，否则不要选中该技能")
    elif mismatched_selected >= min_samples and relevant_selected == 0:
        decision = "demote"
        reasons.append(f"共有 {mismatched_selected} 次错配选中，且没有任务对齐证据")
        suggestions.append("收紧检索条件，或重命名技能，让它不再被当前任务族误选")
    elif selected < min_samples:
        decision = "insufficient_evidence"
        reasons.append(f"仅有 {selected} 次样本，低于最少要求 {min_samples}")
        suggestions.append("先补更多 benchmark 运行，再决定是否调整其状态")
    elif validation_failed:
        decision = "revise" if positive else "demote"
        reasons.append(f"存在 {validation_failed} 次 validator 失败")
        suggestions.append("先检查失败案例的证据，再考虑是否提升")
    elif negative:
        decision = "revise"
        reasons.append(f"存在 {negative} 次负向反馈")
        suggestions.append("修改技能内容，减少误导性步骤或表述")
    elif positive >= promote_samples and mean_score >= 0.8 and file_hits >= positive and function_hits >= positive:
        decision = "promote"
        reasons.append(f"{positive} 次正向样本，平均分 {mean_score:g}，且 file/function 证据均命中")
        suggestions.append("可进入更广基准集继续验证；若后续没有明显证据缺口，可考虑提高默认检索优先级")
    elif positive and mean_score >= 0.65:
        decision = "keep"
        reasons.append(f"{positive} 次正向样本，平均分 {mean_score:g}")
        suggestions.append("暂时保留启用，但在提升前仍需更多案例")
    else:
        decision = "revise"
        reasons.append(f"反馈结构偏弱：positive={positive}, neutral={neutral}, negative={negative}")
        suggestions.append("重写示例，并补充更具体的证据要求")

    if selected >= min_samples and cve_hits == 0 and (file_hits or function_hits):
        if decision in {"promote", "keep"}:
            decision = "revise"
            suggestions = [
                item
                for item in suggestions
                if "检索优先级" not in item and "提升" not in item
            ]
            suggestions.append("可保留为定位指导，但在提升前必须先修正 CVE 识别问题")
        reasons.append("已有定位证据，但缺少精确 CVE 身份确认")
        suggestions.append("补充规则：只有在 advisory、patch 或版本元数据支持时，才能输出精确 CVE")
    if selected >= min_samples and evidence_hits < selected:
        reasons.append("并非每次被选中的运行都命中了所需证据")
        suggestions.append("把证据检查清单明确写进技能")
    if selected >= min_samples and root_cause_hits < selected:
        reasons.append("并非每次被选中的运行都解释清楚根因")
        suggestions.append("要求输出中把根因解释与源码级证据绑定起来")
    if mismatched_selected:
        reasons.append(f"共有 {mismatched_selected} 次运行选中了该技能，但与任务并不对齐")
        suggestions.append("增加更窄的触发条件，减少过度选中")
    if infra_selected:
        reasons.append(f"共有 {infra_selected} 次运行把该技能当作上下文噪声选入")
    if validation_passed:
        reasons.append(f"共有 {validation_passed} 次 validator 通过")

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
        "# 技能 Gate 报告",
        "",
        "这份报告把 validator 支持的技能反馈转换成保守的 gate 决策。",
        "它不会自动发布、改写或删除任何技能。",
        "",
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(_md_escape(row.get(key, "")) for key in headers) + " |")
    lines.extend(
        [
            "",
            "## Gate 含义",
            "",
            "- `promote`：当前证据较强，可考虑提高检索优先级或纳入更广基准集继续验证。",
            "- `keep`：已有正向证据，但样本还不够，不宜直接提升。",
            "- `revise`：定位可能有帮助，但证据缺口、CVE 识别错误或失败案例要求先修改。",
            "- `demote`：该技能大概率与当前任务族不相关，或会带来误导。",
            "- `insufficient_evidence`：样本数太少，暂时不能判断。",
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
    parser.add_argument("--feedback-csv", type=Path, default=Path("reports/current/skill_feedback.csv"))
    parser.add_argument("--out-md", type=Path, default=Path("reports/current/skill_gate.md"))
    parser.add_argument("--out-json", type=Path, default=Path("reports/current/skill_gate.json"))
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



