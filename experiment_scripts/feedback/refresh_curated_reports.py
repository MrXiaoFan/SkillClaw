#!/usr/bin/env python3
"""Refresh curated experiment reports in a fixed, race-free order."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    from experiment_scripts.feedback.build_skill_feedback_bundle import (
        build_feedback_bundles,
        collect_records as collect_bundle_records,
        write_json as write_bundle_json,
        write_markdown as write_bundle_markdown,
    )
    from experiment_scripts.feedback.build_skill_gate_report import (
        build_gate_report,
        write_json as write_gate_json,
        write_markdown as write_gate_markdown,
    )
    from experiment_scripts.feedback.summarize_results import (
        collect_rows,
        write_csv as write_matrix_csv,
        write_markdown as write_matrix_markdown,
    )
    from experiment_scripts.feedback.summarize_skill_feedback import (
        build_skill_feedback,
        collect_records as collect_feedback_records,
        write_csv as write_feedback_csv,
        write_markdown as write_feedback_markdown,
    )
except ImportError:  # pragma: no cover - direct script execution.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from experiment_scripts.feedback.build_skill_feedback_bundle import (
        build_feedback_bundles,
        collect_records as collect_bundle_records,
        write_json as write_bundle_json,
        write_markdown as write_bundle_markdown,
    )
    from experiment_scripts.feedback.build_skill_gate_report import (
        build_gate_report,
        write_json as write_gate_json,
        write_markdown as write_gate_markdown,
    )
    from experiment_scripts.feedback.summarize_results import (
        collect_rows,
        write_csv as write_matrix_csv,
        write_markdown as write_matrix_markdown,
    )
    from experiment_scripts.feedback.summarize_skill_feedback import (
        build_skill_feedback,
        collect_records as collect_feedback_records,
        write_csv as write_feedback_csv,
        write_markdown as write_feedback_markdown,
    )


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
            path = (base / path).resolve()
        paths.append(path)
    return paths


def _require_paths(paths: list[Path]) -> None:
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        joined = "\n".join(missing)
        raise FileNotFoundError(f"curated record(s) missing:\n{joined}")


def _write_runset_summary(manifest: dict[str, Any], record_paths: list[Path], out_path: Path) -> None:
    lines = [
        "# Curated Runset",
        "",
        f"Manifest: `{manifest.get('name', 'unnamed-runset')}`",
        f"Records: {len(record_paths)}",
        "",
        "## Included Records",
        "",
        "| case_id | mode | score | validation | selected_skills | skill_relevance | record |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for path in record_paths:
        row = collect_rows([path])[0]
        rel = str(row.get("skill_relevance") or "")
        sel = str(row.get("selected_skills") or "")
        lines.append(
            f"| {row.get('case_id','')} | {row.get('mode','')} | {row.get('score_text','')} | "
            f"{row.get('validation','')} | {sel} | {rel} | `{path.as_posix()}` |"
        )
    lines.append("")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def refresh_reports(manifest_path: Path) -> dict[str, Any]:
    manifest = _load_manifest(manifest_path)
    base_dir = manifest_path.parent
    record_paths = _resolve_paths(list(manifest.get("records") or []), base_dir)
    _require_paths(record_paths)

    outputs = manifest.get("outputs") or {}
    matrix_md = (base_dir / outputs["matrix_md"]).resolve()
    matrix_csv = (base_dir / outputs["matrix_csv"]).resolve()
    feedback_md = (base_dir / outputs["feedback_md"]).resolve()
    feedback_csv = (base_dir / outputs["feedback_csv"]).resolve()
    gate_md = (base_dir / outputs["gate_md"]).resolve()
    gate_json = (base_dir / outputs["gate_json"]).resolve()
    bundle_md = (base_dir / outputs["bundle_md"]).resolve()
    bundle_json = (base_dir / outputs["bundle_json"]).resolve()
    runset_md = (base_dir / outputs["runset_md"]).resolve()

    rows = collect_rows(record_paths)
    write_matrix_markdown(rows, matrix_md)
    write_matrix_csv(rows, matrix_csv)

    feedback_records = collect_feedback_records(record_paths)
    feedback_rows = build_skill_feedback(feedback_records)
    write_feedback_markdown(feedback_rows, feedback_md)
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
    write_bundle_markdown(bundles, bundle_md)
    write_bundle_json(bundles, bundle_json)

    _write_runset_summary(manifest, record_paths, runset_md)
    return {
        "records": [str(path) for path in record_paths],
        "outputs": {
            "matrix_md": str(matrix_md),
            "matrix_csv": str(matrix_csv),
            "feedback_md": str(feedback_md),
            "feedback_csv": str(feedback_csv),
            "gate_md": str(gate_md),
            "gate_json": str(gate_json),
            "bundle_md": str(bundle_md),
            "bundle_json": str(bundle_json),
            "runset_md": str(runset_md),
        },
    }


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("experiment_records/curated_skillclaw_runset.json"),
    )
    args = parser.parse_args(argv)

    result = refresh_reports(args.manifest.resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
