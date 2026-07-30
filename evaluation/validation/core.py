from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import os
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
    if not checks:
        return "no_validators"
    if soft_failures:
        return "partial"
    if passed and len(passed) + len(skipped) == len(checks):
        return "passed"
    return "partial"


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


def _task_profile_enabled() -> bool:
    value = str(os.environ.get("SKILLCLAW_ENABLE_TASK_PROFILE", "") or "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def _task_profile(case: dict[str, Any]) -> dict[str, Any]:
    if not _task_profile_enabled():
        return {}
    profile = case.get("task_profile")
    return profile if isinstance(profile, dict) else {}


def _case_feature_flags(case: dict[str, Any]) -> dict[str, bool]:
    case = case or {}
    target = case.get("target", {}) if isinstance(case.get("target"), dict) else {}
    truth = case.get("ground_truth", {}) if isinstance(case.get("ground_truth"), dict) else {}
    profile = _task_profile(case)
    text_parts: list[str] = []
    text_parts.extend(str(target.get(key, "")) for key in ("project", "version", "binary", "build", "source_root"))
    text_parts.extend(str(truth.get(key, "")) for key in ("vulnerability_type", "root_cause"))
    for key in ("files", "functions", "required_evidence", "cves"):
        value = truth.get(key)
        if isinstance(value, list):
            text_parts.extend(str(item) for item in value)
        elif value:
            text_parts.append(str(value))
    tokens = set().union(*(_tokens(part) for part in text_parts)) if text_parts else set()
    files = [str(item).lower() for item in truth.get("files") or [] if str(item).strip()]
    functions = [str(item).lower() for item in truth.get("functions") or [] if str(item).strip()]

    parser_markers = {
        "parser", "parse", "parsing", "xml", "html", "fragment", "header",
        "lookahead", "chunked", "protocol", "state", "machine", "oob",
    }
    firmware_markers = {
        "firmware", "rootfs", "squashfs", "busybox", "router", "embedded",
        "cgi", "webvpn", "extracted", "iot",
    }
    binary_markers = {
        "elf", "binary", "bsdtar", "xmllint", "tcpdump",
    }
    cwe120_markers = {
        "cwe120", "overflow", "buffer", "strcpy", "strcat", "sprintf", "gets",
    }

    workspace = str(profile.get("workspace") or "").strip().lower()
    target_component = str(profile.get("target_component") or "").strip().lower()
    analysis_mode = str(profile.get("analysis_mode") or "").strip().lower()
    bug_class = str(profile.get("bug_class") or "").strip().lower()

    has_source_tree = bool(target.get("source_root")) or any(name.endswith((".c", ".cc", ".cpp", ".h")) for name in files)
    if workspace in {"source_tree", "mixed"}:
        has_source_tree = True
    has_parser_path = any("parser" in item or "html" in item or "xml" in item or "print-" in item for item in files + functions)
    parser_case = bool(tokens & parser_markers) or has_parser_path
    if target_component in {"file_parser", "network_parser"}:
        parser_case = True
    firmware_case = bool(tokens & firmware_markers)
    if workspace == "firmware_rootfs" or target_component == "firmware_service":
        firmware_case = True
    binary_case = bool(tokens & binary_markers) or bool(target.get("binary"))
    if workspace in {"binary_only", "mixed"} or target_component == "elf_binary" or analysis_mode == "binary_reverse":
        binary_case = True
    cwe120_case = bool(tokens & cwe120_markers)
    if "cwe120" in bug_class or "buffer_overflow" in bug_class:
        cwe120_case = True
    return {
        "source_tree": has_source_tree,
        "parser_case": parser_case,
        "firmware_case": firmware_case,
        "binary_case": binary_case,
        "cwe120_case": cwe120_case,
    }


def _skill_profile_relevant(skill: str, flags: dict[str, bool]) -> bool | None:
    name = str(skill or "").lower()
    if name == "source-parser-state-machine-oob":
        if flags["parser_case"] and flags["source_tree"]:
            return True
        if flags["parser_case"]:
            return None
        return False
    if name in {"vuln-hunting", "vuln-hunting-claw"}:
        return flags["firmware_case"] or (flags["binary_case"] and not flags["source_tree"] and not flags["parser_case"])
    if name == "verify-rootfs-full-enumeration":
        return flags["firmware_case"]
    if name == "elf-cwe120-firmware-triage":
        return flags["firmware_case"] and flags["binary_case"] and flags["cwe120_case"]
    if name.startswith(("ida-", "idalib-")):
        return flags["binary_case"] and not flags["source_tree"]
    return None


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
    flags = _case_feature_flags(case)

    infra_skills = [skill for skill in skills if skill.startswith("skillclaw-")]
    relevant: list[str] = []
    matched_terms: dict[str, list[str]] = {}
    for skill in skills:
        profile_match = _skill_profile_relevant(skill, flags)
        if profile_match is True:
            relevant.append(skill)
            matched_terms[skill] = ["profile_match"]
            continue
        if profile_match is False:
            continue
        skill_terms = _tokens(skill)
        matches = sorted(skill_terms & task_terms)
        if matches:
            relevant.append(skill)
            matched_terms[skill] = matches

    mismatched_skills = [
        skill
        for skill in skills
        if skill not in relevant and skill not in infra_skills
    ]

    if relevant and mismatched_skills:
        status = "mixed_task_relevance"
    elif relevant:
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
        "mismatched_skills": mismatched_skills,
        "matched_terms": matched_terms,
    }


def classify_skill_role(skill_relevance: dict[str, Any] | None, skill: str) -> str:
    if not isinstance(skill_relevance, dict):
        return "unknown"
    name = str(skill)
    if name in [str(item) for item in skill_relevance.get("infra_skills") or []]:
        return "infrastructure"
    if name in [str(item) for item in skill_relevance.get("relevant_skills") or []]:
        return "relevant"
    if name in [str(item) for item in skill_relevance.get("mismatched_skills") or []]:
        return "mismatched"
    return "unknown"


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
        quality_flags.append("cve_identity_miss")
        reasons.append("quality_flag=cve_identity_miss")
    if relevance_status == "mixed_task_relevance":
        quality_flags.append("extraneous_skill_selection")
        reasons.append("quality_flag=extraneous_skill_selection")

    validation_passed = validation_status == "passed"

    if relevance_status == "no_selected_skills":
        if "cve_identity_miss" in quality_flags:
            decision = "neutral"
            action = "baseline_cve_identity_review"
        elif normalized is not None and normalized >= 0.8 and validation_passed:
            decision = "positive"
            action = "use_as_baseline_positive"
        else:
            decision = "neutral"
            action = "baseline_no_skill_feedback"
    elif relevance_status in {"only_infra_skills", "no_task_relevant_skill"} and selected_skills:
        decision = "neutral"
        action = "inspect_retrieval_before_promoting_skill"
    elif "cve_identity_miss" in quality_flags:
        decision = "neutral"
        action = "revise_cve_identity_before_promotion"
    elif relevance_status == "mixed_task_relevance" and normalized is not None and normalized >= 0.8 and validation_passed:
        decision = "positive"
        action = "keep_skill_but_prune_extraneous_selection"
    elif normalized is not None and normalized >= 0.8 and validation_passed:
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

