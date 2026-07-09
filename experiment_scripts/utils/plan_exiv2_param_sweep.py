#!/usr/bin/env python3
"""Generate a parameter-sweep plan for the Exiv2 JP2/ICC-profile candidate."""

from __future__ import annotations

import argparse
import itertools
import json
import sys
from pathlib import Path
from typing import Any


def _load_case(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))


def _parse_csv_ints(text: str) -> list[int]:
    values: list[int] = []
    for item in str(text or "").split(","):
        item = item.strip()
        if not item:
            continue
        values.append(int(item))
    return values


def _command_for_combo(*, root: str, icc_size: int, colr_method: int, width: int, height: int) -> str:
    env_prefix = " ".join(
        [
            f"EXIV2_ICC_SIZE={icc_size}",
            f"EXIV2_COLR_METHOD={colr_method}",
            f"EXIV2_JP2_WIDTH={width}",
            f"EXIV2_JP2_HEIGHT={height}",
        ]
    )
    return "\n".join(
        [
            f"cd {root}",
            f"{env_prefix} bash ../experiment_cases/pocs/exiv2-0.26-cve-2017-17725/prepare_artifacts.sh",
            "bash artifacts/run_exiv2_poc.sh > artifacts/exiv2-sweep.stdout 2> artifacts/exiv2-sweep.stderr",
            "grep -E \"EXIV2_JP2_ICC_PATH_OK|EXIV2_ASAN_OOB_OK|TARGET_EXECUTION_RC=|AddressSanitizer|Jp2Image::readMetadata|getULong\" artifacts/exiv2-sweep.stderr || true",
        ]
    )


def render_plan(
    case: dict[str, Any],
    *,
    case_path: Path,
    root_override: str | None,
    icc_sizes: list[int],
    colr_methods: list[int],
    widths: list[int],
    heights: list[int],
) -> str:
    case_id = str(case.get("case_id") or case_path.stem)
    target = case.get("target") if isinstance(case.get("target"), dict) else {}
    root = root_override or str(target.get("source_root") or ".")
    combos = list(itertools.product(icc_sizes, colr_methods, widths, heights))

    lines = [
        f"# Exiv2 Sweep Plan: {case_id}",
        "",
        f"- Root: `{root}`",
        f"- Total combinations: `{len(combos)}`",
        "- Primary markers to watch:",
        "  - `EXIV2_JP2_ICC_PATH_OK`",
        "  - `EXIV2_ASAN_OOB_OK`",
        "  - `TARGET_EXECUTION_RC=`",
        "  - `AddressSanitizer`",
        "  - `Jp2Image::readMetadata`",
        "  - `getULong`",
        "",
        "## Sweep Matrix",
        "",
        "| idx | icc_size | colr_method | width | height |",
        "| --- | --- | --- | --- | --- |",
    ]
    for idx, (icc_size, colr_method, width, height) in enumerate(combos, start=1):
        lines.append(f"| {idx} | {icc_size} | {colr_method} | {width} | {height} |")

    lines.extend(
        [
            "",
            "## Suggested Commands",
            "",
        ]
    )
    for idx, (icc_size, colr_method, width, height) in enumerate(combos, start=1):
        lines.extend(
            [
                f"### Combo {idx}",
                "",
                "```bash",
                _command_for_combo(
                    root=root,
                    icc_size=icc_size,
                    colr_method=colr_method,
                    width=width,
                    height=height,
                ),
                "```",
                "",
            ]
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", type=Path, help="Path to exiv2 case JSON.")
    parser.add_argument("--root", default=None, help="Optional override for target source root.")
    parser.add_argument("--icc-sizes", default="4,5,6,7,8,12", help="Comma-separated ICC payload sizes.")
    parser.add_argument("--colr-methods", default="2", help="Comma-separated colr method values.")
    parser.add_argument("--widths", default="1", help="Comma-separated width values.")
    parser.add_argument("--heights", default="1", help="Comma-separated height values.")
    parser.add_argument("--out", type=Path, default=None, help="Optional path to write the generated Markdown.")
    args = parser.parse_args(argv)

    case = _load_case(args.case)
    text = render_plan(
        case,
        case_path=args.case,
        root_override=args.root,
        icc_sizes=_parse_csv_ints(args.icc_sizes),
        colr_methods=_parse_csv_ints(args.colr_methods),
        widths=_parse_csv_ints(args.widths),
        heights=_parse_csv_ints(args.heights),
    )
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
