"""Validated handoff from one evaluated run to the skill evolution service."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from evaluation.reporting.feedback.build_feedback_bundle import build_feedback_bundles
from evaluation.reporting.feedback.build_gate_report import build_gate_report
from evaluation.reporting.feedback.build_skill_summary import build_skill_feedback


JsonRequest = Callable[..., dict[str, Any]]


class EvolutionHandoffError(RuntimeError):
    """Raised when a run cannot enter the validated evolution path safely."""


def request_json(
    url: str,
    *,
    method: str = "GET",
    api_key: str = "",
    timeout: float = 30.0,
    json_body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    headers = {"Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    if json_body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(json_body, ensure_ascii=False).encode("utf-8")
    else:
        data = b"" if method.upper() in {"POST", "PUT", "PATCH"} else None
    request = Request(url, data=data, headers=headers, method=method.upper())
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise EvolutionHandoffError(f"{method.upper()} {url} failed: HTTP {exc.code} {detail}") from exc
    except URLError as exc:
        raise EvolutionHandoffError(f"{method.upper()} {url} failed: {exc.reason}") from exc
    try:
        value = json.loads(payload) if payload else {}
    except json.JSONDecodeError as exc:
        raise EvolutionHandoffError(f"{method.upper()} {url} returned invalid JSON") from exc
    if not isinstance(value, dict):
        raise EvolutionHandoffError(f"{method.upper()} {url} did not return a JSON object")
    return value


def build_run_feedback_bundle(final_record_path: Path, output_path: Path) -> dict[str, Any]:
    """Build a compact, run-scoped feedback bundle using existing report logic."""
    record = json.loads(final_record_path.read_text(encoding="utf-8-sig", errors="replace"))
    if not isinstance(record, dict):
        raise EvolutionHandoffError(f"final record is not a JSON object: {final_record_path}")
    session_id = str(record.get("session_id") or "").strip()
    if not session_id:
        raise EvolutionHandoffError("final record has no session_id; it cannot be joined to a SkillClaw session")
    validation = record.get("validation")
    if not isinstance(validation, dict) or not str(validation.get("status") or "").strip():
        raise EvolutionHandoffError("final record has no validator result")

    records = [(final_record_path, record)]
    skill_rows = build_skill_feedback(records)
    gate_rows = build_gate_report(skill_rows)
    gate_map = {str(row["skill"]): row for row in gate_rows if row.get("skill")}
    bundles = build_feedback_bundles(records, gate_map=gate_map)
    if not bundles:
        raise EvolutionHandoffError("final record contains no selected skills to evolve")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(output_path.suffix + ".tmp")
    temporary.write_text(json.dumps(bundles, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, output_path)
    return {
        "path": str(output_path),
        "session_id": session_id,
        "validation_status": validation.get("status"),
        "skills": [str(bundle.get("skill") or "") for bundle in bundles],
        "gate_decisions": {
            str(bundle.get("skill") or ""): str(bundle.get("gate_decision") or "") for bundle in bundles
        },
    }


def build_run_feedback_envelope(
    final_record_path: Path,
    *,
    client_session_id: str,
    session_segment_id: str,
) -> dict[str, Any]:
    record = json.loads(final_record_path.read_text(encoding="utf-8-sig", errors="replace"))
    if not isinstance(record, dict):
        raise EvolutionHandoffError(f"final record is not a JSON object: {final_record_path}")
    validation = record.get("validation")
    if not isinstance(validation, dict) or not str(validation.get("status") or "").strip():
        raise EvolutionHandoffError("final record has no validator result")
    records = [(final_record_path, record)]
    skill_rows = build_skill_feedback(records)
    gate_rows = build_gate_report(skill_rows)
    gate_map = {str(row["skill"]): row for row in gate_rows if row.get("skill")}
    bundles = build_feedback_bundles(records, gate_map=gate_map)
    run_id = str(record.get("run_id") or (record.get("run") or {}).get("run_id") or "").strip()
    if not run_id:
        raise EvolutionHandoffError("final record has no run_id")
    return {
        "schema_version": 1,
        "run_id": run_id,
        "case_id": str(record.get("case_id") or ""),
        "client_session_id": client_session_id,
        "session_segment_id": session_segment_id,
        "validation_status": str(validation.get("status") or ""),
        "attribution_status": "observational",
        "attribution_method": "co_selection_observation",
        "skill_feedback": bundles,
    }


def handoff_validated_run(
    final_record_path: Path,
    *,
    repo_root: Path,
    skillclaw_url: str,
    skillclaw_api_key: str,
    evolve_url: str,
    request: JsonRequest = request_json,
    trigger_attempts: int = 12,
    trigger_delay_seconds: float = 0.5,
) -> dict[str, Any]:
    """Close a SkillClaw session and let Evolve queue validated candidates."""
    evolve_base = evolve_url.rstrip("/")
    skillclaw_base = skillclaw_url.rstrip("/")
    status = request(f"{evolve_base}/status")
    if str(status.get("engine") or "") != "workflow":
        raise EvolutionHandoffError("the closed loop currently requires the workflow evolution engine")
    if str(status.get("publish_mode") or "") != "validated":
        raise EvolutionHandoffError("Evolve must run with --publish-mode validated; direct publishing is refused")
    record = json.loads(final_record_path.read_text(encoding="utf-8-sig", errors="replace"))
    session_id = str(record.get("session_id") or "").strip() if isinstance(record, dict) else ""
    if not session_id:
        raise EvolutionHandoffError("final record has no session_id")
    session_index = request(
        f"{skillclaw_base}/v1/sessions",
        api_key=skillclaw_api_key,
    )
    active_session = next(
        (
            item
            for item in session_index.get("sessions") or []
            if isinstance(item, dict) and str(item.get("session_id") or "") == session_id
        ),
        None,
    )
    recorded_segment_id = str(record.get("session_segment_id") or "").strip()
    active_segment_id = str((active_session or {}).get("session_segment_id") or "").strip()
    segment_id = recorded_segment_id or active_segment_id
    if not segment_id:
        raise EvolutionHandoffError(
            "the final record has no session_segment_id and SkillClaw has no matching active session"
        )
    feedback_envelope = build_run_feedback_envelope(
        final_record_path,
        client_session_id=session_id,
        session_segment_id=segment_id,
    )
    feedback_result = request(
        f"{evolve_base}/v1/run-feedback",
        method="POST",
        timeout=60.0,
        json_body=feedback_envelope,
    )
    if active_session and active_segment_id == segment_id:
        close_result = request(
            f"{skillclaw_base}/v1/sessions/{quote(session_id, safe='')}",
            method="DELETE",
            api_key=skillclaw_api_key,
        )
        if str(close_result.get("session_segment_id") or "") != segment_id:
            raise EvolutionHandoffError("SkillClaw closed a different session segment than the validated run")
    else:
        close_result = {
            "deleted": False,
            "reason": "segment_already_closed" if not active_session else "client_session_has_newer_segment",
            "session_id": session_id,
            "session_segment_id": segment_id,
        }

    trigger_result: dict[str, Any] | None = None
    receipt_result: dict[str, Any] | None = None
    run_id = str(feedback_envelope["run_id"])
    receipt_url = (
        f"{evolve_base}/v1/run-feedback/status?run_id={quote(run_id, safe='')}"
        f"&session_segment_id={quote(segment_id, safe='')}"
    )
    for attempt in range(max(1, trigger_attempts)):
        trigger_result = request(f"{evolve_base}/trigger", method="POST", timeout=900.0)
        receipt_result = request(receipt_url)
        if int(trigger_result.get("sessions") or 0) > 0 or str(receipt_result.get("status") or "") == "consumed":
            break
        if attempt + 1 < trigger_attempts:
            time.sleep(max(0.0, trigger_delay_seconds))
    if (
        not trigger_result
        or (
            int(trigger_result.get("sessions") or 0) <= 0
            and str((receipt_result or {}).get("status") or "") != "consumed"
        )
    ):
        raise EvolutionHandoffError("SkillClaw closed the session, but Evolve did not receive it in time")
    unsafe_uploads = [
        item
        for item in trigger_result.get("evolutions") or []
        if isinstance(item, dict)
        and segment_id in [str(value) for value in item.get("session_ids") or []]
        and item.get("uploaded")
    ]
    if unsafe_uploads:
        raise EvolutionHandoffError("the current session unexpectedly published a skill without candidate validation")

    return {
        "status": "handed_off",
        "session_id": session_id,
        "session_segment_id": segment_id,
        "feedback": {
            "queue": feedback_result,
            "validation_status": feedback_envelope["validation_status"],
            "skills": [str(item.get("skill") or "") for item in feedback_envelope["skill_feedback"]],
            "attribution_status": feedback_envelope["attribution_status"],
        },
        "session_close": close_result,
        "evolve": trigger_result,
        "consumption_receipt": receipt_result,
        "next_stage": "candidate_validation" if int(trigger_result.get("candidates_queued") or 0) else "no_candidate",
    }
