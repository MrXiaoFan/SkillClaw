#!/usr/bin/env python3
"""Build a publication-facing benchmark runset from a broader current runset."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

try:
    from evaluation.cases.loader import load_case_definition
    from evaluation.reporting.current.refresh_reports import (
        _load_manifest,
        _load_json,
        _record_path_from_run_manifest,
        _record_paths_from_run_index,
        _resolve_paths,
    )
except ImportError:  # pragma: no cover - direct script execution.
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from evaluation.cases.loader import load_case_definition
    from evaluation.reporting.current.refresh_reports import (
        _load_manifest,
        _load_json,
        _record_path_from_run_manifest,
        _record_paths_from_run_index,
        _resolve_paths,
    )


def _repo_root_from_manifest(path: Path) -> Path:
    resolved = path.resolve()
    parent = resolved.parent
    if parent.name == "publication" and parent.parent.name == "reports":
        return parent.parent.parent
    if parent.name == "latest" and parent.parent.name == "reports":
        return parent.parent.parent
    if parent.name == "reports":
        return parent.parent
    return resolved.parents[1]


def _case_meta(case_id: str, repo_root: Path) -> dict[str, Any]:
    if not case_id:
        return {}
    path = repo_root / "benchmarks" / "cases" / f"{case_id}.json"
    if not path.is_file():
        return {}
    return load_case_definition(path)


def _record_case_id(record_path: Path) -> str:
    value = _load_json(record_path)
    if not isinstance(value, dict):
        return ""
    return str(value.get("case_id") or "").strip()


def _manifest_case_id(manifest_path: Path) -> str:
    record_path = _record_path_from_run_manifest(manifest_path)
    if record_path is None or not record_path.is_file():
        return ""
    return _record_case_id(record_path)


def _run_index_case_ids(run_index_path: Path) -> list[str]:
    ids: list[str] = []
    for record_path in _record_paths_from_run_index(run_index_path):
        if record_path.is_file():
            case_id = _record_case_id(record_path)
            if case_id:
                ids.append(case_id)
    return ids


def _is_publication_ready(case_id: str, repo_root: Path) -> bool:
    meta = _case_meta(case_id, repo_root)
    benchmark = meta.get("benchmark") if isinstance(meta.get("benchmark"), dict) else {}
    return bool(benchmark.get("publication_ready") or benchmark.get("paper_ready"))


def build_publication_runset_manifest(
    source_manifest_path: Path,
    out_path: Path,
) -> dict[str, Any]:
    source_manifest = _load_manifest(source_manifest_path)
    base_dir = source_manifest_path.parent
    repo_root = _repo_root_from_manifest(source_manifest_path)

    selected_manifests: list[str] = []
    for manifest_path in _resolve_paths(list(source_manifest.get("manifests") or []), base_dir):
        case_id = _manifest_case_id(manifest_path)
        if case_id and _is_publication_ready(case_id, repo_root):
            selected_manifests.append(os.path.relpath(manifest_path, base_dir).replace("\\", "/"))

    selected_records: list[str] = []
    for record_path in _resolve_paths(list(source_manifest.get("records") or []), base_dir):
        case_id = _record_case_id(record_path)
        if case_id and _is_publication_ready(case_id, repo_root):
            selected_records.append(os.path.relpath(record_path, base_dir).replace("\\", "/"))

    selected_run_indexes: list[str] = []
    for run_index_path in _resolve_paths(list(source_manifest.get("run_indexes") or []), base_dir):
        case_ids = _run_index_case_ids(run_index_path)
        if case_ids and all(_is_publication_ready(case_id, repo_root) for case_id in case_ids):
            selected_run_indexes.append(os.path.relpath(run_index_path, base_dir).replace("\\", "/"))

    derived = {
        "name": f"{source_manifest.get('name', 'runset')}-publication",
        "source_manifest": str(source_manifest_path.resolve()),
        "runset_purpose": "publication-facing-benchmark-subset",
        "publication_only": True,
        "eligibility_note": (
            "This runset is automatically derived from the broader current engineering runset. "
            "Only cases whose case JSON declares `benchmark.publication_ready = true` are included."
        ),
        "min_samples": int(source_manifest.get("min_samples", 2)),
        "promote_samples": int(source_manifest.get("promote_samples", 3)),
        "records": selected_records,
        "manifests": selected_manifests,
        "run_indexes": selected_run_indexes,
        "outputs": {
            "matrix_md": "result_matrix.md",
            "feedback_md": "skill_feedback.md",
            "gate_md": "skill_gate.md",
            "gate_json": "skill_gate.json",
            "bundle_json": "skill_feedback_bundle.json",
            "runset_md": "runset.md",
        },
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(derived, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return derived


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-manifest",
        type=Path,
        default=Path("reports/current/runset_manifest.json"),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("reports/publication/runset_manifest.json"),
    )
    args = parser.parse_args(argv)

    result = build_publication_runset_manifest(args.source_manifest.resolve(), args.out.resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


derive_publication_manifest = build_publication_runset_manifest
derive_publication_ready_manifest = build_publication_runset_manifest





