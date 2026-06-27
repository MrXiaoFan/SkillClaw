#!/usr/bin/env python3
"""Create a portable experiment framework zip with POSIX paths.

PowerShell `Compress-Archive` stores Windows backslashes in entry names.  Python's
zip extractor on Linux treats those as literal characters, so remote VM
extraction does not create directories.  This packager normalizes every archive
name to POSIX `/` separators.
"""

from __future__ import annotations

import argparse
import zipfile
from datetime import datetime
from pathlib import Path


DEFAULT_ITEMS = [
    Path("experiment_cases"),
    Path("experiment_scripts"),
    Path("experiment_validation"),
    Path("tests/test_experiment_scripts.py"),
    Path("experiment_records/README.md"),
    Path("experiment_records/dev_notes_20260627.md"),
    Path("experiment_records/experiment_report_20260615_20260621.md"),
    Path("experiment_records/libxml2_deepseek_vs_skillclaw_20260623.md"),
    Path("experiment_records/tcpdump_skillclaw_unified_20260623.md"),
    Path("experiment_records/tcpdump_deepseek_vs_skillclaw_20260623.md"),
    Path("experiment_records/tcpdump_guarded_clean_comparison_20260625.md"),
    Path("experiment_records/libxml2_guarded_clean_comparison_20260625.md"),
    Path("experiment_records/experiment_matrix_20260625.md"),
    Path("experiment_records/experiment_matrix_20260625.csv"),
    Path("experiment_records/scoring_rubric.md"),
]


def should_include(path: Path) -> bool:
    parts = set(path.parts)
    if "__pycache__" in parts:
        return False
    if path.suffix == ".pyc":
        return False
    return True


def iter_files(items: list[Path]) -> list[Path]:
    files: list[Path] = []
    for item in items:
        if item.is_dir():
            files.extend(path for path in item.rglob("*") if path.is_file() and should_include(path))
        elif item.is_file() and should_include(item):
            files.append(item)
    return sorted(files)


def package(output: Path, items: list[Path]) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in iter_files(items):
            archive.write(path, path.as_posix())
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    default_name = f"skillclaw-experiment-framework-{datetime.now():%Y%m%d-%H%M%S}.zip"
    parser.add_argument("--out", type=Path, default=Path("experiment_records") / default_name)
    args = parser.parse_args()

    output = package(args.out, DEFAULT_ITEMS)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
