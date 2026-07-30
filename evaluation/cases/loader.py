"""Load and normalize benchmark case definitions."""

from __future__ import annotations

import copy
import hashlib
import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

DEFAULT_SCORING: dict[str, Any] = {
    "max_score": 10,
    "weights": {
        "cve": 2,
        "file": 2,
        "function": 3,
        "root_cause": 2,
        "evidence": 1,
    },
}

COMMON_VALIDATOR_DEFAULTS: dict[str, Any] = {
    "enabled": True,
    "allow_failure": False,
}

VALIDATOR_TYPE_DEFAULTS: dict[str, dict[str, Any]] = {
    "content_match": {
        "source": "agent_output",
        "use_ground_truth": True,
        "match": "any",
    },
    "asan_command": {
        "expect_crash": True,
        "stack_match": "any",
    },
}

PATH_PROFILE_ENV = "SKILLCLAW_PATH_PROFILE"


def _clone_json_object(value: Mapping[str, Any]) -> dict[str, Any]:
    return copy.deepcopy(dict(value))


def _slug_path_fragment(text: str) -> str:
    allowed: list[str] = []
    for char in str(text or ""):
        if char.isalnum() or char in {"-", "_", "."}:
            allowed.append(char)
        else:
            allowed.append("-")
    value = "".join(allowed).strip("-")
    return value or "case"


def _expand_path_text(text: str | Path) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(str(text)))).resolve()


def _path_text_candidates(container: Mapping[str, Any], field_name: str) -> list[str]:
    profile = str(os.environ.get(PATH_PROFILE_ENV) or "").strip()
    profile_map = container.get(f"{field_name}_by_profile")
    direct = container.get(field_name)
    candidates = container.get(f"{field_name}_candidates")

    ordered: list[str] = []
    seen: set[str] = set()

    def add(value: Any) -> None:
        text = str(value or "").strip()
        if not text or text in seen:
            return
        seen.add(text)
        ordered.append(text)

    if profile and isinstance(profile_map, Mapping):
        add(profile_map.get(profile))

    add(direct)

    if isinstance(candidates, list):
        for item in candidates:
            add(item)

    if isinstance(profile_map, Mapping):
        for key, value in profile_map.items():
            if profile and str(key) == profile:
                continue
            add(value)

    return ordered


def iter_case_path_candidates(
    case: Mapping[str, Any],
    section: str,
    field_name: str,
    *,
    override: str | Path | None = None,
    default: str | Path | None = None,
) -> list[Path]:
    if override:
        return [_expand_path_text(override)]

    container = case.get(section)
    if not isinstance(container, Mapping):
        container = {}

    texts = _path_text_candidates(container, field_name)
    if default is not None and not texts:
        texts = [str(default)]

    paths: list[Path] = []
    seen: set[str] = set()
    for text in texts:
        path = _expand_path_text(text)
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        paths.append(path)
    return paths


def resolve_case_path(
    case: Mapping[str, Any],
    section: str,
    field_name: str,
    *,
    override: str | Path | None = None,
    default: str | Path | None = None,
) -> Path:
    candidates = iter_case_path_candidates(
        case,
        section,
        field_name,
        override=override,
        default=default,
    )
    for path in candidates:
        if path.exists():
            return path
    if candidates:
        return candidates[0]
    return _expand_path_text(default or ".")


def resolve_source_root(case: Mapping[str, Any], override: str | Path | None = None) -> Path:
    return resolve_case_path(case, "target", "source_root", override=override, default=".")


def _default_blind_agent_root(case: Mapping[str, Any]) -> Path:
    source_root = resolve_source_root(case)
    return (source_root.parent / "blind_workspaces" / _blind_workspace_name(case)).resolve()


def _blind_workspace_name(case: Mapping[str, Any]) -> str:
    case_id = str(case.get("case_id") or "").strip()
    target = case.get("target") if isinstance(case.get("target"), Mapping) else {}
    project = str(target.get("project") or "").strip()
    version = str(target.get("version") or "").strip()
    binary = str(target.get("binary") or "").strip()
    seed = "|".join(part for part in (case_id, project, version, binary) if part) or "case"
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:12]
    return f"workspace-{digest}"


def _sanitize_blind_agent_root(case: Mapping[str, Any], path: Path) -> Path:
    root = Path(path).resolve()
    if root.parent == root:
        return root
    return (root.parent / _blind_workspace_name(case)).resolve()


def resolve_blind_agent_root(case: Mapping[str, Any], override: str | Path | None = None) -> Path:
    path = resolve_case_path(
        case,
        "blind_workspace",
        "agent_root",
        override=override,
        default=_default_blind_agent_root(case),
    )
    if override:
        return path
    return _sanitize_blind_agent_root(case, path)


def resolve_blind_validator_root(case: Mapping[str, Any], override: str | Path | None = None) -> Path:
    return resolve_case_path(
        case,
        "blind_workspace",
        "validator_root",
        override=override,
        default=resolve_source_root(case),
    )


def _normalize_scoring(case: dict[str, Any]) -> None:
    scoring = case.get("scoring")
    merged = copy.deepcopy(DEFAULT_SCORING)
    if isinstance(scoring, Mapping):
        if "max_score" in scoring:
            merged["max_score"] = scoring["max_score"]
        weights = scoring.get("weights")
        if isinstance(weights, Mapping):
            merged["weights"].update(dict(weights))
    case["scoring"] = merged


def _normalize_validators(case: dict[str, Any]) -> None:
    validators = case.get("validators")
    if not isinstance(validators, list):
        return

    normalized_validators: list[Any] = []
    for item in validators:
        if not isinstance(item, Mapping):
            normalized_validators.append(copy.deepcopy(item))
            continue
        spec = _clone_json_object(item)
        for key, value in COMMON_VALIDATOR_DEFAULTS.items():
            spec.setdefault(key, value)
        validator_type = str(spec.get("type") or "").strip()
        for key, value in VALIDATOR_TYPE_DEFAULTS.get(validator_type, {}).items():
            spec.setdefault(key, value)
        if validator_type == "artifact_exists" and "artifact_type" not in spec and "min_size_bytes" in spec:
            spec["artifact_type"] = "file"
        normalized_validators.append(spec)
    case["validators"] = normalized_validators


def normalize_case(case: Mapping[str, Any]) -> dict[str, Any]:
    """Return a normalized case object with code-level defaults applied."""
    normalized = _clone_json_object(case)
    _normalize_scoring(normalized)
    _normalize_validators(normalized)
    return normalized


def load_case_definition(path: Path) -> dict[str, Any]:
    """Read one benchmark case JSON file and apply defaults."""
    value = json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return normalize_case(value)
