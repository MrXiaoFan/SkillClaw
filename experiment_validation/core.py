from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any, Callable


ValidatorFn = Callable[["ValidationContext", dict[str, Any]], dict[str, Any]]


@dataclass
class ValidationContext:
    """Shared context passed to every case-level validator."""

    case: dict[str, Any]
    root: Path
    case_path: Path | None = None
    agent_output_path: Path | None = None
    skip_commands: bool = False

    @property
    def timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()


class ValidatorRegistry:
    def __init__(self) -> None:
        self._validators: dict[str, ValidatorFn] = {}

    def register(self, validator_type: str, fn: ValidatorFn) -> None:
        key = str(validator_type or "").strip()
        if not key:
            raise ValueError("validator_type is required")
        self._validators[key] = fn

    def run(self, ctx: ValidationContext, spec: dict[str, Any]) -> dict[str, Any]:
        validator_type = str(spec.get("type", "") or "")
        fn = self._validators.get(validator_type)
        if fn is None:
            return {
                "name": spec.get("name"),
                "type": validator_type,
                "allow_failure": bool(spec.get("allow_failure")),
                "status": "skipped",
                "reason": "unknown validator type",
            }
        result = fn(ctx, spec)
        result.setdefault("name", spec.get("name"))
        result.setdefault("type", validator_type)
        result.setdefault("allow_failure", bool(spec.get("allow_failure")))
        return result


def summarize_checks(checks: list[dict[str, Any]]) -> str:
    hard_failures = [
        item
        for item in checks
        if item.get("status") in {"failed", "missing"} and not bool(item.get("allow_failure"))
    ]
    passed = [item for item in checks if item.get("status") == "passed"]
    skipped = [item for item in checks if item.get("status") == "skipped"]
    soft_failures = [
        item
        for item in checks
        if item.get("status") in {"failed", "missing"} and bool(item.get("allow_failure"))
    ]
    if hard_failures:
        return "failed"
    if passed and len(passed) + len(skipped) + len(soft_failures) == len(checks):
        return "passed"
    if checks:
        return "partial"
    return "no_validators"


def _latest_validation(validation: Any) -> dict[str, Any] | None:
    if isinstance(validation, dict):
        return validation
    if isinstance(validation, list):
        for item in reversed(validation):
            if isinstance(item, dict) and item.get("validator_mode"):
                return item
    return None


def _check_hit(score_result: dict[str, Any] | None, key: str) -> bool:
    if not isinstance(score_result, dict):
        return False
    checks = score_result.get("checks")
    if not isinstance(checks, dict):
        return False
    item = checks.get(key)
    return bool(isinstance(item, dict) and item.get("hit"))


def _has_explicit_check(score_result: dict[str, Any] | None, key: str) -> bool:
    if not isinstance(score_result, dict):
        return False
    checks = score_result.get("checks")
    return isinstance(checks, dict) and isinstance(checks.get(key), dict)


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in re.split(r"[^a-zA-Z0-9]+", str(text).lower())
        if len(token) >= 3
    }


def assess_skill_relevance(
    *,
    case: dict[str, Any] | None = None,
    selected_skills: list[str] | None = None,
) -> dict[str, Any]:
    """Estimate whether selected skills are task-specific.

    This is intentionally a conservative audit signal, not a semantic oracle.
    It prevents high-scoring answers from automatically becoming positive
    feedback for infrastructure/self-inspection skills.
    """

    skills = [str(skill) for skill in (selected_skills or []) if str(skill).strip()]
    if not skills:
        return {
            "status": "no_selected_skills",
            "selected_skills": [],
            "relevant_skills": [],
            "infra_skills": [],
            "matched_terms": {},
        }

    case = case or {}
    text_parts: list[str] = []
    target = case.get("target", {}) if isinstance(case.get("target"), dict) else {}
    truth = case.get("ground_truth", {}) if isinstance(case.get("ground_truth"), dict) else {}
    text_parts.extend(str(target.get(key, "")) for key in ("project", "version", "binary", "build"))
    text_parts.extend(str(truth.get(key, "")) for key in ("vulnerability_type", "root_cause"))
    for key in ("files", "functions", "required_evidence", "cves"):
        value = truth.get(key)
        if isinstance(value, list):
            text_parts.extend(str(item) for item in value)
        elif value:
            text_parts.append(str(value))
    task_terms = set().union(*(_tokens(part) for part in text_parts)) if text_parts else set()

    infra_skills = [skill for skill in skills if skill.startswith("skillclaw-")]
    relevant: list[str] = []
    matched_terms: dict[str, list[str]] = {}
    for skill in skills:
        skill_terms = _tokens(skill)
        matches = sorted(skill_terms & task_terms)
        if matches:
            relevant.append(skill)
            matched_terms[skill] = matches

    if relevant:
        status = "has_task_relevant_skill"
    elif len(infra_skills) == len(skills):
        status = "only_infra_skills"
    else:
        status = "no_task_relevant_skill"

    return {
        "status": status,
        "selected_skills": skills,
        "relevant_skills": relevant,
        "infra_skills": infra_skills,
        "matched_terms": matched_terms,
    }


