#!/usr/bin/env python3
"""Audit whether reports/runs/confirmations follows the directory-first layout."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


RUN_SIGNAL_SUFFIXES = (
    "-final.json",
    "-final-enriched.json",
    "-final-with-injection.json",
    "-validation.json",
    "-score.json",
    "-prompt.txt",
    ".prompt.txt",
    "-raw.txt",
    "-stderr.txt",
    "-run.meta",
    "-agent.json",
    ".claude.json",
)


def _looks_like_run_file(path: Path) -> bool:
    name = path.name
    return any(name.endswith(suffix) for suffix in RUN_SIGNAL_SUFFIXES)


def _scan_run_directory(path: Path) -> dict[str, Any]:
    files = sorted(child.name for child in path.iterdir() if child.is_file())
    has_final = any(name.endswith(("-final.json", "-final-enriched.json", "-final-with-injection.json")) for name in files)
    has_validation = any(name.endswith("-validation.json") for name in files)
    has_score = any(name.endswith("-score.json") for name in files)
    has_prompt = any(name.endswith("-prompt.txt") for name in files)
    has_manifest = "manifest.json" in files or any(name.endswith("-manifest.json") for name in files)
    has_run_index = "run_index.json" in files
    quality = "complete" if has_final and (has_validation or has_score or has_manifest) else "partial"
    return {
        "name": path.name,
        "type": "run_directory",
        "quality": quality,
        "file_count": len(files),
        "has_final": has_final,
        "has_validation": has_validation,
        "has_score": has_score,
        "has_prompt": has_prompt,
        "has_manifest": has_manifest,
        "has_run_index": has_run_index,
    }


def audit_run_layout(root: Path) -> dict[str, Any]:
    root = root.resolve()
    directories: list[dict[str, Any]] = []
    root_run_files: list[str] = []
    other_files: list[str] = []

    for child in sorted(root.iterdir(), key=lambda item: item.name.lower()):
        if child.is_dir():
            if child.name == "__pycache__":
                continue
            directories.append(_scan_run_directory(child))
            continue
        if _looks_like_run_file(child):
            root_run_files.append(child.name)
        else:
            other_files.append(child.name)

    complete_dirs = sum(1 for item in directories if item["quality"] == "complete")
    partial_dirs = len(directories) - complete_dirs

    return {
        "root": str(root),
        "directory_count": len(directories),
        "complete_run_directories": complete_dirs,
        "partial_run_directories": partial_dirs,
        "root_run_file_count": len(root_run_files),
        "other_file_count": len(other_files),
        "run_directories": directories,
        "root_run_files": root_run_files,
        "other_files": other_files,
    }


def _render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# confirmations Layout Audit",
        "",
        f"- root: `{report['root']}`",
        f"- run directories: `{report['directory_count']}`",
        f"- complete run directories: `{report['complete_run_directories']}`",
        f"- partial run directories: `{report['partial_run_directories']}`",
        f"- root-level run files: `{report['root_run_file_count']}`",
        f"- other files: `{report['other_file_count']}`",
        "",
        "## Run Directories",
        "",
        "| name | quality | files | final | validation | score | manifest | run_index | prompt |",
        "| --- | --- | ---: | --- | --- | --- | --- | --- | --- |",
    ]
    for item in report["run_directories"]:
        lines.append(
            "| {name} | {quality} | {file_count} | {has_final} | {has_validation} | {has_score} | {has_manifest} | {has_run_index} | {has_prompt} |".format(
                **item
            )
        )
    if report["root_run_files"]:
        lines.extend(["", "## Root-Level Run Files", ""])
        lines.extend(f"- `{name}`" for name in report["root_run_files"])
    if report["other_files"]:
        lines.extend(["", "## Other Files", ""])
        lines.extend(f"- `{name}`" for name in report["other_files"])
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("reports/runs/confirmations"),
        help="Directory to audit.",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON instead of Markdown.")
    parser.add_argument("--out", type=Path, help="Optional file to write the audit report to.")
    args = parser.parse_args(argv)

    report = audit_run_layout(args.root)
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n" if args.json else _render_markdown(report)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


