#!/usr/bin/env python3
"""Run isolated held-out evolved-skill experiments.

This module adds an experimental runner on top of the existing SkillClaw
components. It does not modify the formal publish path. Instead it:

1. builds one frozen candidate skill from selected source runs;
2. runs held-out blind cases under no-skill / seed-skill / candidate-skill;
3. stores lineage, hashes, leakage checks, and per-run result rows.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

try:
    from evaluation.cases.loader import load_case_definition
    from evaluation.reporting.feedback.build_feedback_bundle import build_feedback_bundles
    from evaluation.reporting.feedback.build_gate_report import build_gate_report
    from evaluation.reporting.feedback.build_skill_summary import build_skill_feedback
    from evaluation.runs.run_remote_case import run_auto as run_remote_case_auto
    from evolve_server.core.llm_client import AsyncLLMClient
    from evolve_server.core.utils import parse_skill_content
    from evolve_server.pipeline.execution import create_skill_from_sessions, evolve_skill_from_sessions
    from evolve_server.pipeline.summarizer import summarize_sessions_parallel
    from skillclaw import skillspace
    from skillclaw.config_store import ConfigStore
    from skillclaw.dashboard_ingest import (
        _extract_record_instruction,
        _extract_skill_names,
        _normalize_timestamp,
        _normalize_tool_calls,
        _trim_message,
    )
    from skillclaw.skill_bundle import bundle_entrypoint_text, bundle_tree_sha256, read_skill_bundle_with_meta
    from skillclaw.skill_markdown import build_skill_md
except ImportError:  # pragma: no cover - direct script execution
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from evaluation.cases.loader import load_case_definition
    from evaluation.reporting.feedback.build_feedback_bundle import build_feedback_bundles
    from evaluation.reporting.feedback.build_gate_report import build_gate_report
    from evaluation.reporting.feedback.build_skill_summary import build_skill_feedback
    from evaluation.runs.run_remote_case import run_auto as run_remote_case_auto
    from evolve_server.core.llm_client import AsyncLLMClient
    from evolve_server.core.utils import parse_skill_content
    from evolve_server.pipeline.execution import create_skill_from_sessions, evolve_skill_from_sessions
    from evolve_server.pipeline.summarizer import summarize_sessions_parallel
    from skillclaw import skillspace
    from skillclaw.config_store import ConfigStore
    from skillclaw.dashboard_ingest import (
        _extract_record_instruction,
        _extract_skill_names,
        _normalize_timestamp,
        _normalize_tool_calls,
        _trim_message,
    )
    from skillclaw.skill_bundle import bundle_entrypoint_text, bundle_tree_sha256, read_skill_bundle_with_meta
    from skillclaw.skill_markdown import build_skill_md


NO_SKILL_KEY = "__no_skill__"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _slug(text: str) -> str:
    chars: list[str] = []
    for ch in str(text):
        if ch.isalnum() or ch in {"-", "_", "."}:
            chars.append(ch)
        else:
            chars.append("-")
    value = "".join(chars).strip("-")
    return value or "item"


def _default_output_dir() -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return _repo_root() / "runtime" / "heldout_experiments" / stamp


def _heldout_experiment_slug(output_dir: Path, candidate_hash: str) -> str:
    name = _slug(output_dir.name)
    if name:
        return name
    short_hash = _slug(str(candidate_hash).strip()[:12])
    if short_hash:
        return short_hash
    return "heldout"


def _make_heldout_run_id(*, experiment_slug: str, case_slug: str, condition: str, repeat: int) -> str:
    return f"heldout-{experiment_slug}-{case_slug}-{condition}-r{repeat}"


def _collect_records(paths: list[Path]) -> list[tuple[Path, dict[str, Any]]]:
    rows: list[tuple[Path, dict[str, Any]]] = []
    for path in paths:
        rows.append((path, _load_json(path)))
    return rows


def _selected_skill_names(record: dict[str, Any]) -> list[str]:
    skill_injection = record.get("skill_injection")
    if isinstance(skill_injection, dict):
        return [str(item) for item in skill_injection.get("selected_skill_names") or [] if str(item).strip()]
    return []


def _infer_target_skill_name(records: list[tuple[Path, dict[str, Any]]]) -> str:
    skills = sorted(
        {
            skill
            for _, record in records
            for skill in _selected_skill_names(record)
            if str(skill).strip()
        }
    )
    if not skills:
        return NO_SKILL_KEY
    if len(skills) == 1:
        return skills[0]
    raise RuntimeError(
        "source finals reference multiple selected skills; pass --target-skill explicitly to choose which one to evolve"
    )


def _feedback_quality_flags(record: dict[str, Any]) -> list[str]:
    feedback = record.get("feedback")
    if not isinstance(feedback, dict):
        return []
    return [str(item) for item in feedback.get("quality_flags") or [] if str(item).strip()]


def _check_hit(record: dict[str, Any], key: str) -> bool:
    checks = record.get("checks")
    if not isinstance(checks, dict):
        return False
    item = checks.get(key)
    return bool(isinstance(item, dict) and item.get("hit"))


def _normalized_score(record: dict[str, Any]) -> float | None:
    score = record.get("score")
    max_score = record.get("max_score")
    if isinstance(score, (int, float)) and isinstance(max_score, (int, float)) and max_score:
        return round(float(score) / float(max_score), 4)
    return None


def _load_skill_catalog(skill_roots: list[Path]) -> dict[str, dict[str, Any]]:
    skills: dict[str, dict[str, Any]] = {}
    for root in skill_roots:
        if not root.is_dir():
            continue
        for skill_md in sorted(root.rglob("SKILL.md")):
            skill_dir = skill_md.parent
            bundle_files, _bundle_records, local_tree_sha = read_skill_bundle_with_meta(skill_dir)
            try:
                raw_md = bundle_entrypoint_text(bundle_files)
            except Exception:
                raw_md = skill_md.read_text(encoding="utf-8", errors="replace")
            parsed = parse_skill_content(skill_dir.name, raw_md)
            name = str(parsed.get("name") or skill_dir.name).strip()
            if not name:
                continue
            skills.setdefault(
                name,
                {
                    "name": name,
                    "description": str(parsed.get("description") or ""),
                    "category": str(parsed.get("category") or "general"),
                    "content": str(parsed.get("content") or ""),
                    "extra_frontmatter": parsed.get("extra_frontmatter") or {},
                    "skill_md": raw_md,
                    "local_tree_sha": local_tree_sha,
                    "local_path": str(skill_dir),
                },
            )
    return skills


def _default_skill_roots() -> list[Path]:
    layout = skillspace.default_layout()
    return [layout.source_dir, layout.live_dir]


def _build_llm_client() -> tuple[AsyncLLMClient, str]:
    cfg = ConfigStore().to_skillclaw_config()
    model = cfg.llm_model_id or cfg.model_name or "gpt-4o"
    client = AsyncLLMClient(
        api_key=cfg.llm_api_key,
        base_url=cfg.llm_api_base,
        model=model,
        max_tokens=8192,
        temperature=0.4,
    )
    return client, str(model)


def _load_segment_sessions(
    conversations_path: Path,
    *,
    allowed_segment_ids: set[str],
    fallback_session_ids: set[str],
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    if not conversations_path.is_file():
        raise FileNotFoundError(f"conversation record not found: {conversations_path}")

    with conversations_path.open(encoding="utf-8-sig", errors="replace") as handle:
        for line_no, raw_line in enumerate(handle, start=1):
            if not raw_line.strip():
                continue
            try:
                payload = json.loads(raw_line)
            except json.JSONDecodeError:
                continue
            if not isinstance(payload, dict):
                continue

            session_id = str(payload.get("session_id") or "").strip()
            segment_id = str(payload.get("session_segment_id") or session_id).strip()
            if not session_id:
                continue
            if allowed_segment_ids:
                if segment_id not in allowed_segment_ids:
                    continue
            elif fallback_session_ids and session_id not in fallback_session_ids:
                continue

            timestamp = _normalize_timestamp(str(payload.get("timestamp") or ""))
            try:
                turn_num = int(payload.get("turn", 0) or 0)
            except (TypeError, ValueError):
                turn_num = 0

            key = (session_id, segment_id)
            group = grouped.setdefault(
                key,
                {
                    "session_id": session_id,
                    "session_segment_id": segment_id,
                    "timestamp": "",
                    "turns": {},
                    "line_index": {},
                },
            )
            if timestamp and (not group["timestamp"] or timestamp > group["timestamp"]):
                group["timestamp"] = timestamp

            if turn_num <= 0:
                turn_num = max(group["turns"].keys(), default=0) + 1

            skill_injection = payload.get("skill_injection")
            injected_skill_names = _extract_skill_names(payload.get("selected_skill_names"))
            if not injected_skill_names and isinstance(skill_injection, dict):
                injected_skill_names = _extract_skill_names(skill_injection.get("selected_skill_names"))

            tool_results = [dict(item) for item in (payload.get("tool_results") or []) if isinstance(item, dict)]
            tool_errors = [
                dict(item)
                for item in tool_results
                if bool(item.get("has_error")) or str(item.get("error_type") or "").strip()
            ]

            turn_payload = {
                "turn_num": turn_num,
                "prompt_text": _extract_record_instruction(payload),
                "response_text": _trim_message(str(payload.get("response_text", "") or "")),
                "reasoning_content": payload.get("reasoning_content"),
                "tool_calls": _normalize_tool_calls(payload.get("tool_calls")),
                "read_skills": [],
                "modified_skills": [],
                "tool_results": tool_results,
                "tool_results_raw": tool_results,
                "tool_observations": tool_results,
                "tool_errors": tool_errors,
                "injected_skills": injected_skill_names,
                "prm_score": payload.get("prm_score"),
            }
            existing_line = group["line_index"].get(turn_num, -1)
            if line_no >= existing_line:
                group["turns"][turn_num] = turn_payload
                group["line_index"][turn_num] = line_no

    sessions: list[dict[str, Any]] = []
    for item in grouped.values():
        turns = [item["turns"][turn_num] for turn_num in sorted(item["turns"])]
        sessions.append(
            {
                "session_id": item["session_id"],
                "session_segment_id": item["session_segment_id"],
                "timestamp": item["timestamp"],
                "user_alias": "local",
                "num_turns": len(turns),
                "turns": turns,
                "source": "local-record-log",
                "outcome": "",
                "outcome_reasons": [],
                "outcome_reason_count": 0,
                "active_skills": [],
                "transcript_path": "",
                "trajectory_path": "",
                "record_path": str(conversations_path),
            }
        )
    return sessions


def _build_feedback_context(
    source_records: list[tuple[Path, dict[str, Any]]],
    *,
    target_skill: str,
) -> dict[str, Any] | None:
    skill_rows = build_skill_feedback(source_records)
    gate_rows = build_gate_report(skill_rows)
    gate_map = {str(item.get("skill") or ""): item for item in gate_rows if str(item.get("skill") or "").strip()}
    bundles = build_feedback_bundles(source_records, gate_map=gate_map, only_skills={target_skill})
    for bundle in bundles:
        if str(bundle.get("skill") or "").strip() == target_skill:
            return bundle
    return None


def _serialize_source_summary(records: list[tuple[Path, dict[str, Any]]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path, record in records:
        rows.append(
            {
                "path": str(path),
                "case_id": str(record.get("case_id") or ""),
                "session_id": str(record.get("session_id") or ""),
                "session_segment_id": str(record.get("session_segment_id") or ""),
                "selected_skill_names": _selected_skill_names(record),
                "score": record.get("score"),
                "max_score": record.get("max_score"),
                "normalized_score": _normalized_score(record),
                "quality_flags": _feedback_quality_flags(record),
            }
        )
    return rows


def _audit_source_quality(records: list[tuple[Path, dict[str, Any]]]) -> dict[str, Any]:
    total = len(records)
    normalized_scores = [score for _, record in records if (score := _normalized_score(record)) is not None]
    function_identity_miss = 0
    cve_identity_miss = 0
    function_hit = 0
    evidence_hit = 0
    root_cause_hit = 0
    for _, record in records:
        quality_flags = set(_feedback_quality_flags(record))
        if "function_identity_miss" in quality_flags:
            function_identity_miss += 1
        if "cve_identity_miss" in quality_flags:
            cve_identity_miss += 1
        if _check_hit(record, "function"):
            function_hit += 1
        if _check_hit(record, "evidence"):
            evidence_hit += 1
        if _check_hit(record, "root_cause"):
            root_cause_hit += 1

    issues: list[str] = []
    blocked = False
    if total > 0 and function_identity_miss == total:
        blocked = True
        issues.append("all_source_runs_have_function_identity_miss")
    if total > 0 and root_cause_hit == 0:
        blocked = True
        issues.append("no_source_run_has_root_cause_hit")

    return {
        "blocked": blocked,
        "issues": issues,
        "summary": {
            "source_run_count": total,
            "mean_normalized_score": round(sum(normalized_scores) / len(normalized_scores), 4) if normalized_scores else None,
            "function_identity_miss_count": function_identity_miss,
            "cve_identity_miss_count": cve_identity_miss,
            "function_hit_count": function_hit,
            "evidence_hit_count": evidence_hit,
            "root_cause_hit_count": root_cause_hit,
        },
    }


def _collect_leakage_terms(case: dict[str, Any]) -> list[str]:
    generic_terms = {
        "httpd",
        "webs",
        "lighttpd",
        "wireless.cgi",
        "login.cgi",
        "sprintf",
        "snprintf",
        "vsprintf",
        "strcpy",
        "strcat",
        "memcpy",
        "system",
        "popen",
    }
    generic_paths = {
        "vul_file/httpd",
        "vul_file/webs",
    }
    terms: list[str] = []
    truth = case.get("ground_truth")
    if isinstance(truth, dict):
        for key in ("cves", "files", "functions"):
            for item in truth.get(key) or []:
                text = str(item).strip()
                if text:
                    lowered = text.lower()
                    if lowered not in generic_paths and lowered not in generic_terms:
                        terms.append(text)
                    if "/" in text:
                        basename = Path(text).name.strip()
                        if basename and basename.lower() not in generic_terms:
                            terms.append(basename)
    return sorted({term for term in terms if term})


def _audit_candidate_leakage(candidate_skill: dict[str, Any], heldout_cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    skill_text = "\n".join(
        [
            str(candidate_skill.get("name") or ""),
            str(candidate_skill.get("description") or ""),
            str(candidate_skill.get("content") or ""),
        ]
    )
    lowered = skill_text.lower()
    rows: list[dict[str, Any]] = []
    for case in heldout_cases:
        case_id = str(case.get("case_id") or "")
        matches = [term for term in _collect_leakage_terms(case) if term.lower() in lowered]
        rows.append(
            {
                "case_id": case_id,
                "blocked": bool(matches),
                "matched_terms": matches,
            }
        )
    return rows


async def _generate_candidate_async(
    *,
    target_skill: str,
    source_sessions: list[dict[str, Any]],
    source_records: list[tuple[Path, dict[str, Any]]],
    current_skill: dict[str, Any] | None,
    existing_skill_names: list[str],
) -> tuple[dict[str, Any] | None, str]:
    llm, model = _build_llm_client()
    await summarize_sessions_parallel(llm, source_sessions)
    feedback_context = _build_feedback_context(source_records, target_skill=target_skill)
    if target_skill == NO_SKILL_KEY:
        candidate = await create_skill_from_sessions(
            llm,
            source_sessions,
            existing_skill_names=existing_skill_names,
            feedback_context=feedback_context,
        )
    else:
        candidate = await evolve_skill_from_sessions(
            llm,
            skill_name=target_skill,
            sessions=source_sessions,
            current_skill=current_skill,
            existing_skill_names=existing_skill_names,
            feedback_context=feedback_context,
        )
    return candidate, model


def build_candidate(args: argparse.Namespace) -> dict[str, Any]:
    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    source_paths = [Path(item).resolve() for item in args.source_final]
    source_records = _collect_records(source_paths)
    source_quality_audit = _audit_source_quality(source_records)
    _write_json(output_dir / "source_quality_audit.json", source_quality_audit)
    if bool(source_quality_audit.get("blocked")) and not bool(args.allow_source_quality_risk):
        issues = ", ".join(str(item) for item in source_quality_audit.get("issues") or [])
        raise RuntimeError(
            "source quality audit blocked candidate generation"
            + (f": {issues}" if issues else "")
            + "; rerun with cleaner source records or pass --allow-source-quality-risk to override"
        )

    explicit_target_skill = str(args.target_skill or "").strip()
    target_skill = explicit_target_skill or _infer_target_skill_name(source_records)
    segment_ids = {
        str(record.get("session_segment_id") or "").strip()
        for _, record in source_records
        if str(record.get("session_segment_id") or "").strip()
    }
    session_ids = {
        str(record.get("session_id") or "").strip()
        for _, record in source_records
        if str(record.get("session_id") or "").strip()
    }
    sessions = _load_segment_sessions(
        args.record_log,
        allowed_segment_ids=segment_ids,
        fallback_session_ids=session_ids,
    )
    if not sessions:
        raise RuntimeError("no source sessions found in the local conversation record")

    skill_catalog = _load_skill_catalog([Path(item) for item in args.skills_dir] if args.skills_dir else _default_skill_roots())
    current_skill = None if target_skill == NO_SKILL_KEY else skill_catalog.get(target_skill)
    if target_skill != NO_SKILL_KEY and current_skill is None:
        raise RuntimeError(f"target skill not found in configured skill roots: {target_skill}")

    candidate_result, model = asyncio.run(
        _generate_candidate_async(
            target_skill=target_skill,
            source_sessions=sessions,
            source_records=source_records,
            current_skill=current_skill,
            existing_skill_names=sorted(skill_catalog),
        )
    )
    if not isinstance(candidate_result, dict):
        raise RuntimeError("evolution pipeline returned no candidate skill")
    action = str(candidate_result.get("action") or "").strip()
    if action == "skip":
        raise RuntimeError("evolution pipeline chose skip; no candidate skill was generated")
    skill = candidate_result.get("skill")
    if not isinstance(skill, dict) or not str(skill.get("name") or "").strip():
        raise RuntimeError("evolution pipeline returned an invalid candidate skill")

    candidate_md = build_skill_md(skill)
    candidate_bundle = {"SKILL.md": candidate_md}
    candidate_sha = _sha256_text(candidate_md)
    candidate_tree_sha = bundle_tree_sha256(candidate_bundle)

    candidate_path = output_dir / "candidate_skill.json"
    candidate_wrapper = {
        "action": action,
        "rationale": str(candidate_result.get("rationale") or ""),
        "candidate_skill": skill,
        "candidate_skill_md": candidate_md,
        "candidate_skill_content_sha256": candidate_sha,
        "candidate_skill_tree_sha256": candidate_tree_sha,
    }
    _write_json(candidate_path, candidate_wrapper)

    feedback_context = _build_feedback_context(source_records, target_skill=target_skill)
    if feedback_context is not None:
        _write_json(output_dir / "source_feedback_context.json", feedback_context)

    manifest = {
        "created_at": _utc_now(),
        "target_skill": target_skill,
        "generator": "evolve_skill_from_sessions" if target_skill != NO_SKILL_KEY else "create_skill_from_sessions",
        "llm_model": model,
        "source_quality_audit": source_quality_audit,
        "source_records": _serialize_source_summary(source_records),
        "source_session_count": len(sessions),
        "source_session_ids": [str(item.get("session_id") or "") for item in sessions],
        "source_session_segment_ids": [str(item.get("session_segment_id") or "") for item in sessions],
        "current_skill": {
            "name": str(current_skill.get("name") or "") if isinstance(current_skill, dict) else "",
            "local_path": str(current_skill.get("local_path") or "") if isinstance(current_skill, dict) else "",
            "local_tree_sha": str(current_skill.get("local_tree_sha") or "") if isinstance(current_skill, dict) else "",
        },
        "candidate": {
            "path": str(candidate_path),
            "name": str(skill.get("name") or ""),
            "description": str(skill.get("description") or ""),
            "category": str(skill.get("category") or "general"),
            "content_sha256": candidate_sha,
            "tree_sha256": candidate_tree_sha,
        },
    }
    _write_json(output_dir / "candidate_manifest.json", manifest)
    return manifest


def _heldout_row(
    *,
    condition: str,
    case_path: Path,
    repeat: int,
    result: dict[str, Any],
    candidate_hash: str,
) -> dict[str, Any]:
    final_path = Path(str(result.get("local_final_enriched") or ""))
    final_record = _load_json(final_path) if final_path.is_file() else {}
    quality_flags = _feedback_quality_flags(final_record)
    confirmation = final_record.get("confirmation") if isinstance(final_record.get("confirmation"), dict) else {}
    return {
        "condition": condition,
        "case_path": str(case_path),
        "case_id": str(final_record.get("case_id") or case_path.stem),
        "repeat": repeat,
        "run_id": str(result.get("run_id") or ""),
        "session_id": str(final_record.get("session_id") or result.get("client_session_id") or ""),
        "session_segment_id": str(final_record.get("session_segment_id") or ""),
        "score": final_record.get("score"),
        "max_score": final_record.get("max_score"),
        "normalized_score": _normalized_score(final_record),
        "confirmation_status": str(confirmation.get("status") or ""),
        "selected_skill_names": _selected_skill_names(final_record),
        "predicted_cves": list((final_record.get("predictions") or {}).get("cves") or []),
        "predicted_files": list((final_record.get("predictions") or {}).get("files") or []),
        "predicted_functions": list((final_record.get("predictions") or {}).get("functions") or []),
        "file_hit": _check_hit(final_record, "file"),
        "function_hit": _check_hit(final_record, "function"),
        "cve_hit": _check_hit(final_record, "cve"),
        "evidence_hit": _check_hit(final_record, "evidence"),
        "root_cause_hit": _check_hit(final_record, "root_cause"),
        "function_identity_miss": "function_identity_miss" in quality_flags,
        "cve_identity_miss": "cve_identity_miss" in quality_flags,
        "candidate_tree_sha256": candidate_hash,
        "final_record_path": str(final_path),
    }


def _write_rows_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    headers = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def _require_successful_remote_run(result: dict[str, Any], *, run_id: str, output_dir: Path) -> None:
    run_result = result.get("run_result")
    exit_status = run_result.get("exit_status") if isinstance(run_result, dict) else None
    final_path = Path(str(result.get("local_final_enriched") or ""))
    if exit_status == 0 and final_path.is_file():
        return

    failure = {
        "run_id": run_id,
        "exit_status": exit_status,
        "remote_command": result.get("remote_command"),
        "run_result": run_result,
        "downloaded_artifacts": result.get("downloaded_artifacts"),
        "local_final_enriched": str(final_path),
    }
    _write_json(output_dir / f"failed_{_slug(run_id)}.json", failure)
    raise RuntimeError(
        f"held-out remote run failed: {run_id} (exit_status={exit_status}); "
        f"failure record: {output_dir / f'failed_{_slug(run_id)}.json'}"
    )


def _build_remote_run_namespace(
    *,
    args: argparse.Namespace,
    case_path: Path,
    run_id: str,
    condition: str,
    sync_repo: bool,
) -> argparse.Namespace:
    common = {
        "action": "run-auto",
        "case": case_path,
        "mode": args.mode,
        "run_id": run_id,
        "session_id": "",
        "preflight": args.preflight,
        "expected_provider": args.expected_provider,
        "skillclaw_url": args.skillclaw_url,
        "skillclaw_key": args.skillclaw_key,
        "expected_skill_count": args.expected_skill_count,
        "evolve_after_run": False,
        "evolve_url": args.evolve_url,
        "run_timeout": args.run_timeout,
        "host": args.host,
        "user": args.user,
        "port": args.port,
        "key_path": args.key_path,
        "password": args.password,
        "connect_timeout": args.connect_timeout,
        "remote_repo_root": args.remote_repo_root,
        "remote_manual_root": args.remote_manual_root,
        "remote_results_root": args.remote_results_root,
        "local_import_root": args.local_import_root,
        "local_session_dir": args.local_session_dir,
        "sync_repo": sync_repo,
        "remote_path_profile": args.remote_path_profile,
        "server_disable_skills": False,
        "server_force_skills": "",
        "server_inline_skill_json": None,
        "server_override_note": f"heldout:{condition}",
    }
    if condition == "no-skill":
        common["server_disable_skills"] = True
    elif condition == "seed-skill":
        common["server_force_skills"] = args.seed_force_skills
        common["server_inline_skill_json"] = Path(args.seed_inline_skill_json) if args.seed_inline_skill_json else None
    elif condition == "candidate-skill":
        common["server_inline_skill_json"] = Path(args.candidate_json)
    else:
        raise ValueError(f"unknown condition: {condition}")
    return SimpleNamespace(**common)


def run_heldout(args: argparse.Namespace) -> dict[str, Any]:
    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    candidate_wrapper = _load_json(Path(args.candidate_json))
    candidate_skill = candidate_wrapper.get("candidate_skill")
    if not isinstance(candidate_skill, dict):
        raise RuntimeError("candidate_json does not contain candidate_skill")
    candidate_hash = str(candidate_wrapper.get("candidate_skill_tree_sha256") or "")
    experiment_slug = _heldout_experiment_slug(output_dir, candidate_hash)

    heldout_cases = [load_case_definition(Path(item)) for item in args.heldout_case]
    leakage_rows = _audit_candidate_leakage(candidate_skill, heldout_cases)
    _write_json(output_dir / "heldout_leakage_audit.json", leakage_rows)
    if any(bool(row.get("blocked")) for row in leakage_rows) and not bool(args.allow_leakage):
        raise RuntimeError(
            "candidate leakage audit found direct held-out ground-truth terms; rerun with a cleaner candidate or pass --allow-leakage to override"
        )

    seed_force = str(args.seed_force_skills or "").strip()
    seed_inline = str(args.seed_inline_skill_json or "").strip()
    if bool(seed_force) == bool(seed_inline):
        raise RuntimeError(
            "seed condition requires exactly one of --seed-force-skills or --seed-inline-skill-json"
        )

    rows: list[dict[str, Any]] = []
    conditions = ["no-skill", "seed-skill", "candidate-skill"]
    run_counter = 0
    for case_item in args.heldout_case:
        case_path = Path(case_item)
        case_slug = _slug(case_path.stem)
        for repeat in range(1, max(1, int(args.repeats)) + 1):
            for condition in conditions:
                run_counter += 1
                run_id = _make_heldout_run_id(
                    experiment_slug=experiment_slug,
                    case_slug=case_slug,
                    condition=condition,
                    repeat=repeat,
                )
                run_args = _build_remote_run_namespace(
                    args=args,
                    case_path=case_path,
                    run_id=run_id,
                    condition=condition,
                    sync_repo=bool(args.sync_repo and run_counter == 1),
                )
                result = run_remote_case_auto(run_args)
                _require_successful_remote_run(result, run_id=run_id, output_dir=output_dir)
                rows.append(
                    _heldout_row(
                        condition=condition,
                        case_path=case_path,
                        repeat=repeat,
                        result=result,
                        candidate_hash=candidate_hash,
                    )
                )

    summary = {
        "created_at": _utc_now(),
        "candidate_json": str(Path(args.candidate_json).resolve()),
        "candidate_name": str(candidate_skill.get("name") or ""),
        "candidate_tree_sha256": candidate_hash,
        "heldout_cases": [str(Path(item).resolve()) for item in args.heldout_case],
        "conditions": conditions,
        "repeats": int(args.repeats),
        "row_count": len(rows),
        "leakage_audit": leakage_rows,
    }
    _write_json(output_dir / "heldout_manifest.json", summary)
    _write_json(output_dir / "heldout_results.json", rows)
    _write_rows_csv(output_dir / "heldout_results.csv", rows)
    return summary


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="action", required=True)

    build = subparsers.add_parser("build-candidate", help="Freeze one candidate skill from selected source runs.")
    build.add_argument("--source-final", action="append", required=True, help="Source final-enriched record path. Repeatable.")
    build.add_argument("--target-skill", default="", help=f"Existing skill to evolve. Use '{NO_SKILL_KEY}' for the no-skill bucket.")
    build.add_argument("--record-log", type=Path, default=_repo_root() / "runtime" / "records" / "conversations.jsonl")
    build.add_argument("--skills-dir", action="append", default=[], help="Skill root(s) to search. Defaults to skillspace/source and skillspace/live.")
    build.add_argument("--output-dir", type=Path, default=_default_output_dir())
    build.add_argument(
        "--allow-source-quality-risk",
        action="store_true",
        help="Override source quality blocking and allow candidate generation even when all source runs miss the target function.",
    )

    heldout = subparsers.add_parser("run-heldout", help="Run held-out blind cases under three isolated conditions.")
    heldout.add_argument("--candidate-json", required=True, help="Path to candidate_skill.json from build-candidate.")
    heldout.add_argument("--heldout-case", action="append", required=True, help="Held-out case JSON. Repeatable.")
    heldout.add_argument("--repeats", type=int, default=3)
    heldout.add_argument("--output-dir", type=Path, default=_default_output_dir())
    heldout.add_argument("--mode", default="blind-skillclaw-inline-guarded")
    heldout.add_argument("--seed-force-skills", default="", help="Comma-separated live skill names for the seed condition.")
    heldout.add_argument("--seed-inline-skill-json", default="", help="Optional inline skill JSON for the seed condition.")
    heldout.add_argument("--allow-leakage", action="store_true", help="Override the direct string-match leakage audit and continue anyway.")
    heldout.add_argument("--preflight", action="store_true")
    heldout.add_argument("--expected-provider", choices=["skillclaw", "deepseek", "unknown"], default=None)
    heldout.add_argument("--skillclaw-url", default="")
    heldout.add_argument("--skillclaw-key", default="")
    heldout.add_argument("--expected-skill-count", type=int, default=None)
    heldout.add_argument("--evolve-url", default="http://127.0.0.1:8787")
    heldout.add_argument("--run-timeout", type=float, default=900.0)
    heldout.add_argument("--host", help="Remote VM host.")
    heldout.add_argument("--user", help="Remote VM user.")
    heldout.add_argument("--port", type=int, default=None)
    heldout.add_argument("--key-path", default=None)
    heldout.add_argument("--password", default=None)
    heldout.add_argument("--connect-timeout", type=float, default=None)
    heldout.add_argument("--remote-repo-root", default="~/skillclaw-eval/SkillClaw")
    heldout.add_argument("--remote-manual-root", default="~/skillclaw-eval/manual_runs")
    heldout.add_argument("--remote-results-root", default="~/skillclaw-eval/results")
    heldout.add_argument("--local-import-root", type=Path, default=_repo_root() / "runtime" / "imports" / "heldout")
    heldout.add_argument("--local-session-dir", type=Path, default=_repo_root() / "runtime" / "records")
    heldout.add_argument("--sync-repo", action="store_true")
    heldout.add_argument("--remote-path-profile", default="vm-li")
    return parser


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.action == "build-candidate":
        result = build_candidate(args)
    elif args.action == "run-heldout":
        result = run_heldout(args)
    else:  # pragma: no cover
        raise AssertionError(f"unknown action: {args.action}")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
