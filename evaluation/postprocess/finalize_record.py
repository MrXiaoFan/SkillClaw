#!/usr/bin/env python3
"""Finalize one experiment record with skill injection and optional compare output."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

try:
    from evaluation.postprocess.compare_records import compare_records, render_markdown
    from evaluation.validation.core import assess_skill_relevance, build_feedback
except ImportError:  # pragma: no cover - direct script execution.
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from evaluation.postprocess.compare_records import compare_records, render_markdown
    from evaluation.validation.core import assess_skill_relevance, build_feedback


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _load_optional_json(path: Path | None) -> Any:
    if not path:
        return None
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8-sig", errors="replace").strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        rows = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return rows


def _select_injection(value: Any, session_id: str) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return value
    if not isinstance(value, list):
        return None
    candidates = [item for item in value if isinstance(item, dict)]
    if session_id:
        for item in reversed(candidates):
            if str(item.get("session_id") or "") == session_id:
                return item
    return candidates[-1] if candidates else None


def _select_injection_history(value: Any, session_id: str) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        return [value]
    if not isinstance(value, list):
        return []
    candidates = [item for item in value if isinstance(item, dict)]
    if session_id:
        candidates = [item for item in candidates if str(item.get("session_id") or "") == session_id]
    return candidates


def _select_validation(value: Any, case_id: str) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return value
    if not isinstance(value, list):
        return None
    candidates = [item for item in value if isinstance(item, dict)]
    validation_rows = [item for item in candidates if item.get("validator_mode")]
    if case_id:
        for item in reversed(validation_rows):
            if str(item.get("case_id") or "") == case_id:
                return item
    if validation_rows:
        return validation_rows[-1]
    return candidates[-1] if candidates else None


def _default_finalized_out(path: Path) -> Path:
    if path.stem.endswith("-final-enriched"):
        return path
    if path.stem.endswith("-with-injection"):
        return path.with_name(f"{path.stem[:-15]}-final-enriched{path.suffix}")
    return path.with_name(f"{path.stem}-final-enriched{path.suffix}")


def _default_compare_json_out(path: Path) -> Path:
    if path.stem.endswith("-final-enriched"):
        return path.with_name(f"{path.stem[:-15]}-compare.json")
    if path.stem.endswith("-with-injection"):
        return path.with_name(f"{path.stem[:-15]}-compare.json")
    return path.with_name(f"{path.stem}-compare.json")


def _default_compare_md_out(path: Path) -> Path:
    if path.stem.endswith("-final-enriched"):
        return path.with_name(f"{path.stem[:-15]}-compare.md")
    if path.stem.endswith("-with-injection"):
        return path.with_name(f"{path.stem[:-15]}-compare.md")
    return path.with_name(f"{path.stem}-compare.md")


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


def _confirmation_snapshot(case: dict[str, Any]) -> dict[str, Any]:
    value = case.get("confirmation")
    return value if isinstance(value, dict) else {}


def build_finalized_record(
    *,
    case: dict[str, Any],
    final_record: dict[str, Any],
    injection_value: Any,
    session_id: str = "",
) -> dict[str, Any]:
    finalized = attach_injection(
        final_record=final_record,
        case=case,
        injection_value=injection_value,
        session_id=session_id,
    )
    confirmation = _confirmation_snapshot(case)
    finalized["confirmation"] = confirmation
    finalized["confirmation_maturity"] = str(confirmation.get("maturity") or "")
    finalized["confirmation_current_claim"] = str(confirmation.get("current_claim") or "")
    finalized["confirmation_accepted_runtime_claim"] = str(confirmation.get("accepted_runtime_claim") or "")
    return finalized


def finalize_record(
    *,
    case: dict[str, Any],
    final_record: dict[str, Any],
    injection_value: Any,
    session_id: str = "",
) -> dict[str, Any]:
    return build_finalized_record(
        case=case,
        final_record=final_record,
        injection_value=injection_value,
        session_id=session_id,
    )


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", type=Path)
    parser.add_argument("final_record", type=Path)
    parser.add_argument("injection_json", type=Path)
    parser.add_argument("--session-id", default="")
    parser.add_argument("--out", type=Path, default=None, help="Output path for finalized record.")
    parser.add_argument("--before", type=Path, default=None, help="Optional baseline record to compare against.")
    parser.add_argument("--compare-json-out", type=Path, default=None)
    parser.add_argument("--compare-md-out", type=Path, default=None)
    args = parser.parse_args(argv)

    case = _load_json(args.case)
    final_record = _load_json(args.final_record)
    injection_value = _load_optional_json(args.injection_json)
    finalized = finalize_record(
        case=case,
        final_record=final_record,
        injection_value=injection_value,
        session_id=args.session_id,
    )

    out_path = args.out or _default_finalized_out(args.final_record)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(finalized, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.before:
        before = _load_json(args.before)
        compare = compare_records(before, finalized)
        compare_json_out = args.compare_json_out or _default_compare_json_out(out_path)
        compare_md_out = args.compare_md_out or _default_compare_md_out(out_path)
        compare_json_out.parent.mkdir(parents=True, exist_ok=True)
        compare_json_out.write_text(json.dumps(compare, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        compare_md_out.parent.mkdir(parents=True, exist_ok=True)
        compare_md_out.write_text(render_markdown(compare) + "\n", encoding="utf-8")

    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
