#!/usr/bin/env python3
"""Finalize a pulled experiment record with injection audit and optional compare output."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    from experiment_scripts.attach_skill_injection import _load_json, attach_injection
    from experiment_scripts.build_result_record import _load_optional_json
    from experiment_scripts.compare_experiment_records import compare_records, render_markdown
except ImportError:  # pragma: no cover - direct script execution.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from experiment_scripts.attach_skill_injection import _load_json, attach_injection
    from experiment_scripts.build_result_record import _load_optional_json
    from experiment_scripts.compare_experiment_records import compare_records, render_markdown


def _default_finalized_out(path: Path) -> Path:
    if path.stem.endswith("-with-injection"):
        return path
    return path.with_name(f"{path.stem}-with-injection{path.suffix}")


def _default_compare_json_out(path: Path) -> Path:
    if path.stem.endswith("-with-injection"):
        return path.with_name(f"{path.stem[:-15]}-compare.json")
    return path.with_name(f"{path.stem}-compare.json")


def _default_compare_md_out(path: Path) -> Path:
    if path.stem.endswith("-with-injection"):
        return path.with_name(f"{path.stem[:-15]}-compare.md")
    return path.with_name(f"{path.stem}-compare.md")


def finalize_record(
    *,
    case: dict[str, Any],
    final_record: dict[str, Any],
    injection_value: Any,
    session_id: str = "",
) -> dict[str, Any]:
    return attach_injection(
        final_record=final_record,
        case=case,
        injection_value=injection_value,
        session_id=session_id,
    )


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", type=Path)
    parser.add_argument("final_record", type=Path)
    parser.add_argument("injection_json", type=Path)
    parser.add_argument("--session-id", default="")
    parser.add_argument("--out", type=Path, default=None, help="Output path for finalized record.")
    parser.add_argument("--before", type=Path, default=None, help="Optional baseline record to compare against.")
    parser.add_argument("--compare-json-out", type=Path, default=None)
    parser.add_argument("--compare-md-out", type=Path, default=None)
    args = parser.parse_args(argv)

    case = _load_json(args.case)
    final_record = _load_json(args.final_record)
    injection_value = _load_optional_json(args.injection_json)
    finalized = finalize_record(
        case=case,
        final_record=final_record,
        injection_value=injection_value,
        session_id=args.session_id,
    )

    out_path = args.out or _default_finalized_out(args.final_record)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(finalized, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.before:
        before = _load_json(args.before)
        compare = compare_records(before, finalized)
        compare_json_out = args.compare_json_out or _default_compare_json_out(out_path)
        compare_md_out = args.compare_md_out or _default_compare_md_out(out_path)
        compare_json_out.parent.mkdir(parents=True, exist_ok=True)
        compare_json_out.write_text(json.dumps(compare, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        compare_md_out.parent.mkdir(parents=True, exist_ok=True)
        compare_md_out.write_text(render_markdown(compare) + "\n", encoding="utf-8")

    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
