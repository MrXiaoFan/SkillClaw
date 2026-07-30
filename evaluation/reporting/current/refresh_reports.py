#!/usr/bin/env python3
"""Refresh current runset reports in a fixed, race-free order."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    from evaluation.cases.loader import load_case_definition
    from evaluation.reporting.feedback.build_feedback_bundle import (
        build_feedback_bundles,
        collect_records as collect_bundle_records,
        write_json as write_bundle_json,
        write_markdown as write_bundle_markdown,
    )
    from evaluation.reporting.feedback.build_gate_report import (
        build_gate_report,
        write_json as write_gate_json,
        write_markdown as write_gate_markdown,
    )
    from evaluation.reporting.current.build_result_matrix import (
        collect_rows,
        write_csv as write_matrix_csv,
        write_markdown as write_matrix_markdown,
    )
    from evaluation.reporting.feedback.build_skill_summary import (
        build_skill_feedback,
        collect_records as collect_feedback_records,
        write_csv as write_feedback_csv,
        write_markdown as write_feedback_markdown,
    )
except ImportError:  # pragma: no cover - direct script execution.
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from evaluation.cases.loader import load_case_definition
    from evaluation.reporting.feedback.build_feedback_bundle import (
        build_feedback_bundles,
        collect_records as collect_bundle_records,
        write_json as write_bundle_json,
        write_markdown as write_bundle_markdown,
    )
    from evaluation.reporting.feedback.build_gate_report import (
        build_gate_report,
        write_json as write_gate_json,
        write_markdown as write_gate_markdown,
    )
    from evaluation.reporting.current.build_result_matrix import (
        collect_rows,
        write_csv as write_matrix_csv,
        write_markdown as write_matrix_markdown,
    )
    from evaluation.reporting.feedback.build_skill_summary import (
        build_skill_feedback,
        collect_records as collect_feedback_records,
        write_csv as write_feedback_csv,
        write_markdown as write_feedback_markdown,
    )


def _repo_root_from_manifest(path: Path) -> Path:
    resolved = path.resolve()
    parent = resolved.parent
    if parent.name == "publication" and parent.parent.name == "reports":
        return parent.parent.parent
    if parent.parent.name == "reports":
        return parent.parent.parent
    if parent.name == "reports":
        return parent.parent
    return resolved.parents[1]


def _load_manifest(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _resolve_paths(items: list[str], base: Path) -> list[Path]:
    paths: list[Path] = []
    for item in items:
        path = Path(item)
        if not path.is_absolute():
            candidate = (base / path).resolve()
            if candidate.exists():
                path = candidate
            else:
                fallback = (base.parent / path).resolve()
                path = fallback if fallback.exists() else candidate
        paths.append(path)
    return paths


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))


def _case_metadata_by_case_id(case_id: str, repo_root: Path) -> dict[str, Any]:
    if not case_id:
        return {}
    path = repo_root / "benchmarks" / "cases" / f"{case_id}.json"
    if not path.is_file():
        return {}
    return load_case_definition(path)


def _hydrate_case_defaults(rows: list[dict[str, Any]], repo_root: Path) -> list[dict[str, Any]]:
    hydrated: list[dict[str, Any]] = []
    for row in rows:
        case_meta = _case_metadata_by_case_id(str(row.get("case_id") or ""), repo_root)
        confirmation = case_meta.get("confirmation") if isinstance(case_meta.get("confirmation"), dict) else {}
        if not row.get("confirmation_maturity"):
            row["confirmation_maturity"] = str(confirmation.get("maturity") or "")
        if not row.get("confirmation_current_claim"):
            row["confirmation_current_claim"] = str(confirmation.get("current_claim") or "")
        hydrated.append(row)
    return hydrated


def _record_path_from_run_manifest(path: Path) -> Path | None:
    value = _load_json(path)
    if not isinstance(value, dict):
        return None
    artifacts = value.get("artifacts")
    if not isinstance(artifacts, dict):
        return None
    final_path = artifacts.get("final")
    if not isinstance(final_path, str) or not final_path.strip():
        return None
    return Path(final_path).resolve()


def _record_paths_from_run_index(path: Path) -> list[Path]:
    value = _load_json(path)
    if not isinstance(value, list):
        return []
    paths: list[Path] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        artifacts = item.get("artifacts")
        if not isinstance(artifacts, dict):
            continue
        final_path = artifacts.get("final")
        if not isinstance(final_path, str) or not final_path.strip():
            continue
        paths.append(Path(final_path).resolve())
    return paths


def _repair_record_path(path: Path) -> Path:
    candidate = path.resolve()
    if candidate.is_file():
        return candidate
    name = candidate.name
    if "-final-final-enriched.json" in name:
        repaired = candidate.with_name(name.replace("-final-final-enriched.json", "-final-enriched.json"))
        if repaired.is_file():
            return repaired.resolve()
    return candidate


def _resolve_record_paths(manifest: dict[str, Any], base_dir: Path) -> tuple[list[Path], dict[str, dict[str, str]]]:
    rows: list[tuple[Path, dict[str, str]]] = []
    for path in _resolve_paths(list(manifest.get("records") or []), base_dir):
        repaired = _repair_record_path(path)
        rows.append((repaired, {"input_type": "record", "input_path": str(path.resolve())}))

    for path in _resolve_paths(list(manifest.get("manifests") or []), base_dir):
        record_path = _record_path_from_run_manifest(path)
        if record_path is not None:
            record_path = _repair_record_path(record_path)
            rows.append(
                (
                    record_path,
                    {"input_type": "manifest", "input_path": str(path.resolve())},
                )
            )

    for path in _resolve_paths(list(manifest.get("run_indexes") or []), base_dir):
        for record_path in _record_paths_from_run_index(path):
            record_path = _repair_record_path(record_path)
            rows.append(
                (
                    record_path,
                    {"input_type": "run_index", "input_path": str(path.resolve())},
                )
            )

    seen: set[str] = set()
    record_paths: list[Path] = []
    sources: dict[str, dict[str, str]] = {}
    for record_path, source in rows:
        key = str(record_path.resolve())
        if key in seen:
            continue
        seen.add(key)
        record_paths.append(record_path.resolve())
        sources[key] = source
    return record_paths, sources


def _require_paths(paths: list[Path]) -> None:
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        joined = "\n".join(missing)
        raise FileNotFoundError(f"current runset record(s) missing:\n{joined}")


def _display_path(path: str | Path, *bases: Path) -> str:
    value = Path(path)
    if not value.as_posix():
        return ""
    resolved = value.resolve() if value.is_absolute() else value
    for base in bases:
        try:
            return resolved.relative_to(base.resolve()).as_posix()
        except ValueError:
            continue
    return resolved.as_posix()


def _write_runset_summary(
    manifest: dict[str, Any],
    record_paths: list[Path],
    record_sources: dict[str, dict[str, str]],
    out_path: Path,
) -> None:
    repo_root = _repo_root_from_manifest(out_path)
    report_dir = out_path.parent.resolve()
    lines = [
        "# 当前 Runset",
        "",
        f"清单名：`{manifest.get('name', 'unnamed-runset')}`",
        f"用途：`{manifest.get('runset_purpose', 'unspecified')}`",
        f"是否仅论文子集：`{bool(manifest.get('publication_only', False))}`",
        f"记录数：{len(record_paths)}",
        "",
    ]
    eligibility_note = str(manifest.get("eligibility_note") or "").strip()
    if eligibility_note:
        lines.extend(
            [
                "## 适用性说明",
                "",
                eligibility_note,
                "",
            ]
        )
    lines.extend(
        [
            "## 收录记录",
            "",
            "| case_id | mode | score | validation | confirmation | benchmark_maturity | benchmark_tier | publication_ready | source_type | source_path | selected_skills | skill_relevance | record |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for path in record_paths:
        row = collect_rows([path])[0]
        case_meta = _case_metadata_by_case_id(str(row.get("case_id") or ""), repo_root)
        benchmark = case_meta.get("benchmark") if isinstance(case_meta.get("benchmark"), dict) else {}
        case_confirmation = case_meta.get("confirmation") if isinstance(case_meta.get("confirmation"), dict) else {}
        rel = str(row.get("skill_relevance") or "")
        sel = str(row.get("selected_skills") or "")
        conf = str(row.get("confirmation_maturity") or case_confirmation.get("maturity") or "")
        bench_maturity = str(benchmark.get("maturity") or "")
        bench_tier = str(benchmark.get("benchmark_tier") or "")
        publication_ready = str(bool((benchmark.get("publication_ready") or benchmark.get("paper_ready")) if benchmark else False))
        source = record_sources.get(str(path.resolve()), {})
        input_type = str(source.get("input_type") or "")
        input_path = str(source.get("input_path") or "")
        display_input_path = _display_path(input_path, repo_root, report_dir) if input_path else ""
        display_record_path = _display_path(path, repo_root, report_dir)
        lines.append(
            f"| {row.get('case_id','')} | {row.get('mode','')} | {row.get('score_text','')} | "
            f"{row.get('validation','')} | {conf} | {bench_maturity} | {bench_tier} | {publication_ready} | "
            f"{input_type} | `{display_input_path}` | "
            f"{sel} | {rel} | `{display_record_path}` |"
        )
    lines.append("")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def refresh_reports(manifest_path: Path) -> dict[str, Any]:
    manifest = _load_manifest(manifest_path)
    base_dir = manifest_path.parent
    repo_root = _repo_root_from_manifest(manifest_path)
    record_paths, record_sources = _resolve_record_paths(manifest, base_dir)
    _require_paths(record_paths)

    outputs = manifest.get("outputs") or {}
    matrix_md = (base_dir / outputs["matrix_md"]).resolve()
    matrix_csv = (base_dir / outputs["matrix_csv"]).resolve() if outputs.get("matrix_csv") else None
    feedback_md = (base_dir / outputs["feedback_md"]).resolve()
    feedback_csv = (base_dir / outputs["feedback_csv"]).resolve() if outputs.get("feedback_csv") else None
    gate_md = (base_dir / outputs["gate_md"]).resolve()
    gate_json = (base_dir / outputs["gate_json"]).resolve()
    bundle_md = (base_dir / outputs["bundle_md"]).resolve() if outputs.get("bundle_md") else None
    bundle_json = (base_dir / outputs["bundle_json"]).resolve()
    runset_md = (base_dir / outputs["runset_md"]).resolve()

    rows = _hydrate_case_defaults(collect_rows(record_paths), repo_root)
    write_matrix_markdown(rows, matrix_md)
    if matrix_csv is not None:
        write_matrix_csv(rows, matrix_csv)

    feedback_records = collect_feedback_records(record_paths)
    feedback_rows = build_skill_feedback(feedback_records)
    write_feedback_markdown(feedback_rows, feedback_md)
    if feedback_csv is not None:
        write_feedback_csv(feedback_rows, feedback_csv)

    gate_rows = build_gate_report(
        feedback_rows,
        min_samples=int(manifest.get("min_samples", 2)),
        promote_samples=int(manifest.get("promote_samples", 3)),
    )
    write_gate_markdown(gate_rows, gate_md)
    write_gate_json(gate_rows, gate_json)

    bundle_records = collect_bundle_records(record_paths)
    bundles = build_feedback_bundles(bundle_records, gate_map={item["skill"]: item for item in gate_rows})
    if bundle_md is not None:
        write_bundle_markdown(bundles, bundle_md)
    write_bundle_json(bundles, bundle_json)

    _write_runset_summary(manifest, record_paths, record_sources, runset_md)
    result = {
        "records": [str(path) for path in record_paths],
        "record_sources": {path: source for path, source in record_sources.items()},
        "outputs": {
            "matrix_md": str(matrix_md),
            "feedback_md": str(feedback_md),
            "gate_md": str(gate_md),
            "gate_json": str(gate_json),
            "bundle_json": str(bundle_json),
            "runset_md": str(runset_md),
        },
    }
    if matrix_csv is not None:
        result["outputs"]["matrix_csv"] = str(matrix_csv)
    if feedback_csv is not None:
        result["outputs"]["feedback_csv"] = str(feedback_csv)
    if bundle_md is not None:
        result["outputs"]["bundle_md"] = str(bundle_md)
    return result


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("reports/current/runset_manifest.json"),
    )
    args = parser.parse_args(argv)

    result = refresh_reports(args.manifest.resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


