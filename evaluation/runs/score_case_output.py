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

try:
    from evaluation.cases.loader import load_case_definition, normalize_case
except ImportError:  # pragma: no cover - direct script execution from copied folders.
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from evaluation.cases.loader import load_case_definition, normalize_case


def _load_json(path: Path) -> dict[str, Any]:
    return load_case_definition(path)


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


_ROOT_CAUSE_STOP_WORDS = frozenset({
    "the", "and", "for", "with", "that", "this", "from", "into", "via",
    "without", "which", "overflows", "overflow", "buffer", "stack",
    "stack-based", "handler", "parameter", "not", "sanitized", "any",
    "length", "check", "checked", "bounds", "checking", "read", "reads",
    "passes", "using", "used", "uses", "then", "when", "while", "after",
    "before", "during", "through", "allowing", "allows", "can", "may",
    "will", "shall", "must", "should", "would", "could", "has", "have",
    "been", "being", "was", "were", "are", "its", "their", "such",
    "also", "but", "however", "therefore", "thus", "hence", "since",
    "because", "due", "based", "user-provided", "user", "provided",
    "directly", "indirectly", "further", "moreover", "additionally",
    "resulting", "results", "result", "causes", "caused", "cause",
    "executes", "executed", "execute", "execution", "formats", "formatted",
    "format", "command", "commands", "string", "strings", "value",
    "values", "field", "fields", "data", "bytes", "byte", "memory",
    "access", "accesses", "accessed", "accessing", "insufficient",
    "insufficiently", "validated", "validates", "validate", "validation",
    "verified", "verifies", "verify", "verification", "guaranteeing",
    "guarantees", "guarantee", "performs", "performed", "perform",
    "leaves", "leave", "left", "never", "advances", "advance", "advanced",
    "global", "regex", "substitution", "empty-string", "match", "matches",
    "matched", "matching", "name", "zero", "forward", "progress",
    "subsequent", "url", "path", "request", "requests", "response",
    "responses", "http", "post", "body", "header", "headers",
    "function", "functions", "call", "calls", "called", "calling",
    "returns", "returned", "return", "wrapper", "wrappers",
    "system", "sprintf", "vsprintf", "vsnprintf", "strcpy", "strncpy",
    "memcpy", "memset", "malloc", "free", "printf", "fprintf",
    "itself", "they", "them", "these", "those", "each", "both",
    "only", "just", "even", "still", "yet", "now", "here", "there",
    "where", "what", "how", "why", "who", "all", "some", "none",
    "many", "few", "more", "most", "less", "least", "other", "another",
    "same", "different", "new", "old", "first", "last", "next", "previous",
    "following", "above", "below", "upon", "within", "without",
})


def _extract_meaningful_root_terms(text):
    """Extract discriminative terms from a root-cause description.

    Filters out common English stop-words and generic vulnerability jargon
    so that the root_cause scoring dimension actually distinguishes between
    analyses that identify the *specific* vulnerability mechanism and those
    that only produce generic boilerplate.
    """
    raw_terms = re.split(r"[,;\s()]+", text)
    meaningful = []
    seen = set()
    for term in raw_terms:
        cleaned = term.strip().rstrip(".,;:")
        lower = cleaned.lower()
        if len(cleaned) < 4:
            continue
        if lower in _ROOT_CAUSE_STOP_WORDS:
            continue
        if cleaned.replace("-", "").replace(".", "").isdigit():
            continue
        if lower in seen:
            continue
        seen.add(lower)
        meaningful.append(cleaned)
    return meaningful[:20]


def score_output(case: dict[str, Any], raw_text: str) -> dict[str, Any]:
    case = normalize_case(case)
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
    # Also check basename match (e.g. expected "vul_file/wireless.cgi", predicted "wireless.cgi")
    file_basenames = [f.rsplit("/", 1)[-1] for f in files]
    hit, matched = _contains_any(predictions["files"] + predictions["raw_text"], files + file_basenames)
    checks["file"] = {"hit": hit, "matched": matched, "expected": files}
    if hit:
        score += float(weights.get("file", 2))

    functions = [str(func) for func in truth.get("functions", [])]
    # Primary check: model's explicit predicted_functions (strict).
    pred_func_hit, pred_func_matched = _contains_any(predictions["functions"], functions)
    # Secondary check: function name mentioned in raw text (lenient).
    text_func_hit, text_func_matched = _contains_any(predictions["raw_text"], functions)
    func_weight = float(weights.get("function", 3))
    if pred_func_hit:
        checks["function"] = {
            "hit": True,
            "matched": pred_func_matched,
            "expected": functions,
            "match_source": "predicted",
            "predicted_function_hit": True,
        }
        score += func_weight
    elif text_func_hit:
        # Partial credit: the correct function appears in the analysis text
        # but was NOT listed in the model's final predicted_functions.
        # This means the model mentioned the right function in passing but
        # chose a different one as its final answer.
        partial = round(func_weight * 0.5, 3)
        checks["function"] = {
            "hit": True,
            "matched": text_func_matched,
            "expected": functions,
            "match_source": "text_partial",
            "predicted_function_hit": False,
            "partial_credit": partial,
        }
        score += partial
    else:
        checks["function"] = {
            "hit": False,
            "matched": [],
            "expected": functions,
            "match_source": "none",
            "predicted_function_hit": False,
        }

    required_evidence = [str(item) for item in truth.get("required_evidence", [])]
    if required_evidence:
        hit, matched = _contains_any(predictions["evidence"] + predictions["raw_text"], required_evidence)
        checks["evidence"] = {"hit": hit, "matched": matched, "expected": required_evidence}
        if hit:
            score += float(weights.get("evidence", 1))

    root_cause = str(truth.get("root_cause", "") or "")
    if root_cause:
        root_terms = _extract_meaningful_root_terms(root_cause)
        # Require at least 2 meaningful terms to match (not just 1 generic word)
        hit, matched = _contains_any(predictions["evidence"] + predictions["raw_text"], root_terms)
        min_required = min(2, len(root_terms)) if root_terms else 1
        hit = len(matched) >= min_required
        checks["root_cause"] = {
            "hit": hit,
            "matched": matched,
            "expected_terms": root_terms,
            "min_required": min_required,
        }
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
