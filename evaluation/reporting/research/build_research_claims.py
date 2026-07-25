#!/usr/bin/env python3
"""Generate research-oriented observations from experiment final records.

The result matrix is useful for debugging, but a paper draft needs higher-level
claims: under which budget did SkillClaw help, where did direct LLM win, and
what systematic failure remains. This script derives conservative observations
from the same final JSON records used by `build_result_matrix.py`.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

try:
    from evaluation.reporting.current.build_result_matrix import collect_rows
except ImportError:  # pragma: no cover - direct script execution.
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from evaluation.reporting.current.build_result_matrix import collect_rows


def _score(row: dict[str, Any]) -> float:
    try:
        return float(row.get("score") or 0)
    except (TypeError, ValueError):
        return 0.0


def _is_skillclaw(row: dict[str, Any]) -> bool:
    return str(row.get("mode") or "").startswith("skillclaw")


def _is_direct(row: dict[str, Any]) -> bool:
    return str(row.get("mode") or "").startswith("direct")


def _budget(row: dict[str, Any]) -> str:
    mode = str(row.get("mode") or "")
    if "budget035" in mode:
        return "budget035"
    if "budget080" in mode:
        return "budget080"
    if "low" in mode:
        return "low"
    if "high" in mode:
        return "high"
    return "unspecified"


def _hit(row: dict[str, Any], key: str) -> bool:
    return str(row.get(f"{key}_hit") or "").upper() == "Y"


def _localization_score(row: dict[str, Any]) -> int:
    return sum(1 for key in ("file", "function", "evidence", "root_cause") if _hit(row, key))


def _best(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not rows:
        return None
    return sorted(rows, key=lambda item: (_score(item), _localization_score(item)), reverse=True)[0]


def _mode_score(row: dict[str, Any] | None) -> str:
    if not row:
        return "n/a"
    return f"{row.get('mode')}={row.get('score_text') or _score(row):}"


def _selected_skills(row: dict[str, Any] | None) -> str:
    if not row:
        return ""
    return str(row.get("selected_skills") or "")


def _confirmation_maturity(row: dict[str, Any] | None) -> str:
    if not row:
        return ""
    return str(row.get("confirmation_maturity") or "")


def build_claims(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_case: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_case[str(row.get("case_id") or "unknown")].append(row)

    cases = []
    observations: list[str] = []
    for case_id, case_rows in sorted(by_case.items()):
        skill_rows = [row for row in case_rows if _is_skillclaw(row)]
        direct_rows = [row for row in case_rows if _is_direct(row)]
        skill_best = _best(skill_rows)
        direct_best = _best(direct_rows)
        skill_low = _best([row for row in skill_rows if _budget(row) in {"budget035", "low"}])
        direct_low = _best([row for row in direct_rows if _budget(row) in {"budget035", "low"}])
        skill_high = _best([row for row in skill_rows if _budget(row) in {"budget080", "high"}])
        direct_high = _best([row for row in direct_rows if _budget(row) in {"budget080", "high"}])

        case_summary = {
            "case_id": case_id,
            "skillclaw_best": _mode_score(skill_best),
            "direct_best": _mode_score(direct_best),
            "skillclaw_low_budget": _mode_score(skill_low),
            "direct_low_budget": _mode_score(direct_low),
            "skillclaw_high_budget": _mode_score(skill_high),
            "direct_high_budget": _mode_score(direct_high),
            "skillclaw_confirmation_maturity": _confirmation_maturity(skill_best),
            "direct_confirmation_maturity": _confirmation_maturity(direct_best),
            "selected_skills": _selected_skills(skill_best),
        }
        cases.append(case_summary)

        if skill_low and direct_low and _score(skill_low) > _score(direct_low):
            observations.append(
                f"{case_id}: SkillClaw produced a stronger low-budget result "
                f"({_mode_score(skill_low)} vs {_mode_score(direct_low)})."
            )
        if skill_high and direct_high and _score(direct_high) > _score(skill_high):
            observations.append(
                f"{case_id}: direct LLM outperformed SkillClaw under the high-budget setting "
                f"({_mode_score(direct_high)} vs {_mode_score(skill_high)}), which is a counterexample "
                "to any unconditional SkillClaw-improves claim."
            )
        if skill_best and _localization_score(skill_best) == 4 and not _hit(skill_best, "cve"):
            observations.append(
                f"{case_id}: SkillClaw localized file/function/root-cause evidence but missed exact CVE identity; "
                "this suggests a CVE identity failure rather than a localization failure."
            )
        if direct_best and _localization_score(direct_best) == 4 and not _hit(direct_best, "cve"):
            observations.append(
                f"{case_id}: direct LLM also localized the vulnerability but missed exact CVE identity, "
                "so CVE identity should be scored separately from location evidence."
            )
        if skill_best and _confirmation_maturity(skill_best):
            observations.append(
                f"{case_id}: the strongest SkillClaw-backed confirmation layer currently recorded is "
                f"`{_confirmation_maturity(skill_best)}`."
            )

    aggregate = {
        "cases": len(by_case),
        "runs": len(rows),
        "skillclaw_runs": sum(1 for row in rows if _is_skillclaw(row)),
        "direct_runs": sum(1 for row in rows if _is_direct(row)),
        "skillclaw_positive_runs": sum(1 for row in rows if _is_skillclaw(row) and _score(row) > 0),
        "direct_positive_runs": sum(1 for row in rows if _is_direct(row) and _score(row) > 0),
        "skillclaw_cve_misses_with_localization": sum(
            1 for row in rows if _is_skillclaw(row) and _localization_score(row) == 4 and not _hit(row, "cve")
        ),
        "direct_cve_misses_with_localization": sum(
            1 for row in rows if _is_direct(row) and _localization_score(row) == 4 and not _hit(row, "cve")
        ),
    }
    return {"aggregate": aggregate, "cases": cases, "observations": observations}


def _md_escape(value: Any) -> str:
    return str(value if value is not None else "").replace("|", "\\|").replace("\n", " ")


def write_markdown(claims: dict[str, Any], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    aggregate = claims["aggregate"]
    lines = [
        "# Research Claim Summary",
        "",
        "## Scope",
        "",
        f"- Cases: {aggregate['cases']}",
        f"- Runs: {aggregate['runs']}",
        f"- SkillClaw runs: {aggregate['skillclaw_runs']}",
        f"- Direct LLM runs: {aggregate['direct_runs']}",
        "",
        "## Case-Level Summary",
        "",
        "| case_id | SkillClaw best | Direct best | SkillClaw low budget | Direct low budget | SkillClaw high budget | Direct high budget | SkillClaw confirmation | Direct confirmation | selected skills |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in claims["cases"]:
        lines.append(
            "| "
            + " | ".join(
                _md_escape(item.get(key, ""))
                for key in (
                    "case_id",
                    "skillclaw_best",
                    "direct_best",
                    "skillclaw_low_budget",
                    "direct_low_budget",
                    "skillclaw_high_budget",
                    "direct_high_budget",
                    "skillclaw_confirmation_maturity",
                    "direct_confirmation_maturity",
                    "selected_skills",
                )
            )
            + " |"
        )
    lines.extend(["", "## Conservative Observations", ""])
    for observation in claims["observations"]:
        lines.append(f"- {observation}")
    lines.extend(
        [
            "",
            "## Paper-Framing Implication",
            "",
            "The current evidence should not be framed as a universal win for SkillClaw. "
            "A safer framing is that task-specific, session-stable skill injection can improve "
            "agent steering under constrained budgets, while exact vulnerability identity and "
            "skill-induced bias require separate validation.",
            "",
        ]
    )
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
    parser.add_argument("--out-md", type=Path, default=Path("reports/research_claims_latest.md"))
    parser.add_argument("--out-json", type=Path, default=Path("reports/research_claims_latest.json"))
    args = parser.parse_args(argv)

    rows = collect_rows(_resolve_inputs(args))
    claims = build_claims(rows)
    write_markdown(claims, args.out_md)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(claims, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.out_md} and {args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


