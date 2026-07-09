#!/usr/bin/env python3
"""Attach server-side SkillClaw injection audit data to final records."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

try:
    from experiment_scripts.postprocess.build_result_record import (
        _load_optional_json,
        _select_injection,
        _select_injection_history,
    )
    from experiment_validation.core import assess_skill_relevance, build_feedback
except ImportError:  # pragma: no cover - direct script execution.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from experiment_scripts.postprocess.build_result_record import (
        _load_optional_json,
        _select_injection,
        _select_injection_history,
    )
    from experiment_validation.core import assess_skill_relevance, build_feedback


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _infer_session_id_from_injection(
    injection_value: Any,
    final_record: dict[str, Any],
    *,
    margin_before_seconds: int = 300,
    margin_after_seconds: int = 300,
) -> str:
    if not isinstance(injection_value, list):
        return ""
    run_meta = final_record.get("run")
    if not isinstance(run_meta, dict):
        return ""
    start_text = str(run_meta.get("start") or "").strip()
    end_text = str(run_meta.get("end") or "").strip()
    if not start_text or not end_text:
        return ""
    try:
        start_utc = datetime.fromisoformat(start_text)
        end_utc = datetime.fromisoformat(end_text)
    except ValueError:
        return ""
    if start_utc.tzinfo is None or end_utc.tzinfo is None:
        return ""

    local_tz = datetime.now().astimezone().tzinfo or timezone.utc
    start_local = start_utc.astimezone(local_tz) - timedelta(seconds=margin_before_seconds)
    end_local = end_utc.astimezone(local_tz) + timedelta(seconds=margin_after_seconds)

    candidates: dict[str, tuple[datetime, int]] = {}
    for item in injection_value:
        if not isinstance(item, dict):
            continue
        candidate_session_id = str(item.get("session_id") or "").strip()
        timestamp_text = str(item.get("timestamp") or "").strip()
        if not candidate_session_id or not timestamp_text:
            continue
        try:
            timestamp = datetime.strptime(timestamp_text, "%Y-%m-%d %H:%M:%S").replace(tzinfo=local_tz)
        except ValueError:
            continue
        if not (start_local <= timestamp <= end_local):
            continue
        turn = int(item.get("turn") or 0)
        current = candidates.get(candidate_session_id)
        if current is None or (timestamp, turn) > current:
            candidates[candidate_session_id] = (timestamp, turn)

    if not candidates:
        return ""
    return max(candidates.items(), key=lambda kv: kv[1])[0]


def attach_injection(
    *,
    final_record: dict[str, Any],
    case: dict[str, Any],
    injection_value: Any,
    session_id: str = "",
) -> dict[str, Any]:
    effective_session_id = session_id or str(final_record.get("session_id") or "")
    session_id_source = "explicit" if effective_session_id else "missing"
    if not effective_session_id:
        inferred_session_id = _infer_session_id_from_injection(injection_value, final_record)
        if inferred_session_id:
            effective_session_id = inferred_session_id
            session_id_source = "inferred_from_injection_log"
    injection = _select_injection(injection_value, effective_session_id)
    injection_history = _select_injection_history(injection_value, effective_session_id)
    selected_skills = []
    if isinstance(injection, dict):
        selected_skills = list(injection.get("selected_skill_names") or [])

    final_record = dict(final_record)
    if effective_session_id:
        final_record["session_id"] = effective_session_id
    final_record["session_id_source"] = session_id_source
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
