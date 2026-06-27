#!/usr/bin/env python3
"""Attach server-side SkillClaw injection audit data to final records."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    from experiment_scripts.build_result_record import _load_optional_json, _select_injection, _select_injection_history
    from experiment_validation.core import assess_skill_relevance, build_feedback
except ImportError:  # pragma: no cover - direct script execution.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from experiment_scripts.build_result_record import _load_optional_json, _select_injection, _select_injection_history
    from experiment_validation.core import assess_skill_relevance, build_feedback


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def attach_injection(
    *,
    final_record: dict[str, Any],
    case: dict[str, Any],
    injection_value: Any,
    session_id: str = "",
) -> dict[str, Any]:
    effective_session_id = session_id or str(final_record.get("session_id") or "")
    injection = _select_injection(injection_value, effective_session_id)
    injection_history = _select_injection_history(injection_value, effective_session_id)
    selected_skills = []
    if isinstance(injection, dict):
        selected_skills = list(injection.get("selected_skill_names") or [])

    final_record = dict(final_record)
    if effective_session_id:
        final_record["session_id"] = effective_session_id
    final_record["skill_injection"] = injection
    final_record["skill_injection_history"] = injection_history
    final_record["skill_relevance"] = assess_skill_relevance(case=case, selected_skills=selected_skills)
    final_record["feedback"] = build_feedback(
        score_result=final_record,
        validation_result=final_record.get("validation"),
        skill_injection=injection,
        skill_relevance=final_record["skill_relevance"],
    )
    return final_record


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", type=Path)
    parser.add_argument("final_record", type=Path)
    parser.add_argument("injection_json", type=Path)
    parser.add_argument("--session-id", default="")
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--in-place", action="store_true")
    args = parser.parse_args(argv)

    case = _load_json(args.case)
    final_record = _load_json(args.final_record)
    injection_value = _load_optional_json(args.injection_json)
    updated = attach_injection(
        final_record=final_record,
        case=case,
        injection_value=injection_value,
        session_id=args.session_id,
    )

    output = json.dumps(updated, ensure_ascii=False, indent=2) + "\n"
    if args.in_place:
        args.final_record.write_text(output, encoding="utf-8")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(output, encoding="utf-8")
    if not args.in_place and not args.out:
        print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
