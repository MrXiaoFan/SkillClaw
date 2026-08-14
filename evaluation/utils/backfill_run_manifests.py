#!/usr/bin/env python3
"""Backfill run manifests and directory indexes from existing final records."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _infer_run_id(record_path: Path, record: dict[str, Any]) -> str:
    run_id = str(record.get("run_id") or "").strip()
    if run_id:
        return run_id
    name = record_path.name
    for suffix in ("-final-enriched.json", "-final-with-injection.json", "-final.json"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return record_path.stem


def _normalize_artifacts(record_path: Path, record: dict[str, Any], run_id: str) -> dict[str, str]:
    artifacts = record.get("artifacts") if isinstance(record.get("artifacts"), dict) else {}
    output_dir = record_path.parent.resolve()
    result = {str(key): str(value) for key, value in artifacts.items() if isinstance(value, str) and value.strip()}
    result["final"] = str(record_path.resolve())
    result.setdefault("manifest", str((output_dir / "manifest.json").resolve()))
    result.setdefault("run_index", str((output_dir / "run_index.json").resolve()))
    return result


def build_manifest_from_final_record(record_path: Path) -> dict[str, Any]:
    record = _load_json(record_path)
    if not isinstance(record, dict):
        raise ValueError(f"{record_path} must contain a JSON object")
    run = record.get("run") if isinstance(record.get("run"), dict) else {}
    confirmation = record.get("confirmation") if isinstance(record.get("confirmation"), dict) else {}
    validation = confirmation if confirmation else (record.get("validation") if isinstance(record.get("validation"), dict) else {})
    skill_relevance = record.get("skill_relevance") if isinstance(record.get("skill_relevance"), dict) else {}
    skill_injection = record.get("skill_injection") if isinstance(record.get("skill_injection"), dict) else {}
    run_id = _infer_run_id(record_path, record)
    artifacts = _normalize_artifacts(record_path, record, run_id)
    return {
        "run_id": run_id,
        "case_id": record.get("case_id") or "",
        "mode": record.get("mode") or "",
        "model": record.get("model") or "",
        "target_root": run.get("target_root") or "",
        "status": run.get("status", ""),
        "agent_ran": run.get("agent_ran", ""),
        "start": run.get("start") or record.get("timestamp") or "",
        "end": run.get("end") or record.get("timestamp") or "",
        "score": record.get("score"),
        "max_score": record.get("max_score"),
        "confirmation_status": validation.get("status") or "",
        "validation_status": validation.get("status") or "",
        "session_id": record.get("session_id") or "",
        "session_id_source": record.get("session_id_source") or "",
        "confirmation_maturity": record.get("confirmation_maturity") or "",
        "confirmation_current_claim": record.get("confirmation_current_claim") or "",
        "skill_relevance": skill_relevance.get("status") or "",
        "selected_skills": skill_injection.get("selected_skill_names") or [],
        "artifacts": artifacts,
    }


def _manifest_candidates(output_dir: Path) -> list[Path]:
    paths: list[Path] = []
    direct = output_dir / "manifest.json"
    if direct.is_file():
        paths.append(direct)
    paths.extend(sorted(output_dir.glob("*-manifest.json")))
    return paths


def _refresh_directory_index(output_dir: Path) -> Path:
    rows: list[dict[str, Any]] = []
    for path in _manifest_candidates(output_dir):
        try:
            value = _load_json(path)
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(value, dict):
            rows.append(value)
    rows.sort(key=lambda item: (str(item.get("start") or ""), str(item.get("run_id") or "")), reverse=True)
    index_path = output_dir / "run_index.json"
    _write_json(index_path, rows)
    return index_path


def backfill_run_manifest(record_path: Path) -> Path:
    record_path = record_path.resolve()
    manifest = build_manifest_from_final_record(record_path)
    output_dir = record_path.parent.resolve()
    manifest_path = output_dir / "manifest.json"
    _write_json(manifest_path, manifest)
    _refresh_directory_index(output_dir)
    return manifest_path


def backfill_many(record_paths: list[Path]) -> list[Path]:
    return [backfill_run_manifest(path) for path in record_paths]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("records", nargs="+", type=Path, help="One or more final record JSON files.")
    args = parser.parse_args(argv)

    manifests = backfill_many(args.records)
    print(json.dumps([str(path) for path in manifests], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
