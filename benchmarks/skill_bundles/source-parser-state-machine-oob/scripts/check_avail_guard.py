#!/usr/bin/env python3
"""Heuristic checker for parser lookahead reads vs avail guards."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    from evaluation.cases.loader import load_case_definition
except ImportError:  # pragma: no cover - direct script execution.
    sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
    from evaluation.cases.loader import load_case_definition


FUNC_RE_TEMPLATE = r"\b{func}\s*\([^)]*\)\s*\{{"
CUR_RE = re.compile(r"(?:\bin->cur|\bcur|\bbuf)\s*\[\s*(\d+)\s*\]")
AVAIL_RE = re.compile(r"\bavail\s*(?:<|<=)\s*(\d+)")


def _load_case(path: Path | None) -> dict[str, Any]:
    if not path:
        return {}
    return load_case_definition(path)


def _extract_function_body(text: str, func: str) -> str:
    match = re.search(FUNC_RE_TEMPLATE.format(func=re.escape(func)), text)
    if not match:
        return ""
    start = match.end()
    depth = 1
    i = start
    while i < len(text):
        char = text[i]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start:i]
        i += 1
    return text[start:]


def _analyze_body(body: str) -> dict[str, Any]:
    cur_indices = [int(match.group(1)) for match in CUR_RE.finditer(body)]
    avail_guards = [int(match.group(1)) for match in AVAIL_RE.finditer(body)]
    max_cur_index = max(cur_indices) if cur_indices else None
    max_required_avail = max_cur_index + 1 if max_cur_index is not None else None
    weakest_guard = min(avail_guards) if avail_guards else None
    suspicious = (
        max_required_avail is not None
        and weakest_guard is not None
        and weakest_guard < max_required_avail
    )
    return {
        "cur_indices": sorted(set(cur_indices)),
        "avail_guards": sorted(set(avail_guards)),
        "max_cur_index": max_cur_index,
        "max_required_avail": max_required_avail,
        "weakest_avail_guard": weakest_guard,
        "suspicious": suspicious,
    }


def run(case: dict[str, Any], root: Path) -> dict[str, Any]:
    truth = case.get("ground_truth", {}) if isinstance(case.get("ground_truth"), dict) else {}
    files = [str(item) for item in truth.get("files", [])] or ["HTMLparser.c"]
    functions = [str(item) for item in truth.get("functions", [])] or ["htmlParseTryOrFinish"]

    findings: list[dict[str, Any]] = []
    for rel_file in files:
        path = root / rel_file
        if not path.is_file():
            findings.append({"file": rel_file, "status": "missing"})
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for func in functions:
            body = _extract_function_body(text, func)
            if not body:
                findings.append({"file": rel_file, "function": func, "status": "function_not_found"})
                continue
            analysis = _analyze_body(body)
            findings.append(
                {
                    "file": rel_file,
                    "function": func,
                    "status": "passed" if analysis["suspicious"] else "partial",
                    "analysis": analysis,
                    "evidence": {
                        "mentions_cur_2": "cur[2]" in body or "in->cur[2]" in body,
                        "mentions_cur_3": "cur[3]" in body or "in->cur[3]" in body,
                        "mentions_avail": "avail" in body,
                    },
                }
            )

    suspicious = [item for item in findings if item.get("analysis", {}).get("suspicious")]
    status = "passed" if suspicious else "partial" if findings else "failed"
    return {
        "status": status,
        "checker": "check_avail_guard",
        "summary": "Detected lookahead reads that exceed an observed avail guard." if suspicious else "No clear avail/lookahead mismatch detected by heuristic.",
        "findings": findings,
    }


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", type=Path, default=None)
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args(argv)

    result = run(_load_case(args.case), args.root.expanduser().resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] in {"passed", "partial"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
