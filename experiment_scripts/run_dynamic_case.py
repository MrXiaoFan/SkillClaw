#!/usr/bin/env python3
"""Run case-level dynamic or semi-dynamic validators.

This CLI is a thin wrapper around `experiment_validation`.  It supports multiple
validator modes through a registry:

- content_match: search the final agent output for ground-truth signals
- source_contains: check source files for required symbols/patterns
- command: run a case-defined shell command
- asan_command: run a PoC/ASan/UBSan command
- bundle_script: execute a script shipped inside a skill bundle
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

try:
    from experiment_validation.runner import run_case_validators
except ImportError:  # pragma: no cover - direct script execution on remote VM.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from experiment_validation.runner import run_case_validators


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))


def _expand_path(path_text: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(path_text)))


def _resolve_root(case: dict[str, Any], override: str | None) -> Path:
    if override:
        return _expand_path(override)
    target = case.get("target", {})
    source_root = str(target.get("source_root", "") or ".")
    return _expand_path(source_root)


def run_validators(
    case: dict[str, Any],
    root: Path,
    *,
    case_path: Path | None = None,
    agent_output_path: Path | None = None,
    skip_commands: bool = False,
) -> dict[str, Any]:
    """Compatibility wrapper used by tests and older scripts."""

    return run_case_validators(
        case,
        root,
        case_path=case_path,
        agent_output_path=agent_output_path,
        skip_commands=skip_commands,
    )


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", type=Path, help="Path to experiment case JSON.")
    parser.add_argument("--root", default=None, help="Override target source root.")
    parser.add_argument("--agent-output", type=Path, default=None, help="Optional final agent output JSON/text.")
    parser.add_argument("--skip-commands", action="store_true", help="Only run non-command validators.")
    parser.add_argument(
        "--strict-exit",
        action="store_true",
        help="Return a non-zero process exit code when the case validation status is failed.",
    )
    parser.add_argument("--result-out", type=Path, default=None, help="Optional JSONL path to append the result.")
    args = parser.parse_args(argv)

    case = _load_json(args.case)
    root = _resolve_root(case, args.root)
    result = run_validators(
        case,
        root,
        case_path=args.case,
        agent_output_path=args.agent_output,
        skip_commands=args.skip_commands,
    )
    line = json.dumps(result, ensure_ascii=False)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.result_out:
        args.result_out.parent.mkdir(parents=True, exist_ok=True)
        with args.result_out.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    if args.strict_exit and result["status"] == "failed":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
