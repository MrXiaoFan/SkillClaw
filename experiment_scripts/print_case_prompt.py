#!/usr/bin/env python3
"""Print the recommended prompt for a benchmark case and experiment mode."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


MODE_TO_PROMPT_KEY = {
    "skillclaw": "recommended_skillclaw",
    "skillclaw-inline": "recommended_skillclaw",
    "skillclaw-inline-default": "recommended_skillclaw",
    "skillclaw-inline-guarded": "recommended_skillclaw",
    "skillclaw-inline-named-skill": "recommended_skillclaw",
    "direct": "recommended_direct",
    "direct-deepseek": "recommended_direct",
    "direct-deepseek-guarded": "recommended_direct",
}

FINAL_ANSWER_GUARD = """

Experiment execution constraints:
- Do not use TodoWrite or other task-list tools.
- Use at most 8 tool calls. Prefer targeted Grep/Read/Bash commands over broad full-project scans.
- As soon as you have a plausible file, function, root cause, and evidence, stop calling tools and produce the final answer.
- If you are uncertain, still output the best-supported JSON instead of continuing tool use.
- The final response must be exactly one JSON object with keys: predicted_cves, predicted_files, predicted_functions, root_cause, evidence, confidence.
""".strip()


def load_case(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))


def _should_apply_guard(mode: str) -> bool:
    return str(mode or "").endswith("-guarded")


def get_case_prompt(case: dict[str, Any], mode: str) -> str:
    prompts = case.get("prompt", {}) if isinstance(case.get("prompt"), dict) else {}
    key = MODE_TO_PROMPT_KEY.get(mode, mode)
    prompt = str(prompts.get(key, "") or "").strip()
    if prompt:
        if _should_apply_guard(mode):
            return f"{prompt}\n\n{FINAL_ANSWER_GUARD}"
        return prompt

    available = ", ".join(sorted(str(item) for item in prompts))
    raise ValueError(f"no prompt found for mode={mode!r}; available prompt keys: {available or '(none)'}")


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", type=Path, help="Path to experiment case JSON.")
    parser.add_argument("--mode", default="skillclaw-inline", help="Experiment mode or exact prompt key.")
    parser.add_argument("--json", action="store_true", help="Print a JSON object instead of plain text.")
    args = parser.parse_args(argv)

    case = load_case(args.case)
    prompt = get_case_prompt(case, args.mode)
    if args.json:
        print(
            json.dumps(
                {
                    "case_id": case.get("case_id"),
                    "mode": args.mode,
                    "prompt": prompt,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(prompt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
