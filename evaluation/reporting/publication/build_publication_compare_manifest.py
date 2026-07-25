#!/usr/bin/env python3
"""Build a fixed comparison batch manifest for publication-ready cases."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    from evaluation.reporting.publication.build_publication_runset import _case_meta
    from evaluation.reporting.current.refresh_reports import (
        _load_json,
        _load_manifest,
        _record_path_from_run_manifest,
        _record_paths_from_run_index,
        _resolve_paths,
    )
except ImportError:  # pragma: no cover - direct script execution.
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from evaluation.reporting.publication.build_publication_runset import _case_meta
    from evaluation.reporting.current.refresh_reports import (
        _load_json,
        _load_manifest,
        _record_path_from_run_manifest,
        _record_paths_from_run_index,
        _resolve_paths,
    )


DEFAULT_MODES: list[dict[str, str]] = [
    {"mode": "skillclaw-inline-guarded", "expected_provider": "skillclaw"},
    {"mode": "direct-deepseek-guarded", "expected_provider": "deepseek"},
]


def _repo_root_from_manifest(path: Path) -> Path:
    resolved = path.resolve()
    parent = resolved.parent
    if parent.name == "publication" and parent.parent.name == "reports":
        return parent.parent.parent
    if parent.name == "reports":
        return parent.parent
    return resolved.parents[1]


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
        if not record_path.is_file():
            continue
        case_id = _record_case_id(record_path)
        if case_id and case_id not in ids:
            ids.append(case_id)
    return ids


def _collect_case_ids(source_manifest_path: Path) -> list[str]:
    manifest = _load_manifest(source_manifest_path)
    base_dir = source_manifest_path.parent
    case_ids: list[str] = []

    for manifest_path in _resolve_paths(list(manifest.get("manifests") or []), base_dir):
        case_id = _manifest_case_id(manifest_path)
        if case_id and case_id not in case_ids:
            case_ids.append(case_id)

    for record_path in _resolve_paths(list(manifest.get("records") or []), base_dir):
        case_id = _record_case_id(record_path)
        if case_id and case_id not in case_ids:
            case_ids.append(case_id)

    for run_index_path in _resolve_paths(list(manifest.get("run_indexes") or []), base_dir):
        for case_id in _run_index_case_ids(run_index_path):
            if case_id not in case_ids:
                case_ids.append(case_id)

    return case_ids


def _publication_case_ids(source_manifest_path: Path) -> tuple[list[str], Path]:
    repo_root = _repo_root_from_manifest(source_manifest_path)
    selected: list[str] = []
    for case_id in _collect_case_ids(source_manifest_path):
        meta = _case_meta(case_id, repo_root)
        benchmark = meta.get("benchmark") if isinstance(meta.get("benchmark"), dict) else {}
        if bool(benchmark.get("publication_ready") or benchmark.get("paper_ready")):
            selected.append(case_id)
    return selected, repo_root


def build_publication_compare_manifest(
    source_manifest_path: Path,
    out_path: Path,
    *,
    output_dir: str = "reports/publication/generated/compare_runs",
    final_records: str = "reports/publication/generated/compare_runs/run_records.jsonl",
    timeout_seconds: int = 2700,
    preflight: bool = True,
    expected_skill_count: int | None = 35,
) -> dict[str, Any]:
    case_ids, repo_root = _publication_case_ids(source_manifest_path)
    manifest_dir = out_path.parent.resolve()

    runs: list[dict[str, Any]] = []
    for case_id in case_ids:
        case_rel = Path("..") / "benchmarks" / "cases" / f"{case_id}.json"
        for mode_spec in DEFAULT_MODES:
            runs.append(
                {
                    "case": case_rel.as_posix(),
                    "mode": mode_spec["mode"],
                    "expected_provider": mode_spec["expected_provider"],
                    "run_id": f"{case_id}-{mode_spec['mode']}-publication-protocol",
                }
            )

    compare_manifest = {
        "name": "publication-compare-protocol-v1",
        "source_manifest": str(source_manifest_path.resolve()),
        "protocol": "paired-publication-compare",
        "description": (
            "Fixed paired comparison manifest for publication-ready cases. "
            "Each case is expanded into one SkillClaw guarded run and one direct guarded baseline run."
        ),
        "case_count": len(case_ids),
        "mode_count": len(DEFAULT_MODES),
        "comparison_modes": DEFAULT_MODES,
        "defaults": {
            "output_dir": output_dir,
            "final_records": final_records,
            "timeout_seconds": timeout_seconds,
            "preflight": preflight,
            "expected_skill_count": expected_skill_count,
        },
        "outputs": {
            "paired_md": "compare.md",
            "paired_csv": "compare.csv",
        },
        "runs": runs,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(compare_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return compare_manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-manifest",
        type=Path,
        default=Path("reports/publication/runset_manifest.json"),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("reports/publication/compare_manifest.json"),
    )
    parser.add_argument("--output-dir", default="reports/publication/generated/compare_runs")
    parser.add_argument("--final-records", default="reports/publication/generated/compare_runs/run_records.jsonl")
    parser.add_argument("--timeout-seconds", type=int, default=2700)
    parser.add_argument("--no-preflight", action="store_true")
    parser.add_argument("--expected-skill-count", type=int, default=35)
    args = parser.parse_args(argv)

    result = build_publication_compare_manifest(
        args.source_manifest.resolve(),
        args.out.resolve(),
        output_dir=args.output_dir,
        final_records=args.final_records,
        timeout_seconds=args.timeout_seconds,
        preflight=not args.no_preflight,
        expected_skill_count=args.expected_skill_count,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


build_compare_manifest = build_publication_compare_manifest





