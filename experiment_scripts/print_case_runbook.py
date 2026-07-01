#!/usr/bin/env python3
"""Print a remote execution runbook for an experiment case.

This helper turns the case schema into a compact operator-facing runbook:
- target/source root
- expected artifacts
- repro/build/run commands
- suggested guarded run_eval_case.py invocations
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_case(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))


def _lines_for_artifacts(case: dict[str, Any]) -> list[str]:
    rows: list[str] = []
    expected = case.get("expected_artifacts")
    if not isinstance(expected, list) or not expected:
        return rows
    rows.append("## Expected Artifacts")
    rows.append("")
    for item in expected:
        if not isinstance(item, dict):
            continue
        path = str(item.get("path") or "").strip()
        artifact_type = str(item.get("type") or "").strip()
        description = str(item.get("description") or "").strip()
        if not path:
            continue
        detail = "; ".join(part for part in (artifact_type, description) if part)
        rows.append(f"- `{path}`" + (f" ({detail})" if detail else ""))
    rows.append("")
    return rows


def _lines_for_repro(case: dict[str, Any]) -> list[str]:
    rows: list[str] = []
    repro = case.get("repro")
    if not isinstance(repro, dict) or not repro:
        return rows
    build = [str(item).strip() for item in repro.get("build") or [] if str(item).strip()]
    run = [str(item).strip() for item in repro.get("run") or [] if str(item).strip()]
    success = [str(item).strip() for item in repro.get("success_markers") or [] if str(item).strip()]
    frames = [str(item).strip() for item in repro.get("target_frames") or [] if str(item).strip()]
    notes = str(repro.get("notes") or "").strip()
    if not any((build, run, success, frames, notes)):
        return rows
    rows.append("## Repro / Confirmation")
    rows.append("")
    if build:
        rows.append("Build:")
        rows.extend(f"- `{item}`" for item in build)
        rows.append("")
    if run:
        rows.append("Run:")
        rows.extend(f"- `{item}`" for item in run)
        rows.append("")
    if success:
        rows.append("Success markers:")
        rows.extend(f"- `{item}`" for item in success)
        rows.append("")
    if frames:
        rows.append("Target frames:")
        rows.extend(f"- `{item}`" for item in frames)
        rows.append("")
    if notes:
        rows.append(f"Notes: {notes}")
        rows.append("")
    return rows


def _run_eval_command(case_path: Path, root: str, output_dir: str, mode: str, provider: str) -> str:
    parts = [
        "python3 experiment_scripts/run_eval_case.py",
        f"  {case_path.as_posix()}",
        f"  --mode {mode}",
        f"  --root {root}",
        f"  --output-dir {output_dir}",
        "  --preflight",
        f"  --expected-provider {provider}",
    ]
    if provider == "skillclaw":
        parts.extend(
            [
                "  --skillclaw-url http://10.12.189.47:30000",
                "  --skillclaw-key sk-skillclaw-lab",
                "  --expected-skill-count 35",
            ]
        )
    return " \\\n".join(parts)


def render_runbook(case: dict[str, Any], *, case_path: Path, root_override: str | None, output_dir: str) -> str:
    case_id = str(case.get("case_id") or case_path.stem)
    target = case.get("target") if isinstance(case.get("target"), dict) else {}
    source_root = root_override or str(target.get("source_root") or ".")

    lines = [
        f"# Runbook: {case_id}",
        "",
        "## Target",
        "",
        f"- Source root: `{source_root}`",
    ]
    project = str(target.get("project") or "").strip()
    version = str(target.get("version") or "").strip()
    if project:
        lines.append(f"- Project: `{project}`" + (f" `{version}`" if version else ""))
    lines.append("")
    lines.extend(_lines_for_artifacts(case))
    lines.extend(_lines_for_repro(case))
    lines.extend(
        [
            "## Suggested Guarded Runs",
            "",
            "SkillClaw:",
            "```bash",
            _run_eval_command(case_path, source_root, output_dir, "skillclaw-inline-guarded", "skillclaw"),
            "```",
            "",
            "Direct baseline:",
            "```bash",
            _run_eval_command(case_path, source_root, output_dir, "direct-deepseek-guarded", "deepseek"),
            "```",
            "",
            "## Notes",
            "",
            "- The guarded modes append execution constraints and now include the confirmation contract from the case schema.",
            "- Recompute `skill_feedback_latest.*` and `skill_feedback_bundle_latest.*` after new final records are produced.",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", type=Path, help="Path to experiment case JSON.")
    parser.add_argument("--root", default=None, help="Optional override for target source root.")
    parser.add_argument("--output-dir", default="~/skillclaw-eval/runs/confirmation-reruns", help="Suggested remote output directory.")
    parser.add_argument("--out", type=Path, default=None, help="Optional path to write the runbook Markdown.")
    args = parser.parse_args(argv)

    case = load_case(args.case)
    text = render_runbook(case, case_path=args.case, root_override=args.root, output_dir=args.output_dir)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