def build_feedback(
    *,
    score_result: dict[str, Any] | None = None,
    validation_result: Any = None,
    skill_injection: dict[str, Any] | None = None,
    skill_relevance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a compact feedback signal for skill evolution experiments."""

    score = None
    max_score = None
    if isinstance(score_result, dict):
        score = score_result.get("score")
        max_score = score_result.get("max_score")

    validation = _latest_validation(validation_result)
    validation_status = validation.get("status") if validation else None
    selected_skills = []
    if isinstance(skill_injection, dict):
        selected_skills = list(skill_injection.get("selected_skill_names") or [])

    normalized = None
    if isinstance(score, (int, float)) and isinstance(max_score, (int, float)) and max_score:
        normalized = float(score) / float(max_score)

    reasons: list[str] = []
    if selected_skills:
        reasons.append(f"selected_skills={','.join(str(s) for s in selected_skills)}")
    relevance_status = None
    if isinstance(skill_relevance, dict):
        relevance_status = skill_relevance.get("status")
        if relevance_status:
            reasons.append(f"skill_relevance={relevance_status}")
    if normalized is not None:
        reasons.append(f"score={score}/{max_score}")
    if validation_status:
        reasons.append(f"validation={validation_status}")

    quality_flags: list[str] = []
    has_cve_check = _has_explicit_check(score_result, "cve")
    cve_hit = _check_hit(score_result, "cve")
    localization_hit = _check_hit(score_result, "file") or _check_hit(score_result, "function")
    if has_cve_check and not cve_hit and localization_hit:
        quality_flags.append("cve_calibration_miss")
        reasons.append("quality_flag=cve_calibration_miss")

    if relevance_status == "no_selected_skills":
        if "cve_calibration_miss" in quality_flags:
            decision = "neutral"
            action = "baseline_cve_calibration_review"
        elif normalized is not None and normalized >= 0.8 and validation_status in {"passed", "partial", None}:
            decision = "positive"
            action = "use_as_baseline_positive"
        else:
            decision = "neutral"
            action = "baseline_no_skill_feedback"
    elif relevance_status in {"only_infra_skills", "no_task_relevant_skill"} and selected_skills:
        decision = "neutral"
        action = "inspect_retrieval_before_promoting_skill"
    elif "cve_calibration_miss" in quality_flags:
        decision = "neutral"
        action = "revise_cve_calibration_before_promotion"
    elif normalized is not None and normalized >= 0.8 and validation_status in {"passed", "partial", None}:
        decision = "positive"
        action = "keep_or_promote_skill"
    elif normalized is not None and normalized < 0.5:
        decision = "negative"
        action = "inspect_skill_mismatch_or_deprecate"
    elif validation_status == "failed":
        decision = "negative"
        action = "require_dynamic_evidence_before_publish"
    else:
        decision = "neutral"
        action = "collect_more_cases"

    return {
        "decision": decision,
        "suggested_action": action,
        "normalized_score": round(normalized, 3) if normalized is not None else None,
        "validation_status": validation_status,
        "selected_skills": selected_skills,
        "skill_relevance": skill_relevance,
        "quality_flags": quality_flags,
        "reasons": reasons,
    }
