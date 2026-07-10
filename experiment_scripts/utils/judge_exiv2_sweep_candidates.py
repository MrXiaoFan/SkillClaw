#!/usr/bin/env python3
"""Rank Exiv2 sweep runs and recommend validator-promotion candidates."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PRIMARY_MARKERS = [
    "EXIV2_JP2_ICC_PATH_OK",
    "EXIV2_ASAN_OOB_OK",
    "TARGET_EXECUTION_RC=",
]

SECONDARY_MARKERS = [
    "AddressSanitizer",
    "Jp2Image::readMetadata",
    "getULong",
]


def _load_rows(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def _score_row(row: dict) -> dict:
    matched = set(row.get("matched_markers") or [])
    primary_hits = [m for m in PRIMARY_MARKERS if m in matched]
    secondary_hits = [m for m in SECONDARY_MARKERS if m in matched]
    returncode = row.get("returncode")
    score = len(primary_hits) * 3 + len(secondary_hits)
    if returncode not in (None, 0):
        score += 1

    if len(primary_hits) == len(PRIMARY_MARKERS) and len(secondary_hits) >= 2:
        decision = "strong_candidate"
    elif len(primary_hits) >= 2 and len(secondary_hits) >= 1:
        decision = "keep_sweeping_nearby"
    elif primary_hits or secondary_hits:
        decision = "weak_signal"
    else:
        decision = "no_signal"

    return {
        **row,
        "score": score,
        "primary_hits": primary_hits,
        "secondary_hits": secondary_hits,
        "decision": decision,
    }


def judge_rows(rows: list[dict]) -> list[dict]:
    judged = [_score_row(row) for row in rows]
    judged.sort(
        key=lambda row: (
            row.get("score", 0),
            len(row.get("primary_hits") or []),
            len(row.get("secondary_hits") or []),
        ),
        reverse=True,
    )
    return judged


def render_markdown(rows: list[dict]) -> str:
    lines = [
        "# Exiv2 Sweep Candidate Ranking",
        "",
        f"- Runs judged: `{len(rows)}`",
        "",
        "| rank | label | score | decision | icc_size | colr_method | returncode | primary_hits | secondary_hits |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for idx, row in enumerate(rows, start=1):
        params = row.get("params") or {}
        lines.append(
            "| {rank} | {label} | {score} | {decision} | {icc} | {colr} | {rc} | {primary} | {secondary} |".format(
                rank=idx,
                label=row.get("label", ""),
                score=row.get("score", 0),
                decision=row.get("decision", ""),
                icc=params.get("icc_size", ""),
                colr=params.get("colr_method", ""),
                rc=row.get("returncode", ""),
                primary=", ".join(row.get("primary_hits") or []),
                secondary=", ".join(row.get("secondary_hits") or []),
            )
        )

    if rows:
        best = rows[0]
        params = best.get("params") or {}
        lines.extend(
            [
                "",
                "## Best Current Candidate",
                "",
                f"- label: `{best.get('label', '')}`",
                f"- decision: `{best.get('decision', '')}`",
                f"- score: `{best.get('score', 0)}`",
                f"- icc_size: `{params.get('icc_size', '')}`",
                f"- colr_method: `{params.get('colr_method', '')}`",
                f"- width: `{params.get('width', '')}`",
                f"- height: `{params.get('height', '')}`",
            ]
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("jsonl", type=Path)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--out-json", type=Path, default=None)
    args = parser.parse_args(argv)

    rows = judge_rows(_load_rows(args.jsonl))
    text = render_markdown(rows)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    if args.out_json:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
