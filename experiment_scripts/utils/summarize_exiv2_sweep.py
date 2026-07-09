#!/usr/bin/env python3
"""Summarize recorded Exiv2 sweep JSONL results into Markdown."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _load_rows(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def render_markdown(rows: list[dict]) -> str:
    lines = [
        "# Exiv2 Sweep Summary",
        "",
        f"- Runs: `{len(rows)}`",
        "",
        "| label | icc_size | colr_method | width | height | returncode | matched_markers |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        params = row.get("params") or {}
        markers = ", ".join(row.get("matched_markers") or [])
        lines.append(
            "| {label} | {icc} | {colr} | {w} | {h} | {rc} | {markers} |".format(
                label=row.get("label", ""),
                icc=params.get("icc_size", ""),
                colr=params.get("colr_method", ""),
                w=params.get("width", ""),
                h=params.get("height", ""),
                rc=row.get("returncode", ""),
                markers=markers,
            )
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("jsonl", type=Path)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    rows = _load_rows(args.jsonl)
    text = render_markdown(rows)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
