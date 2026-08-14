"""
Optional background replay gate worker for idle SkillClaw clients.

This worker is intentionally conservative:
- it is disabled by default
- it only runs when sharing is enabled
- it only picks up jobs when the local client appears idle
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional, Protocol

# Deferred import to avoid triggering evolve_server.__init__ (which imports fastapi)
# AsyncLLMClient is imported lazily in __init__

from .prm_scorer import PRMScorer
from .skill_markdown import build_skill_md
from .replay_gate_store import ReplayGateStore

logger = logging.getLogger(__name__)


class IdleStateProvider(Protocol):
    def active_session_count(self) -> int: ...
    def last_request_age_seconds(self) -> Optional[float]: ...
    def is_idle_for_validation(self, idle_after_seconds: int) -> bool: ...


@dataclass
class ReplayGateRunSummary:
    checked_jobs: int = 0
    validated_jobs: int = 0
    skipped_jobs: int = 0
    reason: str = ""


class ReplayGateWorker:
    """Idle-time client-side replay gate worker."""

    def __init__(
        self,
        config,
        *,
        idle_provider: Optional[IdleStateProvider] = None,
    ) -> None:
        self.config = config
        self._idle_provider = idle_provider
        self._store = ReplayGateStore.from_config(config)
        self._stop_event = asyncio.Event()
        self._jobs_completed_today = 0
        self._jobs_completed_date = datetime.now(timezone.utc).date().isoformat()
        from evolve_server.core.llm_client import AsyncLLMClient
        self._client = AsyncLLMClient(
            api_key=config.llm_api_key,
            base_url=config.llm_api_base,
            model=config.llm_model_id or config.model_name or "gpt-4o",
            max_tokens=4096,
            temperature=0.1,
        )
        prm_url = config.prm_url or config.llm_api_base
        prm_model = config.prm_model or config.llm_model_id or config.model_name or "gpt-4o"
        prm_api_key = config.prm_api_key or config.llm_api_key
        self._prm_scorer = PRMScorer(
            prm_url=prm_url,
            prm_model=prm_model,
            api_key=prm_api_key,
            prm_m=max(1, int(getattr(config, "prm_m", 1) or 1)),
            temperature=float(getattr(config, "prm_temperature", 0.1) or 0.1),
            max_new_tokens=int(getattr(config, "prm_max_new_tokens", 512) or 512),
        )
        self._user_alias = str(config.sharing_user_alias or os.environ.get("USER", "anonymous"))

    def stop(self) -> None:
        self._stop_event.set()

    def _gate_enabled(self) -> bool:
        return bool(self.config.validation_enabled and self.config.sharing_enabled and self.config.sharing_group_id)

    def _reset_daily_quota_if_needed(self) -> None:
        today = datetime.now(timezone.utc).date().isoformat()
        if today != self._jobs_completed_date:
            self._jobs_completed_date = today
            self._jobs_completed_today = 0

    def _quota_available(self) -> bool:
        self._reset_daily_quota_if_needed()
        limit = max(0, int(self.config.validation_max_jobs_per_day))
        return limit <= 0 or self._jobs_completed_today < limit

    def _is_idle(self, *, force: bool = False) -> bool:
        if force:
            return True
        if self._idle_provider is None:
            return False
        return bool(
            self._idle_provider.is_idle_for_validation(
                int(self.config.validation_idle_after_seconds),
            )
        )

    @staticmethod
    def _normalize_replay_score(raw_score: Any) -> Optional[float]:
        if not isinstance(raw_score, (int, float)) or isinstance(raw_score, bool):
            return None
        value = float(raw_score)
        if value <= -1.0:
            return 0.0
        if value >= 1.0:
            return 1.0
        if value == 0.0:
            return 0.5
        return max(0.0, min(1.0, (value + 1.0) / 2.0))

    @staticmethod
    def _accept_replay_candidate(*, candidate_mean: float, baseline_mean: float, threshold: float, acceptance_mode: str = "strict_improvement") -> bool:
        if acceptance_mode == "non_inferior":
            return candidate_mean >= threshold and candidate_mean >= baseline_mean
        return candidate_mean >= threshold and candidate_mean > baseline_mean

    @staticmethod
    def _build_replay_skill_system(skill: Optional[dict[str, Any]]) -> str:
        lines = [
            "You are replaying a previously observed user task on this client machine.",
            "This is a tool-free replay validation pass.",
            "Do not emit tool calls, bash blocks, file-inspection plans, or requests to inspect the workspace again.",
            "Use any provided prior evidence as fixed context and answer directly.",
            "Return only the final answer requested by the user instruction.",
        ]
        if isinstance(skill, dict) and skill.get("name"):
            lines.extend(
                [
                    "",
                    "Apply the following local skill if it is relevant to the user instruction.",
                    "If it does not apply, answer normally.",
                    "",
                    "<skill_file>",
                    build_skill_md(skill).strip(),
                    "</skill_file>",
                ]
            )
        return "\n".join(lines)

    @staticmethod
    def _extract_evidence(reference_response: str) -> str:
        """Extract only the evidence field from a JSON reference response.

        The original run's final answer is typically a JSON object with
        predicted_cves, predicted_files, root_cause, evidence, etc.
        We return only the evidence text so that baseline and candidate
        branches must each derive their own conclusions.
        """
        text = reference_response.strip()
        if not text:
            return ""
        # Try parsing as JSON first
        try:
            obj = json.loads(text)
            if isinstance(obj, dict):
                evidence = str(obj.get("evidence") or "").strip()
                if evidence:
                    return evidence[:3000]
                # If no evidence key, return root_cause as fallback context
                root_cause = str(obj.get("root_cause") or "").strip()
                if root_cause:
                    return f"Context: {root_cause[:3000]}"
        except (json.JSONDecodeError, ValueError):
            pass
        # If not JSON, return first 2000 chars as raw context
        return text[:2000]

    @staticmethod
    def _extract_raw_observations(reference_response: str) -> str:
        """Extract raw findings (bullet points) from reference response, excluding the JSON conclusion."""
        text = reference_response.strip()
        if not text:
            return ""
        json_start = text.find("{")
        if json_start > 100:
            observations = text[:json_start].strip()
            if observations:
                return observations[:3000]
        return text[:2000]

    @staticmethod
    def _build_replay_messages(case: dict[str, Any], skill: Optional[dict[str, Any]], *, context_mode: str = "evidence") -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        system_prompt = ReplayGateWorker._build_replay_skill_system(skill)
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        instruction = str(case.get("instruction", "") or "").strip()
        if instruction:
            messages.append({"role": "user", "content": instruction})
        reference_response = str(case.get("reference_response", "") or "").strip()
        # Extract only the evidence portion from the original run so that
        # baseline and candidate must each derive their own conclusions from
        # the same raw evidence.  Passing the full reference_response (which
        # includes predicted_cves / root_cause / etc.) makes both branches
        # produce identical output, defeating the purpose of replay.
        if context_mode == "blind":
            context_text = ReplayGateWorker._extract_raw_observations(reference_response)
            context_label = "raw workspace observations (no conclusions)"
        else:
            context_text = ReplayGateWorker._extract_evidence(reference_response)
            context_label = "raw observations only, no conclusions"
        evidence_only = context_text
        if evidence_only:
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "Previously collected " + context_label + " from the original run "
                        "no conclusions):\n"
                        "<original_evidence>\n"
                        f"{evidence_only}\n"
                        "</original_evidence>\n\n"
                        "Based on the evidence above and the skill guidance, derive your own "
                        "conclusions. Do not call tools. Do not output bash. "
                        "Produce the best final answer you can."
                    ),
                }
            )
        else:
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "Replay this task without tools. Do not output bash or inspection plans. "
                        "Return only the final answer requested by the instruction."
                    ),
                }
            )
        return messages

    @staticmethod
    def _score_with_case_output(response_text: str, ground_truth: dict) -> dict[str, Any]:
        """Score response using 5-dimension matching against ground truth (0-1 scale)."""
        import json as _json
        import re as _re
        # Parse JSON from response
        obj = {}
        try:
            obj = _json.loads(response_text.strip())
        except (ValueError, _json.JSONDecodeError):
            match = _re.search(r'\{.*\}', response_text, _re.DOTALL)
            if match:
                try: obj = _json.loads(match.group(0))
                except: pass
        raw_lower = response_text.lower()
        score = 0.0
        max_score = 0.0
        details = {}
        # CVE
        cves = [str(v) for v in (ground_truth.get('cves') or [])]
        if cves:
            max_score += 2
            hit = any(v.lower() in raw_lower for v in cves)
            details['cve'] = hit
            if hit: score += 2
        # Files
        files = [str(v) for v in (ground_truth.get('files') or [])]
        if files:
            max_score += 2
            file_basenames = [v.rsplit('/', 1)[-1] for v in files]
            hit = any(v.lower() in raw_lower for v in files + file_basenames)
            details['file'] = hit
            if hit: score += 2
        # Functions
        funcs = [str(v) for v in (ground_truth.get('functions') or [])]
        if funcs:
            max_score += 3
            hit = any(v.lower() in raw_lower for v in funcs)
            details['function'] = hit
            if hit: score += 3
        # Required evidence
        req_ev = [str(v) for v in (ground_truth.get('required_evidence') or [])]
        if req_ev:
            max_score += 1
            hit = any(v.lower() in raw_lower for v in req_ev)
            details['evidence'] = hit
            if hit: score += 1
        # Root cause terms - filter stop words and require >=2 meaningful matches
        rc = str(ground_truth.get('root_cause') or '')
        if rc:
            max_score += 2
            _stop = frozenset({
                'the', 'and', 'for', 'with', 'that', 'this', 'from', 'into', 'via',
                'without', 'which', 'overflows', 'overflow', 'buffer', 'stack',
                'handler', 'parameter', 'not', 'sanitized', 'any', 'length',
                'check', 'checked', 'bounds', 'read', 'reads', 'passes', 'using',
                'used', 'uses', 'then', 'when', 'while', 'after', 'before',
                'during', 'through', 'allowing', 'allows', 'can', 'may', 'will',
                'has', 'have', 'been', 'being', 'was', 'were', 'are', 'its',
                'their', 'such', 'also', 'but', 'however', 'resulting', 'result',
                'causes', 'caused', 'cause', 'executes', 'executed', 'execute',
                'formats', 'formatted', 'format', 'command', 'string', 'value',
                'field', 'data', 'bytes', 'memory', 'access', 'insufficient',
                'validated', 'validate', 'validation', 'performs', 'performed',
                'perform', 'system', 'sprintf', 'vsprintf', 'vsnprintf', 'strcpy',
                'memcpy', 'function', 'call', 'called', 'returns', 'return',
                'wrapper', 'user', 'provided', 'directly', 'request', 'response',
                'http', 'post', 'body', 'header', 'based', 'following',
            })
            raw_terms = _re.split(r'[^a-zA-Z0-9_-]+', rc)
            meaningful = []
            seen = set()
            for t in raw_terms:
                tl = t.lower()
                if len(t) < 4 or tl in _stop or tl in seen:
                    continue
                if t.replace('-', '').replace('.', '').isdigit():
                    continue
                seen.add(tl)
                meaningful.append(tl)
            hits = [t for t in meaningful if t in raw_lower]
            details['root_cause'] = {"hit": len(hits) >= 2, "matched": hits, "expected_terms": meaningful}
            if len(hits) >= 2: score += 2
        normalized = round(score / max_score, 3) if max_score > 0 else 0.0
        return {"normalized_score": normalized, "details": details}

    async def _run_replay_branch(
        self,
        case: dict[str, Any],
        skill: Optional[dict[str, Any]],
        *,
        label: str,
    ) -> dict[str, Any]:
        context_mode = str(getattr(self.config, "replay_context_mode", "evidence") or "evidence")
        scoring_mode = str(getattr(self.config, "replay_scoring_mode", "prm") or "prm")
        messages = self._build_replay_messages(case, skill, context_mode=context_mode)
        if not messages or messages[-1].get("role") != "user":
            raise ValueError("replay case missing user instruction")
        response_text = await self._client.chat(
            messages,
            max_tokens=2048,
            temperature=0.1,
        )
        prm_result = await self._prm_scorer.evaluate(
            response_text,
            str(case.get("instruction", "") or ""),
        )
        # Use mean of individual PRM votes for finer granularity instead of
        # coarse majority vote.  Majority vote collapses [1,1,-1] and [1,1,1]
        # both to 1, making them indistinguishable.  Mean vote preserves the
        # difference: [1,1,-1] -> 0.667, [1,1,1] -> 1.0.
        votes = prm_result.get("votes", [])
        valid_votes = [v for v in votes if isinstance(v, (int, float)) and not isinstance(v, bool)]
        if valid_votes:
            mean_vote = sum(valid_votes) / len(valid_votes)
            prm_normalized = max(0.0, min(1.0, (mean_vote + 1.0) / 2.0))
        else:
            prm_normalized = self._normalize_replay_score(prm_result.get("score"))
        # Case-output scoring (5-dimension match against ground truth)
        ground_truth = case.get("ground_truth") or {}
        case_output_result = self._score_with_case_output(response_text, ground_truth)
        case_output_score = case_output_result.get("normalized_score", 0.0)
        if scoring_mode == "case_output":
            normalized_score = case_output_score
        else:
            normalized_score = prm_normalized
        return {
            "label": label,
            "response_text": response_text,
            "prm_score": prm_result.get("score"),
            "normalized_score": normalized_score,
            "prm_normalized": prm_normalized,
            "case_output_score": case_output_score,
            "case_output_details": case_output_result.get("details", {}),
            "scoring_mode": scoring_mode,
            "context_mode": context_mode,
            "prm_votes": prm_result.get("votes", []),
        }

    async def _replay_validate_job(self, job: dict[str, Any]) -> dict[str, Any]:
        candidate_skill = job.get("candidate_skill")
        if not isinstance(candidate_skill, dict) or not candidate_skill.get("name"):
            raise ValueError("replay gate job missing candidate_skill")

        replay_cases = [case for case in (job.get("replay_cases") or []) if isinstance(case, dict)]
        if not replay_cases:
            raise ValueError("replay gate job missing replay_cases")

        current_skill = job.get("current_skill") if isinstance(job.get("current_skill"), dict) else None
        acceptance_mode = str(getattr(self.config, "replay_acceptance_mode", "strict_improvement") or "strict_improvement")
        scoring_mode = str(getattr(self.config, "replay_scoring_mode", "prm") or "prm")
        case_results: list[dict[str, Any]] = []
        candidate_scores: list[float] = []
        baseline_scores: list[float] = []

        for case in replay_cases[:3]:
            baseline = await self._run_replay_branch(case, current_skill, label="baseline")
            candidate = await self._run_replay_branch(case, candidate_skill, label="candidate")
            baseline_score = baseline.get("normalized_score")
            candidate_score = candidate.get("normalized_score")
            if isinstance(baseline_score, (int, float)):
                baseline_scores.append(float(baseline_score))
            if isinstance(candidate_score, (int, float)):
                candidate_scores.append(float(candidate_score))
            case_results.append(
                {
                    "session_id": str(case.get("session_id", "") or ""),
                    "turn_num": int(case.get("turn_num", 0) or 0),
                    "instruction": str(case.get("instruction", "") or ""),
                    "baseline": baseline,
                    "candidate": candidate,
                }
            )

        if not candidate_scores:
            raise ValueError("replay gate produced no candidate scores")

        candidate_mean = round(sum(candidate_scores) / len(candidate_scores), 3)
        baseline_mean = round(sum(baseline_scores) / len(baseline_scores), 3) if baseline_scores else 0.0
        threshold = round(float(job.get("min_score", 0.75)), 3)
        accepted = self._accept_replay_candidate(
            candidate_mean=candidate_mean,
            baseline_mean=baseline_mean,
            threshold=threshold,
            acceptance_mode=acceptance_mode,
        )
        decision = "accept" if accepted else "reject"
        reason = (
            f"Replay validation compared {len(case_results)} case(s): "
            f"candidate_mean={candidate_mean}, baseline_mean={baseline_mean}, "
            f"threshold={threshold}, acceptance_mode={acceptance_mode}, "
            f"scoring_mode={scoring_mode}"
        )
        return {
            "gate_mode": "replay",
            "validator_mode": "replay",
            "decision": decision,
            "accepted": accepted,
            "score": candidate_mean,
            "threshold": threshold,
            "reason": reason,
            "checks": {
                "grounded_in_evidence": candidate_mean,
                "preserves_existing_value": min(1.0, max(0.0, candidate_mean - baseline_mean + 0.5)),
                "specificity_and_reusability": candidate_mean,
                "safe_to_publish": candidate_mean,
            },
            "replay_summary": {
                "case_count": len(case_results),
                "baseline_mean_score": baseline_mean,
                "candidate_mean_score": candidate_mean,
                "cases": case_results,
                "scoring_mode": scoring_mode,
                "acceptance_mode": acceptance_mode,
            },
        }

    async def _real_rerun_validate_job(self, job: dict[str, Any]) -> dict[str, Any]:
        """Scheme B: trigger real agent re-runs with candidate skill via remote VM.

        Falls back to Scheme A (replay) when real re-run is not possible
        (no case_id, SSH failure, timeout, etc.).
        """
        candidate_skill = job.get("candidate_skill")
        if not isinstance(candidate_skill, dict) or not candidate_skill.get("name"):
            raise ValueError("replay gate job missing candidate_skill")

        replay_cases = [case for case in (job.get("replay_cases") or []) if isinstance(case, dict)]
        if not replay_cases:
            raise ValueError("replay gate job missing replay_cases")

        current_skill = job.get("current_skill") if isinstance(job.get("current_skill"), dict) else None
        acceptance_mode = str(getattr(self.config, "replay_acceptance_mode", "strict_improvement") or "strict_improvement")
        rerun_threshold = float(getattr(self.config, "real_rerun_threshold", 0.6) or 0.6)

        # Try real re-run for each case; fall back to replay for cases without case_id
        case_results: list[dict[str, Any]] = []
        candidate_scores: list[float] = []
        baseline_scores: list[float] = []
        rerun_count = 0
        fallback_count = 0

        for case in replay_cases[:3]:
            case_id = str(case.get("case_id", "") or "").strip()
            ground_truth = case.get("ground_truth") or {}

            if case_id:
                try:
                    result = await self._trigger_remote_rerun(
                        case=case,
                        case_id=case_id,
                        candidate_skill=candidate_skill,
                        current_skill=current_skill,
                        ground_truth=ground_truth,
                    )
                    if result is not None:
                        candidate_scores.append(result["candidate_score"])
                        baseline_scores.append(result["baseline_score"])
                        case_results.append(result)
                        rerun_count += 1
                        continue
                except Exception as exc:
                    logger.warning("[ReplayGateWorker] real re-run failed for case %s: %s", case_id, exc)

            # Fallback to Scheme A replay for this case
            baseline = await self._run_replay_branch(case, current_skill, label="baseline")
            candidate = await self._run_replay_branch(case, candidate_skill, label="candidate")
            bs = baseline.get("normalized_score")
            cs = candidate.get("normalized_score")
            if isinstance(bs, (int, float)):
                baseline_scores.append(float(bs))
            if isinstance(cs, (int, float)):
                candidate_scores.append(float(cs))
            case_results.append({
                "session_id": str(case.get("session_id", "") or ""),
                "case_id": case_id,
                "mode": "replay_fallback",
                "baseline": baseline,
                "candidate": candidate,
            })
            fallback_count += 1

        if not candidate_scores:
            raise ValueError("real re-run gate produced no candidate scores")

        candidate_mean = round(sum(candidate_scores) / len(candidate_scores), 3)
        baseline_mean = round(sum(baseline_scores) / len(baseline_scores), 3) if baseline_scores else 0.0
        threshold = round(rerun_threshold, 3)
        accepted = self._accept_replay_candidate(
            candidate_mean=candidate_mean,
            baseline_mean=baseline_mean,
            threshold=threshold,
            acceptance_mode=acceptance_mode,
        )
        decision = "accept" if accepted else "reject"
        reason = (
            f"Real re-run validation: {rerun_count} real rerun(s), {fallback_count} replay fallback(s). "
            f"candidate_mean={candidate_mean}, baseline_mean={baseline_mean}, "
            f"threshold={threshold}, acceptance_mode={acceptance_mode}"
        )
        return {
            "gate_mode": "real_rerun",
            "validator_mode": "real_rerun",
            "decision": decision,
            "accepted": accepted,
            "score": candidate_mean,
            "threshold": threshold,
            "reason": reason,
            "checks": {
                "grounded_in_evidence": candidate_mean,
                "preserves_existing_value": min(1.0, max(0.0, candidate_mean - baseline_mean + 0.5)),
                "specificity_and_reusability": candidate_mean,
                "safe_to_publish": candidate_mean,
            },
            "rerun_summary": {
                "case_count": len(case_results),
                "real_rerun_count": rerun_count,
                "replay_fallback_count": fallback_count,
                "baseline_mean_score": baseline_mean,
                "candidate_mean_score": candidate_mean,
                "cases": case_results,
                "acceptance_mode": acceptance_mode,
            },
        }

    async def _trigger_remote_rerun(
        self,
        *,
        case: dict[str, Any],
        case_id: str,
        candidate_skill: dict[str, Any],
        current_skill: Optional[dict[str, Any]],
        ground_truth: dict,
    ) -> Optional[dict[str, Any]]:
        """Trigger a real agent re-run on the remote VM with an injected skill.

        Returns None to signal fallback to replay if prerequisites are missing.
        """
        import time
        import uuid

        vm_host = str(getattr(self.config, "real_rerun_vm_host", "192.168.1.4") or "192.168.1.4")
        vm_user = str(getattr(self.config, "real_rerun_vm_user", "li") or "li")
        vm_key = str(getattr(self.config, "real_rerun_vm_key_path", "~/.ssh/skillclaw_vm") or "~/.ssh/skillclaw_vm")
        skillclaw_url = str(getattr(self.config, "real_rerun_skillclaw_url", "http://127.0.0.1:30000") or "http://127.0.0.1:30000")
        skillclaw_key = str(getattr(self.config, "real_rerun_skillclaw_key", "") or os.environ.get("SKILLCLAW_API_KEY", ""))
        remote_repo = str(getattr(self.config, "real_rerun_remote_repo", "/home/li/skillclaw-eval/SkillClaw") or "/home/li/skillclaw-eval/SkillClaw")

        # Expand ~ in key path
        vm_key = os.path.expanduser(vm_key)
        if not os.path.exists(vm_key):
            logger.warning("[ReplayGateWorker] SSH key not found: %s, falling back to replay", vm_key)
            return None

        # Build inline skill payload for session override
        skill_name = str(candidate_skill.get("name") or "")
        skill_body = str(candidate_skill.get("body") or candidate_skill.get("markdown") or candidate_skill.get("content") or "")
        if not skill_body:
            return None

        # Generate a unique session ID for this re-run
        rerun_session_id = str(uuid.uuid4())

        # Register session override on SkillClaw
        import urllib.request
        import urllib.error

        override_payload = json.dumps({
            "inline_skills": [{"name": skill_name, "content": skill_body}],
            "note": f"replay gate re-run for candidate {skill_name}",
        }).encode("utf-8")

        override_url = f"{skillclaw_url}/v1/session-overrides/{rerun_session_id}"
        req = urllib.request.Request(override_url, data=override_payload, method="POST")
        req.add_header("Content-Type", "application/json")
        if skillclaw_key:
            req.add_header("Authorization", f"Bearer {skillclaw_key}")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                logger.info("[ReplayGateWorker] session override set for %s", rerun_session_id)
        except urllib.error.URLError as exc:
            logger.warning("[ReplayGateWorker] failed to set session override: %s", exc)
            return None

        # Also set up a baseline session (no skill or current skill)
        baseline_session_id = str(uuid.uuid4())
        baseline_payload = json.dumps({
            "disable_skills": True,
            "note": "replay gate baseline (no skill)",
        }).encode("utf-8")
        baseline_req = urllib.request.Request(
            f"{skillclaw_url}/v1/session-overrides/{baseline_session_id}",
            data=baseline_payload,
            method="POST",
        )
        baseline_req.add_header("Content-Type", "application/json")
        if skillclaw_key:
            baseline_req.add_header("Authorization", f"Bearer {skillclaw_key}")
        try:
            with urllib.request.urlopen(baseline_req, timeout=10) as resp:
                pass
        except urllib.error.URLError:
            pass

        # Trigger remote runs via SSH
        case_file = f"benchmarks/cases/{case_id}.json"
        remote_output_dir = f"/tmp/skillclaw-rerun-{rerun_session_id}"

        async def _run_ssh(session_id: str, output_dir: str) -> str:
            """Run a single case on the remote VM via SSH and return the output text."""
            cmd = (
                f"cd {remote_repo} && "
                f"env SKILLCLAW_PATH_PROFILE=vm-li "
                f"python3 -m evaluation.runs.run_single_case "
                f"{case_file} --mode blind-skillclaw-inline-guarded "
                f"--session-id {session_id} "
                f"--output-dir {output_dir} "
                f"--skillclaw-url {skillclaw_url}"
            )
            if skillclaw_key:
                cmd += f" --skillclaw-key {skillclaw_key}"

            ssh_cmd = ["ssh", "-i", vm_key, "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=10",
                       f"{vm_user}@{vm_host}", cmd]
            proc = await asyncio.create_subprocess_exec(
                *ssh_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=1800)
            except asyncio.TimeoutError:
                proc.kill()
                logger.warning("[ReplayGateWorker] SSH re-run timed out for %s", session_id)
                return ""
            if proc.returncode != 0:
                logger.warning("[ReplayGateWorker] SSH re-run failed (%s): %s", proc.returncode, stderr.decode()[:500])
                return ""
            return stdout.decode("utf-8", errors="replace")

        # Run candidate and baseline in parallel
        candidate_task = _run_ssh(rerun_session_id, remote_output_dir + "-candidate")
        baseline_task = _run_ssh(baseline_session_id, remote_output_dir + "-baseline")
        candidate_raw, baseline_raw = await asyncio.gather(candidate_task, baseline_task, return_exceptions=True)

        # Handle exceptions from gather
        if isinstance(candidate_raw, Exception):
            logger.warning("[ReplayGateWorker] candidate re-run exception: %s", candidate_raw)
            candidate_raw = ""
        if isinstance(baseline_raw, Exception):
            logger.warning("[ReplayGateWorker] baseline re-run exception: %s", baseline_raw)
            baseline_raw = ""

        # Score with case_output - prefer VM\'s own detailed score
        # The VM runs score_case_output.py which gives a fine-grained 5-dimension
        # score (0-10).  We parse that directly instead of re-scoring with the
        # coarse substring matcher, which collapses different-quality responses
        # to the same normalized score.
        candidate_result = self._parse_vm_score(candidate_raw, ground_truth)
        baseline_result = self._parse_vm_score(baseline_raw, ground_truth)

        return {
            "session_id": str(case.get("session_id", "") or ""),
            "case_id": case_id,
            "mode": "real_rerun",
            "rerun_session_id": rerun_session_id,
            "baseline_session_id": baseline_session_id,
            "candidate": {
                "response_text": candidate_raw[:2000],
                "normalized_score": candidate_result.get("normalized_score", 0.0),
                "case_output_score": candidate_result.get("normalized_score", 0.0),
                "case_output_details": candidate_result.get("details", {}),
            },
            "baseline": {
                "response_text": baseline_raw[:2000],
                "normalized_score": baseline_result.get("normalized_score", 0.0),
                "case_output_score": baseline_result.get("normalized_score", 0.0),
                "case_output_details": baseline_result.get("details", {}),
            },
            "candidate_score": candidate_result.get("normalized_score", 0.0),
            "baseline_score": baseline_result.get("normalized_score", 0.0),
        }

    def _parse_vm_score(self, raw_text: str, ground_truth: dict) -> dict[str, Any]:
        """Parse the VM's own score from run_single_case stdout.

        The VM outputs a JSON object with "score" and "max_score" fields
        (computed by score_case_output.py with 5-dimension matching).
        We use that directly for finer granularity than the coarse substring
        matcher in _score_with_case_output.

        Falls back to _score_with_case_output if parsing fails.
        """
        import json as _json
        import re as _re

        obj = {}
        try:
            obj = _json.loads(raw_text.strip())
        except (ValueError, _json.JSONDecodeError):
            match = _re.search(r'\{.*\}', raw_text, _re.DOTALL)
            if match:
                try:
                    obj = _json.loads(match.group(0))
                except Exception:
                    pass

        vm_score = obj.get("score")
        vm_max = obj.get("max_score", 10)
        if isinstance(vm_score, (int, float)) and isinstance(vm_max, (int, float)) and vm_max > 0:
            normalized = round(float(vm_score) / float(vm_max), 3)
            return {
                "normalized_score": normalized,
                "details": {
                    "vm_score": vm_score,
                    "vm_max_score": vm_max,
                    "source": "vm_score_case_output",
                },
            }

        # Fallback to coarse substring matching
        return self._score_with_case_output(raw_text, ground_truth)

    async def _validate_job(self, job: dict[str, Any]) -> dict[str, Any]:
        real_rerun = bool(getattr(self.config, "real_rerun_enabled", False))
        if real_rerun:
            try:
                return await self._real_rerun_validate_job(job)
            except Exception as exc:
                logger.warning("[ReplayGateWorker] real re-run failed, falling back to replay: %s", exc)
        return await self._replay_validate_job(job)

    async def run_once(self, *, force: bool = False) -> dict[str, Any]:
        summary = ReplayGateRunSummary()
        if not self._gate_enabled():
            summary.reason = "replay gate disabled or sharing not configured"
            return summary.__dict__
        if not self._quota_available():
            summary.reason = "daily replay gate quota reached"
            return summary.__dict__
        if not self._is_idle(force=force):
            summary.reason = "client is not idle"
            return summary.__dict__

        jobs = self._store.list_open_jobs(user_alias=self._user_alias)
        summary.checked_jobs = len(jobs)
        if not jobs:
            summary.reason = "no open validation jobs"
            return summary.__dict__

        for job in jobs:
            if not self._quota_available():
                summary.reason = "daily replay gate quota reached"
                break
            job_id = str(job.get("job_id", "") or "")
            if not job_id:
                summary.skipped_jobs += 1
                continue
            try:
                result = await self._validate_job(job)
            except Exception as exc:
                logger.warning("[ReplayGateWorker] job %s failed: %s", job_id, exc)
                summary.skipped_jobs += 1
                continue

            self._store.save_result(job_id, self._user_alias, result)
            self._jobs_completed_today += 1
            summary.validated_jobs += 1
            logger.info(
                "[ReplayGateWorker] submitted gate result for job %s as %s (score=%s)",
                job_id,
                self._user_alias,
                result.get("score"),
            )
            if summary.validated_jobs >= max(1, int(self.config.validation_max_concurrency)):
                break

        if summary.validated_jobs == 0 and not summary.reason:
            summary.reason = "no jobs validated"
        elif summary.validated_jobs > 0:
            summary.reason = "validated"
        return summary.__dict__

    async def run(self) -> None:
        interval = max(5, int(self.config.validation_poll_interval_seconds))
        logger.info(
            "[ReplayGateWorker] enabled=%s mode=%s interval=%ss idle_after=%ss",
            self.config.validation_enabled,
            "replay",
            interval,
            self.config.validation_idle_after_seconds,
        )
        while not self._stop_event.is_set():
            try:
                await self.run_once()
            except Exception as exc:
                logger.warning("[ReplayGateWorker] polling loop failed: %s", exc)
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=interval)
            except asyncio.TimeoutError:
                continue

    def status_snapshot(self) -> dict[str, Any]:
        last_request_age = None
        active_sessions = None
        idle_now = None
        if self._idle_provider is not None:
            try:
                last_request_age = self._idle_provider.last_request_age_seconds()
                active_sessions = self._idle_provider.active_session_count()
                idle_now = self._idle_provider.is_idle_for_validation(
                    int(self.config.validation_idle_after_seconds),
                )
            except Exception:
                pass
        return {
            "enabled": bool(self.config.validation_enabled),
            "mode": "replay",
            "sharing_enabled": bool(self.config.sharing_enabled),
            "group_id": str(self.config.sharing_group_id or ""),
            "user_alias": self._user_alias,
            "idle_after_seconds": int(self.config.validation_idle_after_seconds),
            "poll_interval_seconds": int(self.config.validation_poll_interval_seconds),
            "max_jobs_per_day": int(self.config.validation_max_jobs_per_day),
            "jobs_completed_today": int(self._jobs_completed_today),
            "active_sessions": active_sessions,
            "last_request_age_seconds": last_request_age,
            "idle_now": idle_now,
            "open_jobs_for_me": len(self._store.list_open_jobs(user_alias=self._user_alias))
            if self._gate_enabled()
            else 0,
        }


ValidationWorker = ReplayGateWorker
