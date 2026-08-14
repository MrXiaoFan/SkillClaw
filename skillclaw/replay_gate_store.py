"""
Shared storage helpers for distributed client-side replay gate review.

The replay gate uses the same object store boundary as the rest of
SkillClaw. Jobs are produced by the evolve server, reviewed by opted-in
clients, and later finalized by the evolve server.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from .object_store import build_object_store, is_not_found_error
from .skill_markdown import build_skill_md

logger = logging.getLogger(__name__)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ReplayGateStore:
    """Persist replay gate jobs/results/decisions in shared storage."""

    def __init__(
        self,
        *,
        backend: str,
        endpoint: str,
        bucket: str,
        access_key_id: str,
        secret_access_key: str,
        region: str = "",
        session_token: str = "",
        local_root: str = "",
        group_id: str = "default",
    ) -> None:
        self._bucket = build_object_store(
            backend=backend,
            endpoint=endpoint,
            bucket=bucket,
            access_key_id=access_key_id,
            secret_access_key=secret_access_key,
            region=region,
            session_token=session_token,
            local_root=local_root,
        )
        self._group_id = group_id

    @classmethod
    def from_config(cls, config) -> "ReplayGateStore":
        from .skill_hub import SkillHub

        hub = SkillHub.object_storage_from_config(config)
        if hub is None:
            raise ValueError("replay gate storage requires local/OSS/S3; Nacos stores skills only")
        store = cls.__new__(cls)
        store._bucket = hub._bucket
        store._group_id = str(getattr(config, "sharing_group_id", "default") or "default")
        return store

    def _prefix(self) -> str:
        return f"{self._group_id}/"

    def _job_key(self, job_id: str) -> str:
        return f"{self._prefix()}gate_jobs/{job_id}.json"

    def _legacy_job_key(self, job_id: str) -> str:
        return f"{self._prefix()}validation_jobs/{job_id}.json"

    def _candidate_skill_key(self, job_id: str) -> str:
        return f"{self._prefix()}candidate_skills/{job_id}/SKILL.md"

    def _result_key(self, job_id: str, user_alias: str) -> str:
        return f"{self._prefix()}gate_results/{job_id}/{user_alias}.json"

    def _legacy_result_key(self, job_id: str, user_alias: str) -> str:
        return f"{self._prefix()}validation_results/{job_id}/{user_alias}.json"

    def _decision_key(self, job_id: str) -> str:
        return f"{self._prefix()}gate_decisions/{job_id}.json"

    def _legacy_decision_key(self, job_id: str) -> str:
        return f"{self._prefix()}validation_decisions/{job_id}.json"

    def make_job_id(self, skill_name: str) -> str:
        slug = str(skill_name or "candidate").strip().lower().replace("_", "-")
        slug = "".join(ch if ch.isalnum() or ch == "-" else "-" for ch in slug).strip("-") or "candidate"
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"{timestamp}-{slug}-{uuid.uuid4().hex[:8]}"

    def save_job(self, job: dict[str, Any]) -> None:
        job_id = str(job.get("job_id", "") or "")
        if not job_id:
            raise ValueError("replay gate job requires job_id")
        payload = dict(job)
        payload.setdefault("created_at", _utc_now_iso())
        self._bucket.put_object(
            self._job_key(job_id),
            json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"),
        )
        candidate_skill = payload.get("candidate_skill")
        if isinstance(candidate_skill, dict) and candidate_skill.get("name"):
            self._bucket.put_object(
                self._candidate_skill_key(job_id),
                build_skill_md(candidate_skill).encode("utf-8"),
            )

    def load_job(self, job_id: str) -> Optional[dict[str, Any]]:
        for key in (self._job_key(job_id), self._legacy_job_key(job_id)):
            try:
                return json.loads(self._bucket.get_object(key).read().decode("utf-8"))
            except Exception as exc:
                if is_not_found_error(exc):
                    continue
                logger.warning("[ReplayGateStore] failed to load job %s: %s", job_id, exc)
                return None
        return None

    def list_jobs(self) -> list[dict[str, Any]]:
        jobs_by_id: dict[str, dict[str, Any]] = {}
        for prefix in (f"{self._prefix()}gate_jobs/", f"{self._prefix()}validation_jobs/"):
            for obj in self._bucket.iter_objects(prefix=prefix):
                if not obj.key.endswith(".json"):
                    continue
                try:
                    payload = json.loads(self._bucket.get_object(obj.key).read().decode("utf-8"))
                except Exception as exc:
                    logger.warning("[ReplayGateStore] failed to parse %s: %s", obj.key, exc)
                    continue
                if not isinstance(payload, dict):
                    continue
                job_id = str(payload.get("job_id", "") or "")
                if not job_id:
                    continue
                jobs_by_id[job_id] = payload
        jobs = list(jobs_by_id.values())
        jobs.sort(key=lambda item: str(item.get("created_at", "")))
        return jobs

    def save_result(self, job_id: str, user_alias: str, result: dict[str, Any]) -> None:
        payload = dict(result)
        payload["job_id"] = job_id
        payload["user_alias"] = user_alias
        payload.setdefault("created_at", _utc_now_iso())
        self._bucket.put_object(
            self._result_key(job_id, user_alias),
            json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"),
        )

    def load_result(self, job_id: str, user_alias: str) -> Optional[dict[str, Any]]:
        for key in (
            self._result_key(job_id, user_alias),
            self._legacy_result_key(job_id, user_alias),
        ):
            try:
                return json.loads(self._bucket.get_object(key).read().decode("utf-8"))
            except Exception as exc:
                if is_not_found_error(exc):
                    continue
                logger.warning(
                    "[ReplayGateStore] failed to load result for %s/%s: %s",
                    job_id,
                    user_alias,
                    exc,
                )
                return None
        return None

    def list_results(self, job_id: str) -> list[dict[str, Any]]:
        results_by_user: dict[str, dict[str, Any]] = {}
        for prefix in (
            f"{self._prefix()}gate_results/{job_id}/",
            f"{self._prefix()}validation_results/{job_id}/",
        ):
            for obj in self._bucket.iter_objects(prefix=prefix):
                if not obj.key.endswith(".json"):
                    continue
                try:
                    payload = json.loads(self._bucket.get_object(obj.key).read().decode("utf-8"))
                except Exception as exc:
                    logger.warning("[ReplayGateStore] failed to parse %s: %s", obj.key, exc)
                    continue
                if not isinstance(payload, dict):
                    continue
                user_alias = str(payload.get("user_alias", "") or "")
                if not user_alias:
                    continue
                results_by_user[user_alias] = payload
        results = list(results_by_user.values())
        results.sort(key=lambda item: (str(item.get("created_at", "")), str(item.get("user_alias", ""))))
        return results

    def save_decision(self, job_id: str, decision: dict[str, Any]) -> None:
        payload = dict(decision)
        payload["job_id"] = job_id
        payload.setdefault("decided_at", _utc_now_iso())
        self._bucket.put_object(
            self._decision_key(job_id),
            json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"),
        )

    def load_decision(self, job_id: str) -> Optional[dict[str, Any]]:
        for key in (self._decision_key(job_id), self._legacy_decision_key(job_id)):
            try:
                return json.loads(self._bucket.get_object(key).read().decode("utf-8"))
            except Exception as exc:
                if is_not_found_error(exc):
                    continue
                logger.warning("[ReplayGateStore] failed to load decision %s: %s", job_id, exc)
                return None
        return None

    def list_open_jobs(self, *, user_alias: str = "") -> list[dict[str, Any]]:
        jobs: list[dict[str, Any]] = []
        for job in self.list_jobs():
            job_id = str(job.get("job_id", "") or "")
            if not job_id:
                continue
            if self.load_decision(job_id):
                continue
            if user_alias and self.load_result(job_id, user_alias):
                continue
            jobs.append(job)
        return jobs


ValidationStore = ReplayGateStore
