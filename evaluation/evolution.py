"""Validated handoff from one evaluated run to the skill evolution service."""

from __future__ import annotations

import json
import os
import subprocess
import sys
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


def _collect_validation_job_ids(trigger_result: dict[str, Any], session_segment_id: str) -> list[str]:
    job_ids: list[str] = []
    for item in trigger_result.get("evolutions") or []:
        if not isinstance(item, dict):
            continue
        session_ids = [str(value) for value in item.get("session_ids") or []]
        if session_segment_id not in session_ids:
            continue
        job_id = str(item.get("validation_job_id") or "").strip()
        if job_id:
            job_ids.append(job_id)
    return job_ids


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_validation_runtime_paths() -> tuple[Any, Path]:
    from skillclaw.config_store import ConfigStore

    cfg = ConfigStore().to_skillclaw_config()
    local_root = Path(str(getattr(cfg, "sharing_local_root", "") or "")).expanduser()
    group_id = str(getattr(cfg, "sharing_group_id", "default") or "default")
    return cfg, local_root / group_id


def _load_validation_decisions(job_ids: list[str]) -> dict[str, dict[str, Any] | None]:
    _, group_root = _load_validation_runtime_paths()
    decisions_dir = group_root / "gate_decisions"
    legacy_decisions_dir = group_root / "validation_decisions"
    decisions: dict[str, dict[str, Any] | None] = {}
    for job_id in job_ids:
        path = decisions_dir / f"{job_id}.json"
        if not path.is_file():
            path = legacy_decisions_dir / f"{job_id}.json"
        if not path.is_file():
            decisions[job_id] = None
            continue
        try:
            value = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            decisions[job_id] = None
            continue
        decisions[job_id] = value if isinstance(value, dict) else None
    return decisions


