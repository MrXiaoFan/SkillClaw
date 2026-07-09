#!/usr/bin/env python3
"""Record one Exiv2 JP2/ICC sweep attempt as JSONL."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


MARKERS = [
    "EXIV2_JP2_ICC_PATH_OK",
    "EXIV2_ASAN_OOB_OK",
    "TARGET_EXECUTION_RC=",
    "AddressSanitizer",
    "Jp2Image::readMetadata",
    "getULong",
]


def _tail(text: str, limit: int = 4000) -> str:
    return text[-limit:] if len(text) > limit else text


def _load_text(path: Path | None) -> str:
    if not path or not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def build_record(
    *,
    icc_size: int,
    colr_method: int,
    width: int,
    height: int,
    stdout_text: str,
    stderr_text: str,
    returncode: int | None,
    label: str,
) -> dict:
    combined = f"{stdout_text}\n{stderr_text}"
    combined_lower = combined.lower()
    matched = [marker for marker in MARKERS if marker.lower() in combined_lower]
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "label": label,
        "params": {
            "icc_size": icc_size,
            "colr_method": colr_method,
            "width": width,
            "height": height,
        },
        "returncode": returncode,
        "matched_markers": matched,
        "stdout_tail": _tail(stdout_text),
        "stderr_tail": _tail(stderr_text),
    }


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--icc-size", type=int, required=True)
    parser.add_argument("--colr-method", type=int, required=True)
    parser.add_argument("--width", type=int, default=1)
    parser.add_argument("--height", type=int, default=1)
    parser.add_argument("--stdout-file", type=Path, default=None)
    parser.add_argument("--stderr-file", type=Path, default=None)
    parser.add_argument("--returncode", type=int, default=None)
    parser.add_argument("--label", default="exiv2-sweep")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    record = build_record(
        icc_size=args.icc_size,
        colr_method=args.colr_method,
        width=args.width,
        height=args.height,
        stdout_text=_load_text(args.stdout_file),
        stderr_text=_load_text(args.stderr_file),
        returncode=args.returncode,
        label=args.label,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(json.dumps(record, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
