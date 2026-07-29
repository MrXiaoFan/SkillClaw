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
) -> dict[str, Any]:
    headers = {"Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
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
    if int(status.get("pending_sessions") or 0) != 0:
        raise EvolutionHandoffError("Evolve already has pending sessions; refusing to mix feedback from different runs")

    configured_path = str(status.get("feedback_bundle_path") or "").strip()
    if not configured_path:
        raise EvolutionHandoffError("Evolve status does not expose feedback_bundle_path")
    feedback_path = Path(configured_path)
    if not feedback_path.is_absolute():
        feedback_path = repo_root / feedback_path
    feedback_path = feedback_path.resolve()
    runtime_root = (repo_root / "runtime").resolve()
    try:
        feedback_path.relative_to(runtime_root)
    except ValueError as exc:
        raise EvolutionHandoffError("feedback_bundle_path must be under runtime/ to avoid overwriting reports") from exc

    feedback = build_run_feedback_bundle(final_record_path, feedback_path)
    session_id = str(feedback["session_id"])
    close_result = request(
        f"{skillclaw_base}/v1/sessions/{quote(session_id, safe='')}",
        method="DELETE",
        api_key=skillclaw_api_key,
    )

    trigger_result: dict[str, Any] | None = None
    for attempt in range(max(1, trigger_attempts)):
        trigger_result = request(f"{evolve_base}/trigger", method="POST", timeout=900.0)
        if int(trigger_result.get("sessions") or 0) > 0:
            break
        if attempt + 1 < trigger_attempts:
            time.sleep(max(0.0, trigger_delay_seconds))
    if not trigger_result or int(trigger_result.get("sessions") or 0) <= 0:
        raise EvolutionHandoffError("SkillClaw closed the session, but Evolve did not receive it in time")
    unsafe_uploads = [
        item
        for item in trigger_result.get("evolutions") or []
        if isinstance(item, dict)
        and session_id in [str(value) for value in item.get("session_ids") or []]
        and item.get("uploaded")
    ]
    if unsafe_uploads:
        raise EvolutionHandoffError("the current session unexpectedly published a skill without candidate validation")

    return {
        "status": "handed_off",
        "session_id": session_id,
        "feedback": feedback,
        "session_close": close_result,
        "evolve": trigger_result,
        "next_stage": "candidate_validation" if int(trigger_result.get("candidates_queued") or 0) else "no_candidate",
    }
