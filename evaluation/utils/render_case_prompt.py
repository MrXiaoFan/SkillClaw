#!/usr/bin/env python3
"""Render prompt and guide text from a benchmark case JSON."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

try:
    from evaluation.cases.loader import load_case_definition, resolve_source_root
except ImportError:  # pragma: no cover - direct script execution.
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from evaluation.cases.loader import load_case_definition, resolve_source_root


MODE_TO_PROMPT_KEY = {
    "skillclaw": "recommended_skillclaw",
    "skillclaw-inline": "recommended_skillclaw",
    "skillclaw-inline-default": "recommended_skillclaw",
    "skillclaw-inline-guarded": "recommended_skillclaw",
    "skillclaw-inline-named-skill": "recommended_skillclaw",
    "blind-skillclaw-inline": "recommended_blind_skillclaw",
    "blind-skillclaw-inline-guarded": "recommended_blind_skillclaw",
    "direct": "recommended_direct",
    "direct-deepseek": "recommended_direct",
    "direct-deepseek-guarded": "recommended_direct",
    "blind-direct-deepseek": "recommended_blind_direct",
    "blind-direct-deepseek-guarded": "recommended_blind_direct",
}

FINAL_ANSWER_GUARD = """

Experiment execution constraints:
- Do not use TodoWrite or other task-list tools.
- Use at most 8 tool calls. Prefer targeted Grep/Read/Bash commands over broad full-project scans.
- As soon as you have a plausible file, function, root cause, and evidence, stop calling tools and produce the final answer.
- If you are uncertain, still output the best-supported JSON instead of continuing tool use.
- The final response must be exactly one JSON object with keys: predicted_cves, predicted_files, predicted_functions, root_cause, evidence, confidence.
""".strip()

_WORKSPACE_LABELS = {
    "source_tree": "源码树",
    "firmware_rootfs": "固件或 rootfs",
    "binary_only": "仅二进制",
    "mixed": "源码与二进制混合",
}

_TARGET_COMPONENT_LABELS = {
    "file_parser": "文件解析器",
    "network_parser": "网络协议解析器",
    "firmware_service": "固件服务组件",
    "elf_binary": "ELF 二进制",
    "web_component": "Web 组件",
    "general": "通用组件",
}

_ANALYSIS_MODE_LABELS = {
    "source_analysis": "源码分析",
    "binary_reverse": "二进制逆向",
    "hybrid": "混合分析",
    "full_hunt": "全量排查",
    "dynamic_confirmation": "动态确认",
}

_INPUT_VECTOR_LABELS = {
    "crafted_file": "构造文件输入",
    "crafted_packet": "构造报文输入",
    "network_request": "网络请求输入",
    "local_cli": "本地命令行输入",
    "general": "一般输入",
}


def _task_profile_enabled() -> bool:
    value = str(os.environ.get("SKILLCLAW_ENABLE_TASK_PROFILE", "") or "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def _render_task_profile(case: dict[str, Any]) -> str:
    profile = case.get("task_profile") if isinstance(case.get("task_profile"), dict) else {}
    if not profile:
        return ""

    workspace = str(profile.get("workspace") or "").strip().lower()
    target_component = str(profile.get("target_component") or "").strip().lower()
    analysis_mode = str(profile.get("analysis_mode") or "").strip().lower()
    bug_class = str(profile.get("bug_class") or "").strip()
    input_vector = str(profile.get("input_vector") or "").strip().lower()
    notes = str(profile.get("notes") or "").strip()

    lines = ["Task profile:"]
    if workspace:
        label = _WORKSPACE_LABELS.get(workspace, workspace)
        lines.append(f"- Workspace: `{workspace}` ({label})")
    if target_component:
        label = _TARGET_COMPONENT_LABELS.get(target_component, target_component)
        lines.append(f"- Target component: `{target_component}` ({label})")
    if analysis_mode:
        label = _ANALYSIS_MODE_LABELS.get(analysis_mode, analysis_mode)
        lines.append(f"- Analysis mode: `{analysis_mode}` ({label})")
    if bug_class:
        lines.append(f"- Bug class: `{bug_class}`")
    if input_vector:
        label = _INPUT_VECTOR_LABELS.get(input_vector, input_vector)
        lines.append(f"- Input vector: `{input_vector}` ({label})")

    if workspace == "source_tree":
        lines.append("- Treat this as source-code analysis in a userland source tree.")
        lines.append("- Keep the focus on the userland source tree rather than environment-wide exploration.")
    elif workspace == "firmware_rootfs":
        lines.append("- Treat this as firmware/rootfs analysis rather than a pure userland source task.")

    if target_component in {"file_parser", "network_parser"}:
        lines.append("- Focus on parser control flow, boundary checks, and data-dependent memory access.")

    if analysis_mode == "source_analysis":
        lines.append("- Prefer source-level reasoning over reverse-engineering workflows unless the task explicitly shifts away from source analysis.")
    elif analysis_mode == "binary_reverse":
        lines.append("- Prefer binary-level reasoning; source-only workflows are secondary.")

    if input_vector == "crafted_file":
        lines.append("- Expect the trigger to come from a crafted file or neutral sample already visible in the workspace.")
    elif input_vector == "crafted_packet":
        lines.append("- Expect the trigger to come from a crafted packet, capture, or protocol input already visible in the workspace.")

    if notes:
        lines.append(f"- Notes: {notes}")

    return "\n".join(lines).strip()


def _render_confirmation_contract(case: dict[str, Any]) -> str:
    expected = case.get("expected_artifacts")
    repro = case.get("repro")
    confirmation = case.get("confirmation")
    lines: list[str] = []
    if isinstance(expected, list) and expected:
        lines.extend(
            [
                "Artifact generation requirements:",
            ]
        )
        for item in expected:
            if not isinstance(item, dict):
                continue
            path = str(item.get("path") or "").strip()
            description = str(item.get("description") or "").strip()
            artifact_type = str(item.get("type") or "").strip()
            if not path:
                continue
            suffix = []
            if artifact_type:
                suffix.append(artifact_type)
            if description:
                suffix.append(description)
            detail = f" ({'; '.join(suffix)})" if suffix else ""
            lines.append(f"- Create `{path}`{detail}.")
    if isinstance(repro, dict) and repro:
        build = [str(item).strip() for item in repro.get("build") or [] if str(item).strip()]
        run = [str(item).strip() for item in repro.get("run") or [] if str(item).strip()]
        success = [str(item).strip() for item in repro.get("success_markers") or [] if str(item).strip()]
        frames = [str(item).strip() for item in repro.get("target_frames") or [] if str(item).strip()]
        if build or run or success or frames:
            lines.append("Confirmation / repro targets:")
            if build:
                lines.append("- Be compatible with these build steps:")
                lines.extend(f"  - `{item}`" for item in build)
            if run:
                lines.append("- Be compatible with these run steps:")
                lines.extend(f"  - `{item}`" for item in run)
                lines.append("- If you create a wrapper reproduction script around a crashing target, preserve the target exit status (for example: `status=$?; echo \"Exit code: $status\"; exit $status`).")
            if success:
                lines.append("- Expected success markers:")
                lines.extend(f"  - `{item}`" for item in success)
            if frames:
                lines.append("- Target frames or files to hit:")
                lines.extend(f"  - `{item}`" for item in frames)
    if isinstance(confirmation, dict) and confirmation:
        maturity = str(confirmation.get("maturity") or "").strip()
        current_claim = str(confirmation.get("current_claim") or "").strip()
        target_claim = str(confirmation.get("target_claim") or "").strip()
        accepted_runtime_claim = str(confirmation.get("accepted_runtime_claim") or "").strip()
        confirmed = confirmation.get("confirmed_path") if isinstance(confirmation.get("confirmed_path"), dict) else {}
        blockers = [str(item).strip() for item in confirmation.get("promotion_blockers") or [] if str(item).strip()]
        targets = [str(item).strip() for item in confirmation.get("promotion_targets") or [] if str(item).strip()]
        markers = [str(item).strip() for item in confirmed.get("markers") or [] if str(item).strip()]
        frames = [str(item).strip() for item in confirmed.get("stack_frames") or [] if str(item).strip()]
        summary = str(confirmed.get("summary") or "").strip()
        if maturity or current_claim or target_claim or accepted_runtime_claim or markers or frames or blockers or targets:
            lines.append("Current confirmation state:")
            if maturity:
                lines.append(f"- Current maturity: `{maturity}`")
            if current_claim:
                lines.append(f"- Current confirmed claim: {current_claim}")
            if accepted_runtime_claim:
                lines.append(f"- Accepted runtime claim: {accepted_runtime_claim}")
            if target_claim:
                lines.append(f"- Promotion target: {target_claim}")
            if summary:
                lines.append(f"- Confirmed runtime path: {summary}")
            if markers:
                lines.append("- Current confirmed markers:")
                lines.extend(f"  - `{item}`" for item in markers)
            if frames:
                lines.append("- Current confirmed stack frames:")
                lines.extend(f"  - `{item}`" for item in frames)
            if blockers:
                lines.append("- Promotion blockers:")
                lines.extend(f"  - {item}" for item in blockers)
            if targets:
                lines.append("- Promotion targets:")
                lines.extend(f"  - {item}" for item in targets)
    return "\n".join(lines).strip()


def load_case(path: Path) -> dict[str, Any]:
    return load_case_definition(path)


def _should_apply_guard(mode: str) -> bool:
    return str(mode or "").endswith("-guarded")


def _is_blind_mode(mode: str) -> bool:
    return str(mode or "").startswith("blind-")


def get_case_prompt(case: dict[str, Any], mode: str) -> str:
    prompts = case.get("prompt", {}) if isinstance(case.get("prompt"), dict) else {}
    key = MODE_TO_PROMPT_KEY.get(mode, mode)
    prompt = str(prompts.get(key, "") or "").strip()
    if prompt:
        if _task_profile_enabled():
            task_profile = _render_task_profile(case)
            if task_profile:
                prompt = f"{task_profile}\n\n{prompt}"
        if not _is_blind_mode(mode):
            contract = _render_confirmation_contract(case)
            if contract:
                prompt = f"{prompt}\n\n{contract}"
        if _should_apply_guard(mode):
            return f"{prompt}\n\n{FINAL_ANSWER_GUARD}"
        return prompt

    available = ", ".join(sorted(str(item) for item in prompts))
    raise ValueError(f"no prompt found for mode={mode!r}; available prompt keys: {available or '(none)'}")


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


def _lines_for_confirmation(case: dict[str, Any]) -> list[str]:
    rows: list[str] = []
    confirmation = case.get("confirmation")
    if not isinstance(confirmation, dict) or not confirmation:
        return rows
    maturity = str(confirmation.get("maturity") or "").strip()
    current_claim = str(confirmation.get("current_claim") or "").strip()
    target_claim = str(confirmation.get("target_claim") or "").strip()
    accepted_runtime_claim = str(confirmation.get("accepted_runtime_claim") or "").strip()
    confirmed = confirmation.get("confirmed_path") if isinstance(confirmation.get("confirmed_path"), dict) else {}
    summary = str(confirmed.get("summary") or "").strip()
    markers = [str(item).strip() for item in confirmed.get("markers") or [] if str(item).strip()]
    frames = [str(item).strip() for item in confirmed.get("stack_frames") or [] if str(item).strip()]
    blockers = [str(item).strip() for item in confirmation.get("promotion_blockers") or [] if str(item).strip()]
    targets = [str(item).strip() for item in confirmation.get("promotion_targets") or [] if str(item).strip()]
    if not any((maturity, current_claim, target_claim, accepted_runtime_claim, summary, markers, frames, blockers, targets)):
        return rows
    rows.append("## Current Confirmation State")
    rows.append("")
    if maturity:
        rows.append(f"- Current maturity: `{maturity}`")
    if current_claim:
        rows.append(f"- Current confirmed claim: {current_claim}")
    if accepted_runtime_claim:
        rows.append(f"- Accepted runtime claim: {accepted_runtime_claim}")
    if target_claim:
        rows.append(f"- Promotion target: {target_claim}")
    if summary:
        rows.append(f"- Confirmed runtime path: {summary}")
    if markers:
        rows.append("- Current confirmed markers:")
        rows.extend(f"  - `{item}`" for item in markers)
    if frames:
        rows.append("- Current confirmed stack frames:")
        rows.extend(f"  - `{item}`" for item in frames)
    if blockers:
        rows.append("- Promotion blockers:")
        rows.extend(f"  - {item}" for item in blockers)
    if targets:
        rows.append("- Promotion targets:")
        rows.extend(f"  - {item}" for item in targets)
    rows.append("")
    return rows


def _run_eval_command(case_path: Path, root: str, output_dir: str, mode: str, provider: str) -> str:
    parts = [
        "python3 -m evaluation.runs.run_single_case",
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


def render_guide(case: dict[str, Any], *, case_path: Path, root_override: str | None, output_dir: str) -> str:
    case_id = str(case.get("case_id") or case_path.stem)
    target = case.get("target") if isinstance(case.get("target"), dict) else {}
    source_root = str(resolve_source_root(case, override=root_override))

    lines = [
        f"# Execution Guide: {case_id}",
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
    lines.extend(_lines_for_confirmation(case))
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
            "- The guarded modes append execution constraints and include the confirmation contract from the case schema.",
            "- Recompute `skill_feedback.*` and `skill_feedback_bundle.*` under `reports/current/` after new final records are produced.",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", type=Path, help="Path to experiment case JSON.")
    parser.add_argument("--mode", default="skillclaw-inline", help="Experiment mode or exact prompt key.")
    parser.add_argument("--guide", action="store_true", help="Render an execution guide instead of a prompt.")
    parser.add_argument("--root", default=None, help="Optional override for target source root when rendering a guide.")
    parser.add_argument(
        "--output-dir",
        default="~/skillclaw-eval/runs/confirmation-reruns",
        help="Suggested remote output directory when rendering a guide.",
    )
    parser.add_argument("--json", action="store_true", help="Print a JSON object instead of plain text.")
    args = parser.parse_args(argv)

    case = load_case(args.case)
    if args.guide:
        text = render_guide(case, case_path=args.case, root_override=args.root, output_dir=args.output_dir)
        if args.json:
            print(json.dumps({"case_id": case.get("case_id"), "guide": text}, ensure_ascii=False, indent=2))
        else:
            print(text)
    else:
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