def _run_targeted_validation_jobs(job_ids: list[str]) -> dict[str, Any]:
    script = """
import asyncio
import json
import sys

from skillclaw.config_store import ConfigStore
from skillclaw.replay_gate_store import ReplayGateStore
from skillclaw.replay_gate_worker import ReplayGateWorker

target_job_ids = json.loads(sys.argv[1])
cfg = ConfigStore().to_skillclaw_config()
store = ReplayGateStore.from_config(cfg)
worker = ReplayGateWorker(cfg)
summary = {
    "requested_job_ids": list(target_job_ids),
    "validated_jobs": 0,
    "skipped_jobs": 0,
    "results": [],
}

async def main():
    for job_id in target_job_ids:
        existing = store.load_result(job_id, worker._user_alias)
        if isinstance(existing, dict):
            summary["results"].append({"job_id": job_id, "status": "already_validated"})
            continue
        job = store.load_job(job_id)
        if not isinstance(job, dict):
            summary["skipped_jobs"] += 1
            summary["results"].append({"job_id": job_id, "status": "missing_job"})
            continue
        try:
            result = await worker._validate_job(job)
        except Exception as exc:
            summary["skipped_jobs"] += 1
            summary["results"].append({"job_id": job_id, "status": "error", "error": str(exc)})
            continue
        store.save_result(job_id, worker._user_alias, result)
        summary["validated_jobs"] += 1
        summary["results"].append(
            {
                "job_id": job_id,
                "status": "validated",
                "accepted": bool(result.get("accepted")),
                "score": result.get("score"),
            }
        )

asyncio.run(main())
print(json.dumps(summary, ensure_ascii=False))
"""
    completed = subprocess.run(
        [sys.executable, "-c", script, json.dumps(job_ids, ensure_ascii=False)],
        cwd=_repo_root(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode != 0:
        raise EvolutionHandoffError(
            f"local validation run-once failed with exit code {completed.returncode}: {completed.stderr.strip()}"
        )
    stdout = (completed.stdout or "").strip()
    try:
        parsed = json.loads(stdout) if stdout else {}
    except json.JSONDecodeError as exc:
        raise EvolutionHandoffError(f"targeted validation returned invalid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise EvolutionHandoffError("targeted validation did not return a JSON object")
    parsed["returncode"] = completed.returncode
    if completed.stderr:
        parsed["stderr"] = completed.stderr.strip()
    return parsed


def _finalize_candidate_validation_jobs(
    *,
    job_ids: list[str],
    evolve_url: str,
    request: JsonRequest,
    max_attempts: int = 5,
    attempt_delay_seconds: float = 0.2,
) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "status": "not_needed" if not job_ids else "pending",
        "job_ids": list(job_ids),
        "attempts": 0,
        "validation_runs": [],
        "trigger_runs": [],
        "decisions": {},
        "pending_job_ids": [],
    }
    if not job_ids:
        return summary

    try:
        cfg, group_root = _load_validation_runtime_paths()
    except Exception as exc:
        summary["status"] = "error"
        summary["error"] = f"failed to load validation runtime: {exc}"
        return summary

    if str(getattr(cfg, "sharing_backend", "") or "").strip().lower() != "local":
        summary["status"] = "skipped"
        summary["reason"] = "local validation followup currently requires sharing.backend=local"
        return summary
    if not group_root.parent.exists():
        summary["status"] = "error"
        summary["error"] = f"validation share root not found: {group_root.parent}"
        return summary
    if not bool(getattr(cfg, "validation_enabled", False)):
        summary["status"] = "skipped"
        summary["reason"] = "validation disabled"
        return summary
    if not bool(getattr(cfg, "sharing_enabled", False)):
        summary["status"] = "skipped"
        summary["reason"] = "sharing disabled"
        return summary

    evolve_base = evolve_url.rstrip("/")
    decisions = _load_validation_decisions(job_ids)
    if all(isinstance(decisions.get(job_id), dict) for job_id in job_ids):
        summary["status"] = "already_decided"
        summary["decisions"] = decisions
        return summary

    for attempt in range(max(1, max_attempts)):
        summary["attempts"] = attempt + 1
        validation_result = _run_targeted_validation_jobs(job_ids)
        summary["validation_runs"].append(validation_result)

        trigger_result = request(f"{evolve_base}/trigger", method="POST", timeout=900.0)
        summary["trigger_runs"].append(
            {
                "sessions": int(trigger_result.get("sessions") or 0),
                "actions": int(trigger_result.get("actions") or 0),
                "candidates_queued": int(trigger_result.get("candidates_queued") or 0),
                "published_after_validation": int(trigger_result.get("published_after_validation") or 0),
                "validation_publish": trigger_result.get("validation_publish"),
            }
        )

        decisions = _load_validation_decisions(job_ids)
        if all(isinstance(decisions.get(job_id), dict) for job_id in job_ids):
            summary["status"] = "completed"
            break
        if attempt + 1 < max_attempts:
            time.sleep(max(0.0, attempt_delay_seconds))

    summary["decisions"] = decisions
    summary["pending_job_ids"] = [
        job_id for job_id, decision in decisions.items() if not isinstance(decision, dict)
    ]
    if summary["status"] == "pending":
        summary["status"] = "partial" if summary["pending_job_ids"] else "completed"
    return summary


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
    confirmation_result = record.get("confirmation")
    if not (isinstance(confirmation_result, dict) and str(confirmation_result.get("status") or "").strip()):
        confirmation_result = record.get("validation")
    if not isinstance(confirmation_result, dict) or not str(confirmation_result.get("status") or "").strip():
        raise EvolutionHandoffError("final record has no confirmation result")

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
        "confirmation_status": confirmation_result.get("status"),
        "validation_status": confirmation_result.get("status"),
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
    confirmation_result = record.get("confirmation")
    if not (isinstance(confirmation_result, dict) and str(confirmation_result.get("status") or "").strip()):
        confirmation_result = record.get("validation")
    if not isinstance(confirmation_result, dict) or not str(confirmation_result.get("status") or "").strip():
        raise EvolutionHandoffError("final record has no confirmation result")
    records = [(final_record_path, record)]
    skill_rows = build_skill_feedback(records)
    gate_rows = build_gate_report(skill_rows)
    gate_map = {str(row["skill"]): row for row in gate_rows if row.get("skill")}
    bundles = build_feedback_bundles(records, gate_map=gate_map)
    selected_skill_names = _extract_selected_skill_names(record)
    run_id = str(record.get("run_id") or (record.get("run") or {}).get("run_id") or "").strip()
    if not run_id:
        raise EvolutionHandoffError("final record has no run_id")
    return {
        "schema_version": 1,
        "run_id": run_id,
        "case_id": str(record.get("case_id") or ""),
        "client_session_id": client_session_id,
        "session_segment_id": session_segment_id,
        "confirmation_status": str(confirmation_result.get("status") or ""),
        "validation_status": str(confirmation_result.get("status") or ""),
        "attribution_status": "observational" if selected_skill_names else "no_selected_skills_control",
        "attribution_method": "co_selection_observation" if selected_skill_names else "control_blank_skillset",
        "skill_feedback": bundles,
    }


def _extract_confirmation_result(record: dict[str, Any]) -> dict[str, Any]:
    confirmation_result = record.get("confirmation")
    if not (isinstance(confirmation_result, dict) and str(confirmation_result.get("status") or "").strip()):
        confirmation_result = record.get("validation")
    if not isinstance(confirmation_result, dict) or not str(confirmation_result.get("status") or "").strip():
        raise EvolutionHandoffError("final record has no confirmation result")
    return confirmation_result


def _extract_selected_skill_names(record: dict[str, Any]) -> list[str]:
    raw_names = record.get("selected_skill_names")
    if not isinstance(raw_names, list):
        raw_names = (record.get("skill_injection") or {}).get("selected_skill_names")
    if not isinstance(raw_names, list):
        return []
    seen: set[str] = set()
    selected: list[str] = []
    for value in raw_names:
        name = str(value or "").strip()
        if name and name not in seen:
            seen.add(name)
            selected.append(name)
    return selected


def _build_synthetic_session_record(
    record: dict[str, Any],
    *,
    segment_id: str,
    session_id: str,
) -> dict[str, Any]:
    """Build a minimal session record from an enriched final record.

    Used when the API server has no active session (remote VM runs) so
    that the evolve server can still pair validated feedback with a
    session record and proceed with evolution.
    """
    from datetime import datetime, timezone

    predictions = record.get("predictions") or {}
    root_cause = str(record.get("root_cause") or "")
    evidence = str(record.get("evidence") or "")
    selected_skill_names = record.get("selected_skill_names") or []
    skill_injection = record.get("skill_injection") or {}

    response_parts: list[str] = []
    if root_cause:
        response_parts.append("Root cause: " + root_cause)
    if evidence:
        response_parts.append("Evidence: " + evidence)
    predicted_functions = predictions.get("functions") or []
    if predicted_functions:
        response_parts.append("Predicted functions: " + ", ".join(str(f) for f in predicted_functions))
    predicted_files = predictions.get("files") or []
    if predicted_files:
        response_parts.append("Predicted files: " + ", ".join(str(f) for f in predicted_files))
    response_text = "\n\n".join(response_parts) if response_parts else "(no agent output captured)"

    turn: dict[str, Any] = {
        "prompt_text": str(record.get("case_id") or ""),
        "response_text": response_text,
        "selected_skill_names": list(selected_skill_names),
    }
    if isinstance(skill_injection, dict) and skill_injection:
        turn["skill_injection"] = skill_injection

    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    return {
        "session_id": segment_id,
        "client_session_id": session_id,
        "session_segment_id": segment_id,
        "segment_status": "closed",
        "segment_closed_at": now,
        "timestamp": now,
        "user_alias": "remote_vm",
        "num_turns": 1,
        "turns": [turn],
    }


def _close_matching_session_segment(
    *,
    active_session: dict[str, Any] | None,
    active_segment_id: str,
    segment_id: str,
    session_id: str,
    skillclaw_base: str,
    skillclaw_api_key: str,
    request: JsonRequest,
) -> dict[str, Any]:
    if active_session and active_segment_id == segment_id:
        close_result = request(
            f"{skillclaw_base}/v1/sessions/{quote(session_id, safe='')}",
            method="DELETE",
            api_key=skillclaw_api_key,
        )
        if str(close_result.get("session_segment_id") or "") != segment_id:
            raise EvolutionHandoffError("SkillClaw closed a different session segment than the validated run")
        return close_result
    return {
        "deleted": False,
        "reason": "segment_already_closed" if not active_session else "client_session_has_newer_segment",
        "session_id": session_id,
        "session_segment_id": segment_id,
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
    if not isinstance(record, dict):
        raise EvolutionHandoffError(f"final record is not a JSON object: {final_record_path}")
    confirmation_result = _extract_confirmation_result(record)
    selected_skill_names = _extract_selected_skill_names(record)
    session_id = str(record.get("session_id") or "").strip()
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
    feedback_bundle_path = Path(
        str(status.get("feedback_bundle_path") or (repo_root / "runtime" / "evolve" / "skill_feedback_bundle.json"))
    )
    if not feedback_bundle_path.is_absolute():
        feedback_bundle_path = (repo_root / feedback_bundle_path).resolve()
    runtime_feedback_bundle = build_run_feedback_bundle(final_record_path, feedback_bundle_path)
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
    close_result = _close_matching_session_segment(
        active_session=active_session,
        active_segment_id=active_segment_id,
        segment_id=segment_id,
        session_id=session_id,
        skillclaw_base=skillclaw_base,
        skillclaw_api_key=skillclaw_api_key,
        request=request,
    )

    synthesize_result: dict[str, Any] | None = None
    if not close_result.get("deleted"):
        synthetic_session = _build_synthetic_session_record(
            record, segment_id=segment_id, session_id=session_id
        )
        synthesize_result = request(
            f"{evolve_base}/v1/sessions/synthesize",
            method="POST",
            timeout=30.0,
            json_body=synthetic_session,
        )

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
        if str(receipt_result.get("status") or "") == "consumed":
            break
        if attempt + 1 < trigger_attempts:
            time.sleep(max(0.0, trigger_delay_seconds))
    receipt_status = str((receipt_result or {}).get("status") or "")
    if receipt_status != "consumed":
        if trigger_result and bool(trigger_result.get("had_processing_error")):
            raise EvolutionHandoffError(
                "Evolve received the session but failed during processing; run feedback was not consumed"
            )
        raise EvolutionHandoffError("SkillClaw closed the session, but Evolve did not consume it in time")
    unsafe_uploads = [
        item
        for item in trigger_result.get("evolutions") or []
        if isinstance(item, dict)
        and segment_id in [str(value) for value in item.get("session_ids") or []]
        and item.get("uploaded")
    ]
    if unsafe_uploads:
        raise EvolutionHandoffError("the current session unexpectedly published a skill without candidate validation")

    validation_job_ids = _collect_validation_job_ids(trigger_result, segment_id)
    validation_followup = _finalize_candidate_validation_jobs(
        job_ids=validation_job_ids,
        evolve_url=evolve_base,
        request=request,
        max_attempts=max(1, len(validation_job_ids) + 2),
        attempt_delay_seconds=trigger_delay_seconds,
    )

    return {
        "status": "handed_off",
        "session_id": session_id,
        "session_segment_id": segment_id,
        "feedback": {
            "queue": feedback_result,
            "confirmation_status": feedback_envelope["confirmation_status"],
            "validation_status": feedback_envelope["validation_status"],
            "skills": [str(item.get("skill") or "") for item in feedback_envelope["skill_feedback"]],
            "attribution_status": feedback_envelope["attribution_status"],
            "selected_skills": selected_skill_names,
        },
        "runtime_feedback_bundle": runtime_feedback_bundle,
        "session_close": close_result,
        "session_synthesize": synthesize_result,
        "evolve": trigger_result,
        "consumption_receipt": receipt_result,
        "next_stage": "candidate_validation" if int(trigger_result.get("candidates_queued") or 0) else "no_candidate",
        "validation_followup": validation_followup,
    }
