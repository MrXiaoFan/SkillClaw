"""
Core orchestrator for the current session-level evolve_server pipeline.

Active flow:
1. Drain pending sessions from shared storage.
2. Summarize sessions and extract metadata.
3. Optionally backfill a session-level score with session_judge.
4. Aggregate sessions by referenced skill.
5. Evolve existing-skill groups or create new skills from no-skill groups.
6. Upload skills, persist registry state, and ack processed sessions.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Request

from skillclaw.skill_bundle import bundle_tree_sha256
from skillclaw.validation_store import ValidationStore

from ..core.config import EvolveServerConfig
from ..core.constants import NO_SKILL_KEY, DecisionAction
from ..core.llm_client import AsyncLLMClient
from ..core.skill_registry import SkillIDRegistry
from ..core.utils import build_skill_md, parse_skill_content
from ..pipeline.aggregation import aggregate_sessions_by_skill
from ..pipeline.execution import (
    create_skill_from_sessions,
    evolve_skill_from_sessions,
    execute_merge,
    set_evolve_debug_dir,
)
from ..pipeline.session_judge import judge_sessions_parallel
from ..pipeline.skill_verifier import verify_skill_candidate
from ..pipeline.summarizer import set_summarizer_debug_dir, summarize_sessions_parallel
from ..storage.oss_helpers import (
    delete_object_keys,
    delete_session_keys,
    fetch_skill_content,
    list_run_feedback_keys,
    list_session_keys,
    read_json_object,
    save_manifest,
    save_version_bundle,
    write_json_object,
)
from .common import EvolveEngineMixin

logger = logging.getLogger(__name__)


class EvolveServer(EvolveEngineMixin):
    """Session-level evolve server backed by shared object storage."""

    def __init__(
        self,
        config: EvolveServerConfig,
        *,
        mock: bool = False,
        mock_root: str | None = None,
    ) -> None:
        self.config = config
        self._mock = mock
        self._bucket = self._build_bucket(config, mock=mock, mock_root=mock_root)
        self._prefix = f"{config.group_id}/"
        self._llm = AsyncLLMClient(
            api_key=config.llm_api_key,
            base_url=config.llm_base_url,
            model=config.llm_model,
            max_tokens=config.llm_max_tokens,
            temperature=config.llm_temperature,
        )
        self._validation_store = ValidationStore(
            backend=self.config.storage_backend,
            endpoint=self.config.storage_endpoint,
            bucket=self.config.storage_bucket,
            access_key_id=self.config.storage_access_key_id,
            secret_access_key=self.config.storage_secret_access_key,
            region=self.config.storage_region,
            session_token=self.config.storage_session_token,
            local_root=self.config.local_root,
            group_id=self.config.group_id,
        )
        self._id_registry = SkillIDRegistry()
        self._nacos_skill_client = self._build_nacos_skill_client()
        self._running = False

        set_evolve_debug_dir(config.debug_dump_dir)
        set_summarizer_debug_dir(config.debug_dump_dir)
        if not self._uses_nacos_skill_registry():
            self._id_registry.load_from_oss(self._bucket, self._prefix)

    def _load_feedback_bundle(self) -> list[dict[str, Any]] | None:
        raw_path = str(self.config.feedback_bundle_path or "").strip()
        if not raw_path:
            return None
        path = Path(raw_path)
        if not path.is_file():
            logger.info(
                "[EvolveServer] feedback bundle not found at %s; continuing without it",
                path,
            )
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning(
                "[EvolveServer] failed to parse feedback bundle %s: %s",
                path,
                exc,
            )
            return None
        if not isinstance(payload, list):
            logger.warning("[EvolveServer] feedback bundle %s is not a list; ignoring", path)
            return None
        logger.info(
            "[EvolveServer] loaded validator-backed feedback bundle: %d skill record(s) from %s",
            len(payload),
            path,
        )
        return [item for item in payload if isinstance(item, dict)]

    @staticmethod
    def _feedback_map(feedback_bundle: list[dict[str, Any]] | None) -> dict[str, dict[str, Any]]:
        if not isinstance(feedback_bundle, list):
            return {}
        return {
            str(item.get("skill") or "").strip(): item
            for item in feedback_bundle
            if str(item.get("skill") or "").strip()
        }

    async def _load_validated_pairs(
        self,
    ) -> tuple[list[dict[str, Any]], list[str], list[str], dict[str, int]]:
        session_keys = await self._call_storage(list_session_keys, self._bucket, self._prefix)
        feedback_keys = await self._call_storage(list_run_feedback_keys, self._bucket, self._prefix)
        feedback_by_segment: dict[str, list[tuple[str, dict[str, Any]]]] = {}
        for key in feedback_keys:
            payload = await self._call_storage(read_json_object, self._bucket, key)
            if not isinstance(payload, dict):
                continue
            segment_id = str(payload.get("session_segment_id") or "").strip()
            if segment_id:
                feedback_by_segment.setdefault(segment_id, []).append((key, payload))

        ready_sessions: list[dict[str, Any]] = []
        ready_session_keys: list[str] = []
        ready_feedback_keys: list[str] = []
        closed_unmatched = 0
        active_sessions = 0
        matched_segments: set[str] = set()
        for key in session_keys:
            session = await self._call_storage(read_json_object, self._bucket, key)
            if not isinstance(session, dict):
                continue
            if str(session.get("segment_status") or "") != "closed":
                active_sessions += 1
                continue
            segment_id = str(session.get("session_segment_id") or session.get("session_id") or "").strip()
            client_session_id = str(session.get("client_session_id") or "").strip()
            matches = [
                item
                for item in feedback_by_segment.get(segment_id, [])
                if not client_session_id
                or str(item[1].get("client_session_id") or "").strip() == client_session_id
            ]
            if not matches:
                closed_unmatched += 1
                continue
            paired = dict(session)
            paired["validator_feedback"] = [payload for _, payload in matches]
            ready_sessions.append(paired)
            ready_session_keys.append(key)
            ready_feedback_keys.extend(feedback_key for feedback_key, _ in matches)
            matched_segments.add(segment_id)

        unmatched_feedback = sum(
            len(items)
            for segment_id, items in feedback_by_segment.items()
            if segment_id not in matched_segments
        )
        queue = {
            "ready_pairs": len(ready_sessions),
            "active_sessions": active_sessions,
            "closed_sessions_waiting_feedback": closed_unmatched,
            "feedback_waiting_session": unmatched_feedback,
        }
        return ready_sessions, ready_session_keys, ready_feedback_keys, queue

    @classmethod
    def _paired_feedback_map(cls, sessions: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for session in sessions:
            for envelope in session.get("validator_feedback") or []:
                if not isinstance(envelope, dict):
                    continue
                for item in envelope.get("skill_feedback") or []:
                    if not isinstance(item, dict):
                        continue
                    skill = str(item.get("skill") or "").strip()
                    if skill:
                        grouped.setdefault(skill, []).append(item)

        merged: dict[str, dict[str, Any]] = {}
        decision_order = {"demote": 0, "revise": 1, "insufficient_evidence": 2, "keep": 3, "promote": 4}
        for skill, rows in grouped.items():
            item = dict(rows[-1])
            summaries = [row.get("summary") for row in rows if isinstance(row.get("summary"), dict)]
            dimensions = [row.get("dimensions") for row in rows if isinstance(row.get("dimensions"), dict)]
            selected_runs = sum(int(summary.get("selected_runs") or 0) for summary in summaries)
            weighted_score = sum(
                float(summary.get("mean_score") or 0) * int(summary.get("selected_runs") or 0)
                for summary in summaries
            )
            summary_keys = {key for summary in summaries for key in summary if key != "mean_score"}
            item["summary"] = {
                key: sum(int(summary.get(key) or 0) for summary in summaries)
                for key in summary_keys
            }
            item["summary"]["mean_score"] = round(weighted_score / selected_runs, 3) if selected_runs else None
            dimension_keys = {key for dimension in dimensions for key in dimension}
            item["dimensions"] = {
                key: sum(int(dimension.get(key) or 0) for dimension in dimensions)
                for key in dimension_keys
            }
            item["gate_decision"] = min(
                (str(row.get("gate_decision") or "unknown") for row in rows),
                key=lambda value: decision_order.get(value, 2),
            )
            for key in ("gate_reasons", "gate_suggestions", "revision_directives"):
                item[key] = sorted({str(value) for row in rows for value in row.get(key) or [] if str(value).strip()})
            item["attribution_status"] = "observational"
            item["attribution_note"] = (
                "The validator confirms the run outcome, but does not by itself prove that this selected skill caused it."
            )
            merged[skill] = item
        return merged

    def _run_receipt_key(self, session_segment_id: str, run_id: str) -> str:
        run_key = hashlib.sha256(run_id.encode("utf-8")).hexdigest()[:20]
        return f"{self._prefix}run_receipts/{session_segment_id}/{run_key}.json"

    async def _write_consumption_receipts(
        self,
        sessions: list[dict[str, Any]],
        records: list[dict[str, Any]],
    ) -> None:
        for session in sessions:
            for envelope in session.get("validator_feedback") or []:
                if not isinstance(envelope, dict):
                    continue
                segment_id = str(envelope.get("session_segment_id") or "").strip()
                run_id = str(envelope.get("run_id") or "").strip()
                if not segment_id or not run_id:
                    continue
                segment_records = [
                    record
                    for record in records
                    if segment_id in {str(value) for value in record.get("session_ids") or []}
                ]
                receipt = {
                    "status": "consumed",
                    "consumed_at": datetime.now(timezone.utc).isoformat(),
                    "run_id": run_id,
                    "client_session_id": str(envelope.get("client_session_id") or ""),
                    "session_segment_id": segment_id,
                    "candidate_count": sum(
                        1 for record in segment_records if record.get("action") == "queued_for_validation"
                    ),
                    "uploaded_count": sum(1 for record in segment_records if record.get("uploaded")),
                }
                await self._call_storage(
                    write_json_object,
                    self._bucket,
                    self._run_receipt_key(segment_id, run_id),
                    receipt,
                )

    def _uses_nacos_skill_registry(self) -> bool:
        return str(getattr(self.config, "skill_storage_backend", "") or "").strip().lower() == "nacos"

    def _build_nacos_skill_client(self) -> Any | None:
        if not self._uses_nacos_skill_registry():
            return None
        from skillclaw.nacos_skill_hub import NacosSkillClient

        return NacosSkillClient(
            server=str(getattr(self.config, "nacos_server", "") or ""),
            namespace_id=str(getattr(self.config, "nacos_namespace_id", "") or "public"),
            access_token=str(getattr(self.config, "nacos_access_token", "") or ""),
            username=str(getattr(self.config, "nacos_username", "") or ""),
            password=str(getattr(self.config, "nacos_password", "") or ""),
        )

    def _load_remote_skills(self) -> dict[str, dict[str, Any]]:
        if self._nacos_skill_client is not None:
            skills: dict[str, dict[str, Any]] = {}
            for item in self._nacos_skill_client.list_skills():
                name = str(item.get("name") or "")
                if name:
                    skills[name] = item
            return skills
        return super()._load_remote_skills()

    def _load_remote_skill_record(self, name: str) -> Optional[dict[str, Any]]:
        rec = self._load_remote_skills().get(name)
        return rec if isinstance(rec, dict) else None

    @staticmethod
    def _overlay_manifest_metadata(
        skill: Optional[dict[str, Any]],
        manifest_record: Optional[dict[str, Any]],
    ) -> Optional[dict[str, Any]]:
        if not skill or not manifest_record:
            return skill
        category = str(manifest_record.get("category", "") or "").strip()
        if category and str(skill.get("category", "general") or "general").strip() == "general":
            skill["category"] = category
        if not str(skill.get("description", "") or "").strip():
            description = str(manifest_record.get("description", "") or "").strip()
            if description:
                skill["description"] = description
        return skill

    def _wait_nacos_publish(self, name: str, version: str, timeout: float = 30.0) -> bool:
        """Publish a Nacos skill version and wait for it to go online.

        Nacos v3 runs a publish pipeline on submit. The pipeline must approve
        before the publish call succeeds. This method polls for approval and
        retries publish until the version goes online with the latest label.
        """
        import time

        deadline = time.monotonic() + timeout
        published = False
        while time.monotonic() < deadline:
            try:
                detail = self._nacos_skill_client.get_skill(name)
                labels = detail.get("labels", {}) if detail else {}
                if labels.get("latest") == version:
                    return True
                if not published:
                    try:
                        self._nacos_skill_client.publish(name, version, update_latest_label=True)
                        logger.info("[EvolveServer] Nacos publish accepted for %s %s", name, version)
                        published = True
                    except Exception:
                        pass
            except Exception:
                pass
            time.sleep(2.0)
        logger.warning("[EvolveServer] Nacos publish not confirmed for %s %s within %.0fs", name, version, timeout)
        return False

    def _fetch_skill(self, name: str) -> Optional[str]:
        if self._nacos_skill_client is not None:
            try:
                from skillclaw.nacos_skill_hub import (
                    _nacos_published_version,
                    _nacos_working_version,
                    _nacos_zip_to_bundle,
                )

                record = self._load_remote_skill_record(name) or {}
                try:
                    detail = self._nacos_skill_client.get_skill(name) if record else {}
                except Exception:
                    detail = {}
                working = _nacos_working_version(record, detail)
                if working:
                    _status, version = working
                    zip_bytes = self._nacos_skill_client.download_skill_zip(name, version=version, admin=True)
                else:
                    label = str(getattr(self.config, "nacos_label", "") or "latest")
                    version = _nacos_published_version(record, detail, label=label)
                    if not version:
                        logger.info(
                            "[EvolveServer] Nacos skill %s has no published %s version",
                            name,
                            label,
                        )
                        return None
                    zip_bytes = self._nacos_skill_client.download_skill_zip(
                        name,
                        version=version,
                        label=label,
                    )
                bundle = _nacos_zip_to_bundle(zip_bytes)
                data = bundle.get("SKILL.md")
                return data.decode("utf-8") if data is not None else None
            except Exception as exc:
                logger.warning("[EvolveServer] failed to fetch Nacos skill %s: %s", name, exc)
                return None
        return fetch_skill_content(self._bucket, self._prefix, name)

    def _upload_skill(self, skill: dict, action: str) -> str:
        name = skill.get("name", "")
        if not name:
            return "skipped_missing_name"

        if self._nacos_skill_client is not None:
            from skillclaw.nacos_skill_hub import (
                _bundle_matches_remote,
                _bundle_to_nacos_zip,
                _nacos_working_version,
                _nacos_zip_to_bundle,
                _next_version,
            )

            md_content = build_skill_md(skill)
            md_bytes = md_content.encode("utf-8")
            bundle_files = {"SKILL.md": md_bytes}
            record = self._load_remote_skill_record(name) or {}
            try:
                detail = self._nacos_skill_client.get_skill(name) if record else {}
            except Exception:
                detail = {}
            working = _nacos_working_version(record, detail)
            if working:
                status, version = working
                try:
                    zip_bytes = self._nacos_skill_client.download_skill_zip(name, version=version, admin=True)
                    remote_bundle = _nacos_zip_to_bundle(zip_bytes)
                except Exception as exc:
                    logger.warning(
                        "[EvolveServer] skipping Nacos skill %s: failed to inspect %s version %s: %s",
                        name,
                        status,
                        version,
                        exc,
                    )
                    return f"skipped_existing_{status}"
                if _bundle_matches_remote(bundle_files, remote_bundle):
                    logger.info(
                        "[EvolveServer] skipped Nacos skill %s: %s version %s already matches",
                        name,
                        status,
                        version,
                    )
                    return f"skipped_existing_{status}"
                logger.info(
                    "[EvolveServer] skipped Nacos skill %s: %s version %s already exists",
                    name,
                    status,
                    version,
                )
                return f"skipped_existing_{status}"
            target_version = _next_version(record, detail)
            zip_bytes = _bundle_to_nacos_zip(name, bundle_files)
            self._nacos_skill_client.upload_skill_zip(
                zip_bytes=zip_bytes,
                filename=f"{name}-{target_version}.zip",
                overwrite=True,
                target_version=target_version,
            )
            publish_mode = str(getattr(self.config, "nacos_publish_mode", "") or "review").strip().lower()
            if publish_mode in {"review", "direct"}:
                self._nacos_skill_client.submit(name, target_version)
            publish_confirmed = False
            if publish_mode == "direct":
                publish_confirmed = self._wait_nacos_publish(name, target_version)
            logger.info(
                "[EvolveServer] uploaded skill %s to Nacos as %s via action=%s publish_mode=%s",
                name,
                target_version,
                action,
                publish_mode,
            )
            if publish_mode == "draft":
                return "uploaded_draft"
            if publish_mode == "review":
                return "uploaded_pending_review"
            if not publish_confirmed:
                return "uploaded_pending_publish"
            return "uploaded"

        skill_id = self._id_registry.get_or_create(name)
        md_content = build_skill_md(skill)
        object_key = f"{self._prefix}skills/{name}/SKILL.md"
        md_bytes = md_content.encode("utf-8")
        self._bucket.put_object(object_key, md_bytes)

        content_sha = hashlib.sha256(md_bytes).hexdigest()
        tree_sha = bundle_tree_sha256({"SKILL.md": md_bytes})
        bundle_record = {
            "format": "bundle_v1",
            "entrypoint": "SKILL.md",
            "tree_sha256": tree_sha,
            "files": [{"path": "SKILL.md", "sha256": content_sha, "size": len(md_bytes)}],
        }
        version = self._id_registry.record_update(
            name,
            content_sha,
            action=action,
            bundle_record=bundle_record,
        )
        save_version_bundle(self._bucket, self._prefix, name, version, {"SKILL.md": md_bytes})

        manifest = self._load_remote_skills()
        manifest[name] = {
            "name": name,
            "skill_id": skill_id,
            "version": version,
            "sha256": content_sha,
            "tree_sha256": tree_sha,
            "format": "bundle_v1",
            "entrypoint": "SKILL.md",
            "files": bundle_record["files"],
            "uploaded_by": "evolve_server",
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
            "description": skill.get("description", ""),
            "category": skill.get("category", "general"),
        }
        save_manifest(self._bucket, self._prefix, manifest)
        logger.info(
            "[EvolveServer] uploaded skill %s (id=%s, v%d) to %s",
            name,
            skill_id,
            version,
            object_key,
        )
        return "uploaded"

    def _detect_conflict(self, name: str, incoming_skill: dict) -> bool:
        if self._nacos_skill_client is not None:
            existing_md = self._fetch_skill(name)
            if not existing_md:
                return False
            existing_sha = hashlib.sha256(existing_md.encode("utf-8")).hexdigest()
            incoming_md = build_skill_md(incoming_skill)
            incoming_sha = hashlib.sha256(incoming_md.encode("utf-8")).hexdigest()
            return existing_sha != incoming_sha
        existing_sha = self._id_registry.get_content_sha(name)
        if not existing_sha:
            return False
        incoming_md = build_skill_md(incoming_skill)
        incoming_sha = hashlib.sha256(incoming_md.encode("utf-8")).hexdigest()
        return existing_sha != incoming_sha

    async def _resolve_and_upload(self, skill: dict, action_type: str) -> tuple[str, bool]:
        name = skill.get("name", "")
        has_conflict = await self._call_storage(self._detect_conflict, name, skill)
        if not has_conflict:
            upload_status = await self._call_storage(self._upload_skill, skill, action_type)
            return self._upload_status_to_action(action_type, upload_status)

        logger.info("[EvolveServer] conflict detected for '%s' - merging", name)
        existing_md = await self._call_storage(self._fetch_skill, name)
        if not existing_md:
            upload_status = await self._call_storage(self._upload_skill, skill, action_type)
            return self._upload_status_to_action(action_type, upload_status)

        existing_skill = parse_skill_content(name, existing_md)
        existing_skill = self._overlay_manifest_metadata(
            existing_skill,
            self._load_remote_skill_record(name),
        )
        existing_skill["_version"] = self._id_registry.get_version(name)
        merged = await execute_merge(self._llm, existing_skill, skill)
        if merged and merged.get("name"):
            merged["name"] = name
            upload_status = await self._call_storage(self._upload_skill, merged, "merge")
            return self._upload_status_to_action("merge", upload_status)

        logger.warning("[EvolveServer] merge failed for '%s' - keeping incoming version", name)
        upload_status = await self._call_storage(self._upload_skill, skill, action_type)
        return self._upload_status_to_action(action_type, upload_status)

    @staticmethod
    def _upload_status_to_action(action_type: str, upload_status: str) -> tuple[str, bool]:
        if upload_status == "uploaded":
            return action_type, True
        if upload_status == "uploaded_pending_review":
            return f"{action_type}_pending_review", False
        if upload_status == "uploaded_pending_publish":
            return f"{action_type}_pending_publish", False
        if upload_status == "uploaded_draft":
            return f"{action_type}_draft", False
        return upload_status, False

    def _empty_judge_summary(self) -> dict[str, Any]:
        return {
            "enabled": bool(self.config.use_session_judge),
            "judged_sessions": 0,
            "scored_sessions": 0,
            "mean_score": None,
            "min_score": None,
            "max_score": None,
        }

    async def _run_session_judge(self, sessions: list[dict]) -> dict[str, Any]:
        summary = self._empty_judge_summary()
        if not self.config.use_session_judge or not sessions:
            return summary

        judged = await judge_sessions_parallel(self._llm, sessions)
        scores = [
            float(judge_scores["overall_score"])
            for session in sessions
            for judge_scores in [session.get("_judge_scores")]
            if isinstance(judge_scores, dict) and isinstance(judge_scores.get("overall_score"), (int, float))
        ]
        summary["judged_sessions"] = judged
        summary["scored_sessions"] = len(scores)
        if scores:
            summary["mean_score"] = round(sum(scores) / len(scores), 3)
            summary["min_score"] = round(min(scores), 3)
            summary["max_score"] = round(max(scores), 3)
        logger.info("[EvolveServer] judged %d sessions without benchmark scores", judged)
        return summary

    def _empty_skill_verifier_summary(self) -> dict[str, Any]:
        return {
            "enabled": bool(self.config.use_skill_verifier),
            "verified_skills": 0,
            "accepted": 0,
            "rejected": 0,
            "mean_score": None,
            "min_score": None,
            "max_score": None,
        }

    def _collect_skill_verifier_summary(self, records: list[dict[str, Any]]) -> dict[str, Any]:
        summary = self._empty_skill_verifier_summary()
        if not self.config.use_skill_verifier:
            return summary

        scores: list[float] = []
        for record in records:
            verification = record.get("verification")
            if not isinstance(verification, dict) or not verification.get("enabled"):
                continue
            summary["verified_skills"] += 1
            if verification.get("accepted"):
                summary["accepted"] += 1
            else:
                summary["rejected"] += 1
            score = verification.get("score")
            if isinstance(score, (int, float)) and not isinstance(score, bool):
                scores.append(float(score))

        if scores:
            summary["mean_score"] = round(sum(scores) / len(scores), 3)
            summary["min_score"] = round(min(scores), 3)
            summary["max_score"] = round(max(scores), 3)
        return summary

    def _empty_validation_publish_summary(self) -> dict[str, Any]:
        return {
            "publish_mode": self.config.publish_mode,
            "jobs_scanned": 0,
            "pending": 0,
            "published": 0,
            "rejected": 0,
            "skipped": 0,
        }

    def _build_validation_evidence(self, sessions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        evidence: list[dict[str, Any]] = []
        for session in sessions[:8]:
            item: dict[str, Any] = {
                "session_id": str(session.get("session_id", "")),
                "summary": str(session.get("_summary", "")),
            }
            skills = session.get("_skills_referenced")
            if skills:
                item["skills_referenced"] = sorted(str(s or "") for s in skills if str(s or ""))
            judge_scores = session.get("_judge_scores")
            if isinstance(judge_scores, dict) and isinstance(judge_scores.get("overall_score"), (int, float)):
                item["judge_overall_score"] = float(judge_scores["overall_score"])
            if isinstance(session.get("_avg_prm"), (int, float)):
                item["avg_prm"] = float(session["_avg_prm"])
            evidence.append(item)
        return evidence

    def _build_replay_cases(self, sessions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        preferred: list[dict[str, Any]] = []
        fallback: list[dict[str, Any]] = []

        for session in sessions[:6]:
            session_id = str(session.get("session_id", "") or "")
            turns = session.get("turns") or []
            if not isinstance(turns, list):
                continue
            for turn in turns:
                if not isinstance(turn, dict):
                    continue
                instruction = str(turn.get("prompt_text", "") or "").strip()
                reference_response = str(turn.get("response_text", "") or "").strip()
                if not instruction or not reference_response:
                    continue
                case = {
                    "session_id": session_id,
                    "turn_num": int(turn.get("turn_num", 0) or 0),
                    "instruction": instruction[:3000],
                    "reference_response": reference_response[:4000],
                    "had_tool_calls": bool(turn.get("tool_calls")),
                    "had_tool_results": bool(turn.get("tool_results") or turn.get("tool_observations")),
                }
                if not case["had_tool_calls"] and not case["had_tool_results"]:
                    preferred.append(case)
                else:
                    fallback.append(case)
                if len(preferred) >= 3:
                    return preferred[:3]

        if preferred:
            return preferred[:3]
        return fallback[:3]

    def _queue_validation_job(
        self,
        skill: dict[str, Any],
        action_type: str,
        sessions: list[dict[str, Any]],
        rationale: str,
        source: str,
        *,
        current_skill: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        name = str(skill.get("name", "") or "")
        skill_id = self._id_registry.get_or_create(name)
        job_id = self._validation_store.make_job_id(name)
        job = {
            "job_id": job_id,
            "status": "pending_validation",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "candidate_skill_name": name,
            "candidate_skill_id": skill_id,
            "candidate_skill": skill,
            "current_skill": current_skill,
            "proposed_action": action_type,
            "source": source,
            "rationale": rationale,
            "session_ids": [session.get("session_id", "") for session in sessions],
            "session_evidence": self._build_validation_evidence(sessions),
            "replay_cases": self._build_replay_cases(sessions),
            "min_results": self.config.validation_required_results,
            "min_approvals": self.config.validation_required_approvals,
            "min_score": self.config.validation_min_mean_score,
            "max_rejections": self.config.validation_max_rejections,
        }
        self._validation_store.save_job(job)
        logger.info(
            "[EvolveServer] queued validation job %s for skill '%s' (publish_mode=validated)",
            job_id,
            name,
        )
        return {
            "action": "queued_for_validation",
            "proposed_action": action_type,
            "skill_name": name,
            "skill_id": skill_id,
            "version": None,
            "session_ids": job["session_ids"],
            "rationale": rationale,
            "source": source,
            "edit_summary": skill.get("edit_summary"),
            "uploaded": False,
            "validation_job_id": job_id,
        }

    async def _finalize_validation_jobs(self) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        summary = self._empty_validation_publish_summary()
        if self.config.publish_mode != "validated":
            return [], summary

        records: list[dict[str, Any]] = []
        for job in self._validation_store.list_jobs():
            summary["jobs_scanned"] += 1
            job_id = str(job.get("job_id", "") or "")
            if not job_id:
                continue
            if self._validation_store.load_decision(job_id):
                continue

            results = self._validation_store.list_results(job_id)
            if not results:
                summary["pending"] += 1
                continue

            accepted = 0
            rejected = 0
            scores: list[float] = []
            for result in results:
                if result.get("accepted") is True:
                    accepted += 1
                else:
                    rejected += 1
                score = result.get("score")
                if isinstance(score, (int, float)) and not isinstance(score, bool):
                    scores.append(float(score))

            mean_score = round(sum(scores) / len(scores), 3) if scores else None
            publish_ready = (
                len(results) >= self.config.validation_required_results
                and accepted >= self.config.validation_required_approvals
                and mean_score is not None
                and mean_score >= self.config.validation_min_mean_score
            )
            reject_ready = rejected >= self.config.validation_max_rejections

            if publish_ready:
                candidate_skill = job.get("candidate_skill")
                if not isinstance(candidate_skill, dict) or not candidate_skill.get("name"):
                    self._validation_store.save_decision(
                        job_id,
                        {
                            "status": "rejected",
                            "reason": "candidate skill payload missing",
                            "result_count": len(results),
                            "accepted_count": accepted,
                            "rejected_count": rejected,
                            "mean_score": mean_score,
                        },
                    )
                    summary["rejected"] += 1
                    continue
                action_type = str(job.get("proposed_action", DecisionAction.CREATE) or DecisionAction.CREATE)
                actual_action, uploaded = await self._resolve_and_upload(candidate_skill, action_type)
                self._validation_store.save_decision(
                    job_id,
                    {
                        "status": "published" if uploaded else "skipped",
                        "published_action": actual_action,
                        "result_count": len(results),
                        "accepted_count": accepted,
                        "rejected_count": rejected,
                        "mean_score": mean_score,
                    },
                )
                if uploaded:
                    summary["published"] += 1
                else:
                    summary["skipped"] += 1
                records.append(
                    {
                        "action": "published_after_validation" if uploaded else actual_action,
                        "published_action": actual_action,
                        "skill_name": str(candidate_skill.get("name", "")),
                        "skill_id": self._id_registry.get_or_create(str(candidate_skill.get("name", ""))),
                        "version": self._id_registry.get_version(str(candidate_skill.get("name", ""))),
                        "session_ids": list(job.get("session_ids") or []),
                        "rationale": str(job.get("rationale", "") or ""),
                        "source": "validation_publish",
                        "uploaded": uploaded,
                        "validation_job_id": job_id,
                        "validation_results": {
                            "result_count": len(results),
                            "accepted_count": accepted,
                            "rejected_count": rejected,
                            "mean_score": mean_score,
                        },
                    }
                )
                continue

            if reject_ready:
                self._validation_store.save_decision(
                    job_id,
                    {
                        "status": "rejected",
                        "reason": "client validation rejected candidate",
                        "result_count": len(results),
                        "accepted_count": accepted,
                        "rejected_count": rejected,
                        "mean_score": mean_score,
                    },
                )
                summary["rejected"] += 1
                records.append(
                    {
                        "action": "validation_rejected",
                        "proposed_action": str(job.get("proposed_action", "")),
                        "skill_name": str(job.get("candidate_skill_name", "")),
                        "skill_id": str(job.get("candidate_skill_id", "")),
                        "version": None,
                        "session_ids": list(job.get("session_ids") or []),
                        "rationale": str(job.get("rationale", "") or ""),
                        "source": "validation_publish",
                        "uploaded": False,
                        "validation_job_id": job_id,
                        "validation_results": {
                            "result_count": len(results),
                            "accepted_count": accepted,
                            "rejected_count": rejected,
                            "mean_score": mean_score,
                        },
                    }
                )
                continue

            summary["pending"] += 1

        return records, summary

    async def _run_skill_verifier(
        self,
        skill: dict[str, Any],
        action_type: str,
        sessions: list[dict[str, Any]],
        *,
        current_skill: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        if not self.config.use_skill_verifier:
            return {"enabled": False}
        return await verify_skill_candidate(
            self._llm,
            skill,
            sessions,
            action_type,
            current_skill=current_skill,
            min_score=self.config.skill_verifier_min_score,
        )

    def _inherit_current_skill(
        self,
        evolved_skill: Optional[dict[str, Any]],
        current_skill: Optional[dict[str, Any]],
        *,
        overwrite_body: bool = False,
    ) -> None:
        if not evolved_skill or not current_skill:
            return
        if overwrite_body:
            evolved_skill["content"] = current_skill.get("content", "")
            evolved_skill["category"] = current_skill.get("category", "general")
        else:
            evolved_skill.setdefault("content", current_skill.get("content", ""))
            evolved_skill.setdefault("category", current_skill.get("category", "general"))
        evolved_skill.setdefault("extra_frontmatter", current_skill.get("extra_frontmatter") or {})

    async def _materialize_skill(
        self,
        evolved_skill: Optional[dict],
        action_type: str,
        sessions: list[dict[str, Any]],
        rationale: str,
        source: str,
        *,
        current_skill: Optional[dict[str, Any]] = None,
    ) -> Optional[dict]:
        if not evolved_skill or not evolved_skill.get("name"):
            return None

        if action_type == DecisionAction.IMPROVE and current_skill and current_skill.get("name"):
            name = current_skill["name"]
        else:
            name = self._sanitise_name(evolved_skill["name"])
        evolved_skill["name"] = name

        verification = await self._run_skill_verifier(
            evolved_skill,
            action_type,
            sessions,
            current_skill=current_skill,
        )
        session_ids = [session.get("session_id", "") for session in sessions]
        if verification.get("enabled") and not verification.get("accepted"):
            logger.info(
                "[EvolveServer] verifier rejected skill '%s': %s",
                name,
                verification.get("reason", "no reason provided"),
            )
            return {
                "action": "verification_rejected",
                "proposed_action": action_type,
                "skill_name": name,
                "skill_id": None,
                "version": None,
                "session_ids": session_ids,
                "rationale": rationale,
                "source": source,
                "edit_summary": evolved_skill.get("edit_summary"),
                "uploaded": False,
                "verification": verification,
            }

        skill_id = self._id_registry.get_or_create(name)
        evolved_skill["skill_id"] = skill_id
        if self.config.publish_mode == "validated":
            record = self._queue_validation_job(
                evolved_skill,
                action_type,
                sessions,
                rationale,
                source,
                current_skill=current_skill,
            )
            record["verification"] = verification
            return record

        actual_action, uploaded = await self._resolve_and_upload(evolved_skill, action_type)
        logger.info(
            "[EvolveServer] %s skill '%s' (id=%s, v%d)",
            actual_action,
            name,
            skill_id,
            self._id_registry.get_version(name),
        )
        return {
            "action": actual_action,
            "skill_name": name,
            "skill_id": skill_id,
            "version": self._id_registry.get_version(name),
            "session_ids": session_ids,
            "rationale": rationale,
            "source": source,
            "edit_summary": evolved_skill.get("edit_summary"),
            "uploaded": uploaded,
            "verification": verification,
        }

    async def _evolve_skill_group(
        self,
        skill_name: str,
        sessions: list[dict],
        existing_skill_names: list[str],
        *,
        feedback_context: Optional[dict[str, Any]] = None,
    ) -> Optional[dict]:
        current_md = await self._call_storage(self._fetch_skill, skill_name)
        current_skill = parse_skill_content(skill_name, current_md) if current_md else None
        current_skill = self._overlay_manifest_metadata(
            current_skill,
            await self._call_storage(self._load_remote_skill_record, skill_name),
        )

        result = await evolve_skill_from_sessions(
            self._llm,
            skill_name,
            sessions,
            current_skill,
            existing_skill_names,
            feedback_context=feedback_context,
        )
        if not result or result.get("action") == DecisionAction.SKIP:
            logger.info("[EvolveServer] skill '%s': LLM decided to skip", skill_name)
            return None

        action_type = result.get("action", DecisionAction.IMPROVE)
        evolved_skill = result.get("skill")
        if not evolved_skill:
            return None

        if action_type == DecisionAction.OPTIMIZE_DESC and current_skill:
            self._inherit_current_skill(evolved_skill, current_skill, overwrite_body=True)
        elif current_skill:
            self._inherit_current_skill(evolved_skill, current_skill)

        return await self._materialize_skill(
            evolved_skill,
            action_type,
            sessions,
            result.get("rationale", ""),
            "skill_group",
            current_skill=current_skill,
        )

    async def _handle_no_skill_sessions(
        self,
        sessions: list[dict],
        existing_skill_names: list[str],
    ) -> list[dict]:
        result = await create_skill_from_sessions(self._llm, sessions, existing_skill_names)
        if not result or result.get("action") == DecisionAction.SKIP:
            logger.info("[EvolveServer] no-skill sessions: LLM decided to skip")
            return []

        evolved_skill = result.get("skill")
        if not evolved_skill:
            return []

        record = await self._materialize_skill(
            evolved_skill,
            DecisionAction.CREATE,
            sessions,
            result.get("rationale", ""),
            "no_skill",
        )
        return [record] if record else []

    async def run_once(self) -> dict:
        logger.info("[EvolveServer] === starting evolution cycle ===")
        started_at = time.monotonic()

        feedback_keys: list[str] = []
        manifest = await self._call_storage(self._load_remote_skills)
        self._id_registry.prune_unpublished_placeholders(set(manifest))
        queue_status = {
            "ready_pairs": 0,
            "active_sessions": 0,
            "closed_sessions_waiting_feedback": 0,
            "feedback_waiting_session": 0,
        }
        if self.config.publish_mode == "validated":
            sessions, session_keys, feedback_keys, queue_status = await self._load_validated_pairs()
        else:
            sessions, session_keys = await self._drain_sessions()
        judge_summary = self._empty_judge_summary()
        skill_group_count = 0
        no_skill_sessions: list[dict] = []
        evolution_records: list[dict] = []
        had_processing_error = False
        if self.config.publish_mode == "validated":
            feedback_bundle = None
            feedback_by_skill = self._paired_feedback_map(sessions)
        else:
            feedback_bundle = self._load_feedback_bundle()
            feedback_by_skill = self._feedback_map(feedback_bundle)

        if sessions:
            logger.info("[EvolveServer] summarizing %d sessions", len(sessions))
            await summarize_sessions_parallel(self._llm, sessions)
            judge_summary = await self._run_session_judge(sessions)

            grouped_sessions = aggregate_sessions_by_skill(sessions)
            no_skill_sessions = grouped_sessions.pop(NO_SKILL_KEY, [])
            skill_group_count = len(grouped_sessions)

            existing_skill_names = [item.get("name", "") for item in manifest.values()]

            if grouped_sessions:
                logger.info("[EvolveServer] evolving %d skill group(s)", skill_group_count)
            for skill_name, skill_sessions in grouped_sessions.items():
                try:
                    record = await self._evolve_skill_group(
                        skill_name,
                        skill_sessions,
                        existing_skill_names,
                        feedback_context=feedback_by_skill.get(skill_name),
                    )
                except Exception as exc:
                    logger.error("[EvolveServer] skill '%s' evolve failed: %s", skill_name, exc)
                    had_processing_error = True
                    continue
                if record:
                    if feedback_by_skill.get(skill_name):
                        record["feedback_context"] = {
                            "skill": feedback_by_skill[skill_name].get("skill"),
                            "gate_decision": feedback_by_skill[skill_name].get("gate_decision"),
                            "revision_directives": list(feedback_by_skill[skill_name].get("revision_directives") or []),
                        }
                    evolution_records.append(record)

            if no_skill_sessions:
                logger.info("[EvolveServer] processing %d no-skill sessions", len(no_skill_sessions))
                try:
                    evolution_records.extend(
                        await self._handle_no_skill_sessions(no_skill_sessions, existing_skill_names)
                    )
                except Exception as exc:
                    logger.error("[EvolveServer] no-skill evolve failed: %s", exc)
                    had_processing_error = True
        else:
            logger.info("[EvolveServer] queue empty - checking pending validation publish jobs")

        published_records, validation_publish_summary = await self._finalize_validation_jobs()
        all_records = evolution_records + published_records

        if not self._uses_nacos_skill_registry():
            await self._call_storage(self._id_registry.save_to_oss, self._bucket, self._prefix)
        if session_keys and not had_processing_error:
            await self._write_consumption_receipts(sessions, all_records)
            await self._call_storage(delete_session_keys, self._bucket, session_keys)
            if feedback_keys:
                await self._call_storage(delete_object_keys, self._bucket, feedback_keys)
        elif session_keys and had_processing_error:
            logger.warning(
                "[EvolveServer] retaining %d session(s) in queue because this cycle had processing errors",
                len(session_keys),
            )

        elapsed = round(time.monotonic() - started_at, 1)
        uploaded_skills = sum(1 for record in all_records if record.get("uploaded"))
        queued_candidates = sum(1 for record in all_records if record.get("action") == "queued_for_validation")
        published_after_validation = sum(
            1 for record in all_records if record.get("action") == "published_after_validation"
        )
        skill_verifier_summary = self._collect_skill_verifier_summary(all_records)
        summary = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": elapsed,
            "sessions": len(sessions),
            "skill_groups": skill_group_count,
            "no_skill_sessions": len(no_skill_sessions),
            "actions": len(all_records),
            "skills_evolved": uploaded_skills,
            "uploaded_skills": uploaded_skills,
            "candidates_queued": queued_candidates,
            "published_after_validation": published_after_validation,
            "evolutions": all_records,
            "session_judge": judge_summary,
            "skill_verifier": skill_verifier_summary,
            "validation_publish": validation_publish_summary,
            "feedback_bundle_loaded": bool(feedback_by_skill),
            "feedback_bundle_skill_count": len(feedback_by_skill),
            "validated_pair_queue": queue_status,
            "had_processing_error": had_processing_error,
        }
        self._append_history(summary)
        logger.info(
            "[EvolveServer] === cycle done: %d sessions, %d skill groups, %d uploaded, %d queued in %.1fs ===",
            len(sessions),
            skill_group_count,
            uploaded_skills,
            queued_candidates,
            elapsed,
        )
        if uploaded_skills > 0:
            await self._notify_proxy_reload()
        return summary

    async def _notify_proxy_reload(self) -> None:
        mode = str(getattr(self.config, "skill_reload_mode", "") or "poll").strip().lower()
        url = str(getattr(self.config, "proxy_reload_url", "") or "").strip().rstrip("/")
        if mode != "callback" or not url:
            return
        headers: dict[str, str] = {}
        api_key = str(getattr(self.config, "proxy_reload_api_key", "") or "")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        import httpx

        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.post(f"{url}/internal/reload-skills", headers=headers)
                    resp.raise_for_status()
                logger.info("[EvolveServer] notified proxy to reload skills: %s", url)
                return
            except Exception as exc:
                if attempt < 2:
                    await asyncio.sleep(1.0 * (attempt + 1))
                else:
                    logger.warning("[EvolveServer] proxy reload notify failed after 3 attempts: %s", exc)

    async def run_periodic(self) -> None:
        self._running = True
        logger.info("[EvolveServer] periodic mode: interval=%ds", self.config.interval_seconds)
        while self._running:
            try:
                await self.run_once()
            except Exception as exc:
                logger.error("[EvolveServer] cycle error: %s", exc, exc_info=True)
            await asyncio.sleep(self.config.interval_seconds)

    def stop(self) -> None:
        self._running = False

    def create_http_app(self):
        from fastapi.responses import JSONResponse

        app = FastAPI(title="SkillClaw Evolve Server")

        @app.post("/trigger")
        async def trigger_evolve():
            return JSONResponse(content=await self.run_once())

        @app.post("/v1/run-feedback")
        async def submit_run_feedback(request: Request):
            payload = await request.json()
            if not isinstance(payload, dict):
                raise HTTPException(status_code=400, detail="feedback payload must be a JSON object")
            segment_id = str(payload.get("session_segment_id") or "").strip()
            run_id = str(payload.get("run_id") or "").strip()
            client_session_id = str(payload.get("client_session_id") or "").strip()
            skill_feedback = payload.get("skill_feedback")
            try:
                uuid.UUID(segment_id)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail="session_segment_id must be a UUID") from exc
            if not run_id or not client_session_id:
                raise HTTPException(status_code=400, detail="run_id and client_session_id are required")
            if not isinstance(skill_feedback, list):
                raise HTTPException(status_code=400, detail="skill_feedback must be a list")
            run_key = hashlib.sha256(run_id.encode("utf-8")).hexdigest()[:20]
            key = f"{self._prefix}run_feedback/{segment_id}/{run_key}.json"
            await self._call_storage(write_json_object, self._bucket, key, payload)
            return JSONResponse(
                content={
                    "queued": True,
                    "run_id": run_id,
                    "client_session_id": client_session_id,
                    "session_segment_id": segment_id,
                    "storage_key": key,
                }
            )

        @app.get("/v1/run-feedback/status")
        async def run_feedback_status(run_id: str, session_segment_id: str):
            if not run_id or not session_segment_id:
                raise HTTPException(status_code=400, detail="run_id and session_segment_id are required")
            receipt = await self._call_storage(
                read_json_object,
                self._bucket,
                self._run_receipt_key(session_segment_id, run_id),
                False,
            )
            if not isinstance(receipt, dict):
                return JSONResponse(
                    content={
                        "status": "pending",
                        "run_id": run_id,
                        "session_segment_id": session_segment_id,
                    }
                )
            return JSONResponse(content=receipt)

        @app.get("/status")
        async def status():
            published_entries = self._load_remote_skills()
            registry_entries = self._id_registry.all_entries()
            pending_keys = await self._call_storage(list_session_keys, self._bucket, self._prefix)
            feedback_keys = await self._call_storage(list_run_feedback_keys, self._bucket, self._prefix)
            pair_status = None
            if self.config.publish_mode == "validated":
                _, _, _, pair_status = await self._load_validated_pairs()
            return JSONResponse(
                content={
                    "engine": "workflow",
                    "running": self._running,
                    "publish_mode": self.config.publish_mode,
                    "feedback_bundle_path": self.config.feedback_bundle_path,
                    "pending_sessions": len(pending_keys),
                    "pending_run_feedback": len(feedback_keys),
                    "validated_pair_queue": pair_status,
                    "validation_policy": {
                        "required_results": self.config.validation_required_results,
                        "required_approvals": self.config.validation_required_approvals,
                        "min_mean_score": self.config.validation_min_mean_score,
                        "max_rejections": self.config.validation_max_rejections,
                    },
                    "published_skills": len(published_entries),
                    "registered_skills": len(registry_entries),
                    "stale_registry_entries": max(0, len(registry_entries) - len(published_entries)),
                    "skills": {
                        name: {
                            "skill_id": item.get("skill_id") or item.get("name") or name,
                            "version": item.get("version") or (item.get("labels") or {}).get("latest") or 0,
                        }
                        for name, item in published_entries.items()
                    },
                }
            )

        @app.get("/health")
        async def health():
            return {"status": "ok"}

        return app
