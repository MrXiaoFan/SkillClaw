#!/usr/bin/env python3
"""Score one agent output against a SkillClaw experiment case.

The script intentionally stays small and dependency-free so it can run on the
remote VM. It accepts either a JSON answer emitted by the agent or a markdown
transcript and falls back to simple text matching against the case ground truth.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _extract_json_object(text: str) -> dict[str, Any]:
    stripped = text.lstrip("\ufeff").strip()
    if not stripped:
        return {}
    try:
        obj = json.loads(stripped)
        if isinstance(obj, dict) and isinstance(obj.get("result"), str):
            nested = _extract_json_object(obj["result"])
            if nested:
                return nested
        if isinstance(obj, dict) and obj.get("is_error") is True and not obj.get("result"):
            return {"_unscoreable_error": True, "raw_error": obj}
        return obj if isinstance(obj, dict) else {}
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", stripped, re.DOTALL)
    if not match:
        return {}
    try:
        obj = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    text = str(value).strip()
    return [text] if text else []


def _collect_predictions(obj: dict[str, Any], raw_text: str) -> dict[str, list[str]]:
    scoreable_raw_text = "" if obj.get("_unscoreable_error") else raw_text
    return {
        "cves": _as_list(obj.get("predicted_cves") or obj.get("predicted_cve") or obj.get("cve")),
        "files": _as_list(obj.get("predicted_files") or obj.get("predicted_file") or obj.get("file")),
        "functions": _as_list(
            obj.get("predicted_functions") or obj.get("predicted_function") or obj.get("function")
        ),
        "evidence": _as_list(obj.get("evidence") or obj.get("root_cause") or obj.get("analysis")),
        "raw_text": [scoreable_raw_text] if scoreable_raw_text else [],
    }


def _contains_any(haystack_items: list[str], needles: list[str]) -> tuple[bool, list[str]]:
    haystack = "\n".join(haystack_items).lower()
    matched = [needle for needle in needles if str(needle).lower() in haystack]
    return bool(matched), matched


def score_output(case: dict[str, Any], raw_text: str) -> dict[str, Any]:
    obj = _extract_json_object(raw_text)
    predictions = _collect_predictions(obj, raw_text)
    truth = case.get("ground_truth", {})
    weights = case.get("scoring", {}).get("weights", {})
    max_score = float(case.get("scoring", {}).get("max_score", 10))

    checks: dict[str, dict[str, Any]] = {}
    score = 0.0

    cves = [str(cve) for cve in truth.get("cves", [])]
    if cves:
        hit, matched = _contains_any(predictions["cves"] + predictions["raw_text"], cves)
        checks["cve"] = {"hit": hit, "matched": matched, "expected": cves}
        if hit:
            score += float(weights.get("cve", 2))

    files = [str(file) for file in truth.get("files", [])]
    hit, matched = _contains_any(predictions["files"] + predictions["raw_text"], files)
    checks["file"] = {"hit": hit, "matched": matched, "expected": files}
    if hit:
        score += float(weights.get("file", 2))

    functions = [str(func) for func in truth.get("functions", [])]
    hit, matched = _contains_any(predictions["functions"] + predictions["raw_text"], functions)
    checks["function"] = {"hit": hit, "matched": matched, "expected": functions}
    if hit:
        score += float(weights.get("function", 3))

    required_evidence = [str(item) for item in truth.get("required_evidence", [])]
    if required_evidence:
        hit, matched = _contains_any(predictions["evidence"] + predictions["raw_text"], required_evidence)
        checks["evidence"] = {"hit": hit, "matched": matched, "expected": required_evidence}
        if hit:
            score += float(weights.get("evidence", 1))

    root_cause = str(truth.get("root_cause", "") or "")
    if root_cause:
        root_terms = [term for term in re.split(r"[,;，；。.\s]+", root_cause) if len(term) >= 3]
        hit, matched = _contains_any(predictions["evidence"] + predictions["raw_text"], root_terms[:12])
        checks["root_cause"] = {"hit": hit, "matched": matched, "expected_terms": root_terms[:12]}
        if hit:
            score += float(weights.get("root_cause", 2))

    score = round(min(max_score, score), 3)
    return {
        "case_id": case.get("case_id"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "score": score,
        "max_score": max_score,
        "checks": checks,
        "predictions": predictions,
        "agent_json": obj,
    }


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", type=Path, help="Path to experiment case JSON.")
    parser.add_argument("agent_output", type=Path, help="Path to agent output text or JSON.")
    parser.add_argument("--mode", default="", help="Experiment mode, e.g. skillclaw-inline or direct-deepseek.")
    parser.add_argument("--session-id", default="", help="Claude/SkillClaw session id if known.")
    parser.add_argument("--result-out", type=Path, default=None, help="Optional JSONL path to append the result.")
    args = parser.parse_args(argv)

    case = _load_json(args.case)
    raw_text = args.agent_output.read_text(encoding="utf-8-sig", errors="replace")
    result = score_output(case, raw_text)
    if args.mode:
        result["mode"] = args.mode
    if args.session_id:
        result["session_id"] = args.session_id

    line = json.dumps(result, ensure_ascii=False)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.result_out:
        args.result_out.parent.mkdir(parents=True, exist_ok=True)
        with args.result_out.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
