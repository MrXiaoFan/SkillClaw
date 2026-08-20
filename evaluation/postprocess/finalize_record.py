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
    from evaluation.confirmation.core import assess_skill_relevance, build_feedback
except ImportError:  # pragma: no cover - direct script execution.
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from evaluation.postprocess.compare_records import compare_records, render_markdown
    from evaluation.confirmation.core import assess_skill_relevance, build_feedback


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _load_optional_json(path: Path | None, session_filter: str = "") -> Any:
    if not path:
        return None
    if path.is_dir():
        items = []
        for child in sorted(path.glob("*.json")):
            text = child.read_text(encoding="utf-8-sig", errors="replace").strip()
            if not text:
                continue
            try:
                items.append(json.loads(text))
            except json.JSONDecodeError:
                continue
        return items
    if not path.is_file():
        return None
    # Stream-read with session filter for large JSONL files to avoid OOM
    if session_filter:
        rows = []
        with open(path, "r", encoding="utf-8-sig", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line or session_filter not in line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return rows
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
            if session_filter and session_filter not in line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return rows


def _as_clean_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    text = str(value).strip()
    return [text] if text else []


def _first_non_empty_list(*values: Any) -> list[str]:
    for value in values:
        cleaned = _as_clean_list(value)
        if cleaned:
            return cleaned
    return []


def _first_non_empty_text(*values: Any) -> str:
    for value in values:
        if isinstance(value, list):
            text = "\n".join(str(item) for item in value if str(item).strip()).strip()
        else:
            text = str(value or "").strip()
        if text:
            return text
    return ""


def _extract_json_object_from_text(text: str) -> dict[str, Any]:
    stripped = str(text or "").lstrip("\ufeff").strip()
    if not stripped:
        return {}
    try:
        obj = json.loads(stripped)
        return obj if isinstance(obj, dict) else {}
    except json.JSONDecodeError:
        pass
    if "```" in stripped:
        parts = stripped.split("```")
        for idx, part in enumerate(parts):
            candidate = part
            if idx % 2 == 1 and candidate.lstrip().lower().startswith("json"):
                candidate = candidate.lstrip()[4:]
            candidate = candidate.strip()
            if not candidate:
                continue
            try:
                obj = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                return obj
    decoder = json.JSONDecoder()
    for idx, char in enumerate(stripped):
        if char != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(stripped[idx:])
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            return obj
    return {}


def _extract_agent_json(final_record: dict[str, Any]) -> dict[str, Any]:
    direct = final_record.get("agent_json")
    if isinstance(direct, dict):
        return direct
    predictions = final_record.get("predictions")
    if not isinstance(predictions, dict):
        return {}
    raw_text_items = predictions.get("raw_text")
    if not isinstance(raw_text_items, list):
        return {}
    for item in raw_text_items:
        obj = _extract_json_object_from_text(str(item or ""))
        if obj:
            return obj
    return {}


def normalize_prediction_fields(final_record: dict[str, Any]) -> dict[str, Any]:
    record = dict(final_record)
    predictions = record.get("predictions")
    prediction_map = predictions if isinstance(predictions, dict) else {}
    agent_json = _extract_agent_json(record)
    if agent_json and not isinstance(record.get("agent_json"), dict):
        record["agent_json"] = agent_json

    record["predicted_cves"] = _first_non_empty_list(
        record.get("predicted_cves"),
        agent_json.get("predicted_cves"),
        agent_json.get("predicted_cve"),
        agent_json.get("cve"),
        prediction_map.get("cves"),
    )
    record["predicted_files"] = _first_non_empty_list(
        record.get("predicted_files"),
        agent_json.get("predicted_files"),
        agent_json.get("predicted_file"),
        agent_json.get("file"),
        prediction_map.get("files"),
    )
    record["predicted_functions"] = _first_non_empty_list(
        record.get("predicted_functions"),
        agent_json.get("predicted_functions"),
        agent_json.get("predicted_function"),
        agent_json.get("function"),
        prediction_map.get("functions"),
    )
    record["root_cause"] = _first_non_empty_text(
        record.get("root_cause"),
        agent_json.get("root_cause"),
        agent_json.get("analysis"),
    )
    record["evidence"] = _first_non_empty_text(
        record.get("evidence"),
        agent_json.get("evidence"),
        prediction_map.get("evidence"),
    )
    record["confidence"] = _first_non_empty_text(
        record.get("confidence"),
        agent_json.get("confidence"),
    )
    return record


def _looks_like_session_snapshot(value: dict[str, Any]) -> bool:
    return isinstance(value.get("turns"), list) and bool(str(value.get("session_id") or "").strip())


def _session_snapshot_to_injection_rows(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    session_id = str(snapshot.get("session_id") or "").strip()
    client_session_id = str(snapshot.get("client_session_id") or session_id).strip()
    session_segment_id = str(snapshot.get("session_segment_id") or session_id).strip()
    turns = snapshot.get("turns")
    timestamp = str(snapshot.get("timestamp") or "").strip()
    if not session_id or not isinstance(turns, list):
        return []

    rows: list[dict[str, Any]] = []
    for turn in turns:
        if not isinstance(turn, dict):
            continue
        raw_injection = turn.get("skill_injection")
        injection = raw_injection if isinstance(raw_injection, dict) else {}
        selected_skill_names = turn.get("selected_skill_names")
        if not isinstance(selected_skill_names, list):
            selected_skill_names = injection.get("selected_skill_names")
        if not isinstance(selected_skill_names, list):
            selected_skill_names = []

        row = {
            "session_id": session_id,
            "client_session_id": str(turn.get("client_session_id") or client_session_id),
            "session_segment_id": str(turn.get("session_segment_id") or session_segment_id),
            "timestamp": timestamp,
            "turn": int(turn.get("turn_num") or turn.get("turn") or 0),
            "selected_skill_names": [str(item) for item in selected_skill_names if str(item).strip()],
            "injection_mode": str(
                turn.get("injection_mode")
                or injection.get("injection_mode")
                or ""
            ),
            "skill_top_k": turn.get("skill_top_k", injection.get("top_k")),
            "skill_prompt_hash": str(
                turn.get("skill_prompt_hash")
                or injection.get("skill_prompt_hash")
                or ""
            ),
            "available_skill_count": int(
                turn.get("available_skill_count")
                or injection.get("available_skill_count")
                or 0
            ),
            "prm_score": turn.get("prm_score"),
            "source": "session_snapshot",
        }
        if row["selected_skill_names"] or row["injection_mode"] or row["skill_prompt_hash"]:
            rows.append(row)
    return rows


def _normalize_injection_rows(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        if _looks_like_session_snapshot(value):
            return _session_snapshot_to_injection_rows(value)
        return [value]
    if not isinstance(value, list):
        return []

    rows: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        if _looks_like_session_snapshot(item):
            rows.extend(_session_snapshot_to_injection_rows(item))
        else:
            rows.append(item)
    return rows


def _row_selected_skill_names(row: dict[str, Any]) -> list[str]:
    selected = row.get("selected_skill_names")
    if isinstance(selected, list):
        return [str(item) for item in selected if str(item).strip()]
    nested = row.get("skill_injection")
    if isinstance(nested, dict):
        selected = nested.get("selected_skill_names")
        if isinstance(selected, list):
            return [str(item) for item in selected if str(item).strip()]
    return []


def _row_attribution_eligible(row: dict[str, Any]) -> bool | None:
    if "attribution_eligible" in row:
        return bool(row.get("attribution_eligible"))
    nested = row.get("skill_injection")
    if isinstance(nested, dict) and "attribution_eligible" in nested:
        return bool(nested.get("attribution_eligible"))
    return None


def _condense_injection_row(row: dict[str, Any]) -> dict[str, Any]:
    nested = row.get("skill_injection")
    nested_meta = nested if isinstance(nested, dict) else {}

    def _value(*keys: str) -> Any:
        for key in keys:
            if key in row and row.get(key) not in (None, ""):
                return row.get(key)
            if key in nested_meta and nested_meta.get(key) not in (None, ""):
                return nested_meta.get(key)
        return None

    def _list_value(*keys: str) -> list[str]:
        return _first_non_empty_list(*[_value(key) for key in keys])

    turn_value = _value("turn")
    if turn_value in (None, "", 0, "0"):
        turn_value = None

    condensed = {
        "session_id": str(_value("session_id") or ""),
        "client_session_id": str(_value("client_session_id") or ""),
        "session_segment_id": str(_value("session_segment_id") or ""),
        "session_id_source": str(_value("session_id_source") or ""),
        "segment_started_at": str(_value("segment_started_at") or ""),
        "segment_status": str(_value("segment_status") or ""),
        "timestamp": str(_value("timestamp") or ""),
        "turn": int(turn_value) if turn_value is not None else None,
        "selected_skill_names": _list_value("selected_skill_names"),
        "injection_mode": str(_value("injection_mode") or ""),
        "skill_top_k": _value("skill_top_k", "top_k"),
        "top_k": _value("top_k", "skill_top_k"),
        "skill_prompt_hash": str(_value("skill_prompt_hash") or ""),
        "skill_prompt_chars": _value("skill_prompt_chars"),
        "available_skill_count": _value("available_skill_count"),
        "enabled": _value("enabled"),
        "override_mode": str(_value("override_mode") or ""),
        "override_note": str(_value("override_note") or ""),
        "override_requested_skill_names": _list_value("override_requested_skill_names"),
        "override_matched_skill_names": _list_value("override_matched_skill_names"),
        "override_unmatched_skill_names": _list_value("override_unmatched_skill_names"),
        "stable_session": _value("stable_session"),
        "stable_action": str(_value("stable_action") or ""),
        "stable_generation": _value("stable_generation"),
        "attribution_eligible": _value("attribution_eligible"),
        "prm_score": _value("prm_score"),
        "source": str(_value("source") or ""),
    }
    return {key: value for key, value in condensed.items() if value not in (None, "", [], {})}


def _select_injection(value: Any, session_id: str) -> dict[str, Any] | None:
    candidates = _normalize_injection_rows(value)
    if session_id:
        candidates = [
            item
            for item in candidates
            if session_id
            in {
                str(item.get("session_id") or ""),
                str(item.get("client_session_id") or ""),
            }
        ]
    if not candidates:
        return None

    attributable = [item for item in candidates if _row_attribution_eligible(item) is True]
    pool = attributable or candidates
    with_selected_skills = [item for item in pool if _row_selected_skill_names(item)]
    if with_selected_skills:
        pool = with_selected_skills
    return _condense_injection_row(pool[-1])


def _select_injection_history(value: Any, session_id: str) -> list[dict[str, Any]]:
    candidates = _normalize_injection_rows(value)
    if session_id:
        candidates = [
            item
            for item in candidates
            if session_id
            in {
                str(item.get("session_id") or ""),
                str(item.get("client_session_id") or ""),
            }
        ]
    return [_condense_injection_row(item) for item in candidates]


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


def _select_confirmation_result(value: Any, case_id: str) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return value
    if not isinstance(value, list):
        return None
    candidates = [item for item in value if isinstance(item, dict)]
    confirmation_rows = [
        item for item in candidates if item.get("confirmation_mode") or item.get("validator_mode")
    ]
    if case_id:
        for item in reversed(confirmation_rows):
            if str(item.get("case_id") or "") == case_id:
                return item
    if confirmation_rows:
        return confirmation_rows[-1]
    return candidates[-1] if candidates else None


def _default_finalized_out(path: Path) -> Path:
    if path.stem.endswith("-final"):
        return path.with_name(f"{path.stem}-enriched{path.suffix}")
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


def _parse_injection_timestamp(timestamp_text: str, local_tz) -> datetime | None:
    text = str(timestamp_text or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = datetime.strptime(text, "%Y-%m-%d %H:%M:%S").replace(tzinfo=local_tz)
        except ValueError:
            return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=local_tz)
    return parsed.astimezone(local_tz)


def _infer_session_id_from_injection(
    injection_value: Any,
    final_record: dict[str, Any],
    *,
    margin_before_seconds: int = 300,
    margin_after_seconds: int = 300,
) -> str:
    injection_rows = _normalize_injection_rows(injection_value)
    if not injection_rows:
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

    direct_candidates: dict[str, tuple[datetime, int]] = {}
    snapshot_candidates: dict[str, tuple[datetime, int]] = {}
    for item in injection_rows:
        candidate_session_id = str(item.get("session_id") or "").strip()
        timestamp_text = str(item.get("timestamp") or "").strip()
        if not candidate_session_id or not timestamp_text:
            continue
        timestamp = _parse_injection_timestamp(timestamp_text, local_tz)
        if timestamp is None:
            continue
        if not (start_local <= timestamp <= end_local):
            continue
        turn = int(item.get("turn") or 0)
        bucket = snapshot_candidates if str(item.get("source") or "") == "session_snapshot" else direct_candidates
        current = bucket.get(candidate_session_id)
        if current is None or (timestamp, turn) > current:
            bucket[candidate_session_id] = (timestamp, turn)

    candidates = direct_candidates or snapshot_candidates
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
    final_record = normalize_prediction_fields(final_record)
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
    injection_mode = ""
    skill_top_k = None
    skill_prompt_hash = ""
    available_skill_count = None
    if isinstance(injection, dict):
        selected_skills = list(injection.get("selected_skill_names") or [])
        nested_injection = injection.get("skill_injection")
        nested = nested_injection if isinstance(nested_injection, dict) else {}
        injection_mode = str(injection.get("injection_mode") or nested.get("injection_mode") or "")
        skill_top_k = injection.get("skill_top_k", nested.get("top_k"))
        skill_prompt_hash = str(injection.get("skill_prompt_hash") or nested.get("skill_prompt_hash") or "")
        available_skill_count = injection.get("available_skill_count", nested.get("available_skill_count"))

    final_record = dict(final_record)
    if effective_session_id:
        final_record["session_id"] = effective_session_id
    if isinstance(injection, dict) and injection.get("session_segment_id"):
        final_record["session_segment_id"] = str(injection["session_segment_id"])
    final_record["session_id_source"] = session_id_source
    final_record["skill_injection"] = injection
    final_record["skill_injection_history"] = injection_history
    final_record["selected_skill_names"] = [str(item) for item in selected_skills if str(item).strip()]
    final_record["injection_mode"] = injection_mode
    final_record["skill_top_k"] = skill_top_k
    final_record["skill_prompt_hash"] = skill_prompt_hash
    final_record["available_skill_count"] = available_skill_count
    final_record["skill_relevance"] = assess_skill_relevance(case=case, selected_skills=selected_skills)
    confirmation_result = final_record.get("confirmation")
    if not (isinstance(confirmation_result, dict) and str(confirmation_result.get("status") or "").strip()):
        confirmation_result = final_record.get("validation")
    final_record["feedback"] = build_feedback(
        score_result=final_record,
        confirmation_result=confirmation_result,
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
    confirmation_spec = _confirmation_snapshot(case)
    finalized["confirmation_spec"] = confirmation_spec
    finalized["confirmation_maturity"] = str(confirmation_spec.get("maturity") or "")
    finalized["confirmation_current_claim"] = str(confirmation_spec.get("current_claim") or "")
    finalized["confirmation_accepted_runtime_claim"] = str(confirmation_spec.get("accepted_runtime_claim") or "")
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
