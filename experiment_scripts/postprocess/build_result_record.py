#!/usr/bin/env python3
"""Build one consolidated experiment result record."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from experiment_scripts.execution.score_agent_output import score_output
except ImportError:  # pragma: no cover - used when the file is executed directly.
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from experiment_scripts.execution.score_agent_output import score_output

try:
    from experiment_validation.core import assess_skill_relevance, build_feedback
except ImportError:  # pragma: no cover - direct script execution from copied folders.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from experiment_validation.core import assess_skill_relevance, build_feedback


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))


def _load_optional_json(path: Path | None) -> Any:
    if not path:
        return None
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8-sig", errors="replace").strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        rows = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return rows


def _select_injection(value: Any, session_id: str) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return value
    if not isinstance(value, list):
        return None
    candidates = [item for item in value if isinstance(item, dict)]
    if session_id:
        for item in reversed(candidates):
            if str(item.get("session_id") or "") == session_id:
                return item
    return candidates[-1] if candidates else None


def _select_injection_history(value: Any, session_id: str) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        return [value]
    if not isinstance(value, list):
        return []
    candidates = [item for item in value if isinstance(item, dict)]
    if session_id:
        candidates = [item for item in candidates if str(item.get("session_id") or "") == session_id]
    return candidates


def _select_validation(value: Any, case_id: str) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return value
    if not isinstance(value, list):
        return None
    candidates = [item for item in value if isinstance(item, dict)]
    validation_rows = [item for item in candidates if item.get("validator_mode")]
    if case_id:
        for item in reversed(validation_rows):
            if str(item.get("case_id") or "") == case_id:
                return item
    if validation_rows:
        return validation_rows[-1]
    return candidates[-1] if candidates else None


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", type=Path)
    parser.add_argument("agent_output", type=Path)
    parser.add_argument("--mode", required=True)
    parser.add_argument("--model", default="")
    parser.add_argument("--session-id", default="")
    parser.add_argument("--validation-json", type=Path, default=None)
    parser.add_argument("--injection-json", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=None, help="Optional JSONL output path.")
    args = parser.parse_args(argv)

    case = _load_json(args.case)
    raw_text = args.agent_output.read_text(encoding="utf-8-sig", errors="replace")
    score = score_output(case, raw_text)
    validation = _select_validation(_load_optional_json(args.validation_json), str(case.get("case_id") or ""))
    injection_value = _load_optional_json(args.injection_json)
    injection = _select_injection(injection_value, args.session_id)
    injection_history = _select_injection_history(injection_value, args.session_id)
    selected_skills = []
    if isinstance(injection, dict):
        selected_skills = list(injection.get("selected_skill_names") or [])
    skill_relevance = assess_skill_relevance(case=case, selected_skills=selected_skills)

    record = {
        "case_id": case.get("case_id"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": args.mode,
        "model": args.model,
        "session_id": args.session_id,
        "score": score.get("score"),
        "max_score": score.get("max_score"),
        "checks": score.get("checks"),
        "predictions": score.get("predictions"),
        "skill_injection": injection,
        "skill_injection_history": injection_history,
        "skill_relevance": skill_relevance,
        "validation": validation,
    }
    record["feedback"] = build_feedback(
        score_result=score,
        validation_result=validation,
        skill_injection=injection,
        skill_relevance=skill_relevance,
    )

    line = json.dumps(record, ensure_ascii=False)
    print(json.dumps(record, ensure_ascii=False, indent=2))
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
