#!/usr/bin/env python3
"""Extract server-side skill injection audit fields from conversations.jsonl."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def _iter_records(path: Path):
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                yield {"_line_no": line_no, "_error": "invalid_json"}
                continue
            if isinstance(record, dict):
                record["_line_no"] = line_no
                yield record


def _pick(record: dict[str, Any]) -> dict[str, Any]:
    injection = record.get("skill_injection") if isinstance(record.get("skill_injection"), dict) else {}
    return {
        "line_no": record.get("_line_no"),
        "session_id": record.get("session_id") or record.get("session"),
        "turn_num": record.get("turn_num") or record.get("turn"),
        "timestamp": record.get("timestamp") or record.get("created_at"),
        "injection_mode": record.get("injection_mode") or injection.get("injection_mode"),
        "selected_skill_names": record.get("selected_skill_names") or injection.get("selected_skill_names") or [],
        "skill_prompt_hash": record.get("skill_prompt_hash") or injection.get("skill_prompt_hash"),
        "available_skill_count": record.get("available_skill_count") or injection.get("available_skill_count"),
        "skill_top_k": record.get("skill_top_k") or injection.get("top_k"),
    }


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("records", type=Path, help="Path to records/conversations.jsonl.")
    parser.add_argument("--session-id", default="", help="Filter by session id.")
    parser.add_argument("--last", type=int, default=20, help="Show last N matching records.")
    parser.add_argument("--jsonl-out", type=Path, default=None, help="Optional JSONL output path.")
    args = parser.parse_args(argv)

    rows = []
    for record in _iter_records(args.records):
        if args.session_id and str(record.get("session_id") or record.get("session")) != args.session_id:
            continue
        row = _pick(record)
        if row["selected_skill_names"] or row["injection_mode"] or row["skill_prompt_hash"]:
            rows.append(row)

    rows = rows[-max(1, args.last) :]
    print(json.dumps(rows, ensure_ascii=False, indent=2))
    if args.jsonl_out:
        args.jsonl_out.parent.mkdir(parents=True, exist_ok=True)
        with args.jsonl_out.open("a", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
