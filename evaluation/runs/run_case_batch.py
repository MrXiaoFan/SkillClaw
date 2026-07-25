#!/usr/bin/env python3
"""Run a manifest of experiment cases with shared defaults."""

from __future__ import annotations

import argparse
import json
import sys
from argparse import Namespace
from pathlib import Path
from typing import Any

try:
    from evaluation.runs.run_single_case import run_case
except ImportError:  # pragma: no cover - direct script execution.
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from evaluation.runs.run_single_case import run_case


DEFAULT_ARGS: dict[str, Any] = {
    "mode": "skillclaw-inline",
    "root": None,
    "output_dir": "runtime/results",
    "run_id": "",
    "model": "auto",
    "session_id": "",
    "injection_json": None,
    "agent_output": "",
    "no_run_agent": False,
    "claude_cmd": "claude",
    "timeout_seconds": 2700,
    "skip_commands": False,
    "preflight": False,
    "preflight_allow_fail": False,
    "preflight_timeout": 5.0,
    "settings": Path.home() / ".claude" / "settings.json",
    "no_claude_settings": False,
    "expected_provider": None,
    "skillclaw_url": "",
    "skillclaw_key": "",
    "expected_skill_count": None,
    "final_records": "runtime/results/run_records.jsonl",
    "strict_exit": False,
}


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _resolve_path(base_dir: Path, value: Any) -> Any:
    if not isinstance(value, str) or not value.strip():
        return value
    text = value.strip()
    if text.startswith(("http://", "https://")):
        return text
    path = Path(text)
    if path.is_absolute():
        return path
    return (base_dir / path).resolve()


def _merge_args(base_dir: Path, defaults: dict[str, Any], item: dict[str, Any]) -> Namespace:
    merged = dict(DEFAULT_ARGS)
    merged.update(defaults)
    merged.update(item)
    if "case" not in merged:
        raise ValueError("each batch run item must include 'case'")

    for key in ("case", "injection_json", "settings"):
        merged[key] = _resolve_path(base_dir, merged.get(key))
    if merged.get("agent_output"):
        merged["agent_output"] = str(_resolve_path(base_dir, merged["agent_output"]))
    if merged.get("root"):
        merged["root"] = str(_resolve_path(base_dir, merged["root"]))
    if merged.get("output_dir"):
        merged["output_dir"] = str(_resolve_path(base_dir, merged["output_dir"]))
    if merged.get("final_records"):
        merged["final_records"] = str(_resolve_path(base_dir, merged["final_records"]))
    if isinstance(merged.get("case"), Path):
        merged["case"] = merged["case"]
    else:
        merged["case"] = Path(str(merged["case"]))
    return Namespace(**merged)


def run_batch(manifest_path: Path) -> dict[str, Any]:
    manifest = _load_json(manifest_path)
    base_dir = manifest_path.parent
    defaults = manifest.get("defaults") if isinstance(manifest.get("defaults"), dict) else {}
    runs = manifest.get("runs")
    if not isinstance(runs, list) or not runs:
        raise ValueError("manifest must contain a non-empty 'runs' list")

    stop_on_error = bool(manifest.get("stop_on_error"))
    summary_rows: list[dict[str, Any]] = []
    failures = 0
    for index, item in enumerate(runs, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"run item #{index} must be an object")
        args = _merge_args(base_dir, defaults, item)
        try:
            final = run_case(args)
            summary_rows.append(
                {
                    "index": index,
                    "case": str(args.case),
                    "case_id": final.get("case_id"),
                    "mode": final.get("mode"),
                    "score": final.get("score"),
                    "max_score": final.get("max_score"),
                    "validation": (final.get("validation") or {}).get("status"),
                    "final_record": (final.get("artifacts") or {}).get("final"),
                    "status": "ok",
                }
            )
        except Exception as exc:  # pragma: no cover - exercised by CLI behavior.
            failures += 1
            summary_rows.append(
                {
                    "index": index,
                    "case": str(args.case),
                    "mode": getattr(args, "mode", ""),
                    "status": "failed",
                    "error": str(exc),
                }
            )
            if stop_on_error:
                break

    return {
        "manifest": str(manifest_path),
        "run_count": len(summary_rows),
        "failure_count": failures,
        "rows": summary_rows,
    }


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=None, help="Optional batch summary JSON path.")
    args = parser.parse_args(argv)

    summary = run_batch(args.manifest.resolve())
    output = json.dumps(summary, ensure_ascii=False, indent=2)
    print(output)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(output + "\n", encoding="utf-8")
    return 1 if summary.get("failure_count") else 0


if __name__ == "__main__":
    raise SystemExit(main())
