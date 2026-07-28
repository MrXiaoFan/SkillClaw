#!/usr/bin/env python3
"""Remote-first orchestration for benchmark cases.

This runner is intentionally thin: it does not reimplement scoring,
validation, or prompt rendering logic. It only synchronizes the reusable
evaluation layer to a remote VM, invokes the existing remote-side entry points,
and optionally pulls the resulting artifacts back to the local machine.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import sys
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

try:
    from evaluation.cases.loader import load_case_definition, resolve_source_root
    from evaluation.postprocess.finalize_record import (
        _default_finalized_out,
        _load_optional_json,
        finalize_record as build_finalized_record,
    )
    from evaluation.remote import RemoteExperimentVmClient, RemoteExperimentVmConfig
    from evaluation.runs.run_single_case import make_run_id
except ImportError:  # pragma: no cover - direct script execution.
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from evaluation.cases.loader import load_case_definition, resolve_source_root
    from evaluation.postprocess.finalize_record import (
        _default_finalized_out,
        _load_optional_json,
        finalize_record as build_finalized_record,
    )
    from evaluation.remote import RemoteExperimentVmClient, RemoteExperimentVmConfig
    from evaluation.runs.run_single_case import make_run_id


SYNC_PATHS = ("evaluation", "benchmarks")


@dataclass(slots=True)
class RemoteRunLayout:
    run_id: str
    remote_case_path: str
    remote_output_dir: str
    remote_manual_dir: str
    remote_prompt_path: str
    remote_raw_path: str
    local_import_dir: Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _join_remote(root: str, *parts: str) -> str:
    path = PurePosixPath(root)
    for part in parts:
        path = path / part
    return path.as_posix()


def _quote(text: str) -> str:
    return shlex.quote(str(text))


def _get_remote_home(client: RemoteExperimentVmClient) -> str:
    result = client.run("printf '%s' \"$HOME\"")
    home = str(result.get("stdout") or "").strip()
    if not home:
        raise RuntimeError("failed to resolve remote $HOME")
    return home


def _expand_remote_path(text: str, remote_home: str) -> str:
    value = str(text or "").strip()
    if not value:
        return value
    if value == "~":
        return remote_home
    if value.startswith("~/"):
        return _join_remote(remote_home, value[2:])
    if value.startswith("$HOME/"):
        return _join_remote(remote_home, value[6:])
    return value


def _ensure_repo_relative(path: Path, repo_root: Path) -> Path:
    try:
        return path.resolve().relative_to(repo_root.resolve())
    except ValueError as exc:
        raise ValueError(f"{path} is outside repository root {repo_root}") from exc


def build_remote_layout(
    *,
    repo_root: Path,
    case_path: Path,
    run_id: str,
    remote_repo_root: str,
    remote_manual_root: str,
    remote_results_root: str,
    local_import_root: Path,
) -> RemoteRunLayout:
    rel_case = _ensure_repo_relative(case_path, repo_root)
    return RemoteRunLayout(
        run_id=run_id,
        remote_case_path=_join_remote(remote_repo_root, rel_case.as_posix()),
        remote_output_dir=_join_remote(remote_results_root, run_id),
        remote_manual_dir=_join_remote(remote_manual_root, run_id),
        remote_prompt_path=_join_remote(remote_manual_dir := _join_remote(remote_manual_root, run_id), "prompt.txt"),
        remote_raw_path=_join_remote(remote_manual_dir, "raw.txt"),
        local_import_dir=local_import_root / run_id,
    )


def build_manual_claude_command(*, agent_root: str, prompt_path: str, raw_path: str) -> str:
    return "\n".join(
        [
            f"cd {_quote(agent_root)}",
            f"rm -f {_quote(raw_path)}",
            "claude -p --dangerously-skip-permissions --output-format text \\",
            f"  < {_quote(prompt_path)} \\",
            f"  | tee {_quote(raw_path)}",
        ]
    )


def _append_option(parts: list[str], flag: str, value: Any) -> None:
    if value in (None, ""):
        return
    parts.extend([flag, str(value)])


def _remote_env_prefix(path_profile: str | None = None) -> str:
    if not path_profile:
        return ""
    return f"env SKILLCLAW_PATH_PROFILE={_quote(path_profile)} "


def build_remote_prepare_command(*, remote_case_path: str, path_profile: str | None = None) -> str:
    return (
        f"{_remote_env_prefix(path_profile)}python3 -m evaluation.utils.prepare_blind_workspace "
        f"{_quote(remote_case_path)}"
    )


def build_remote_run_command(
    *,
    remote_case_path: str,
    mode: str,
    remote_output_dir: str,
    run_id: str,
    agent_output: str | None = None,
    preflight: bool = False,
    expected_provider: str | None = None,
    skillclaw_url: str | None = None,
    skillclaw_key: str | None = None,
    expected_skill_count: int | None = None,
    path_profile: str | None = None,
) -> str:
    parts = [
        "python3",
        "-m",
        "evaluation.runs.run_single_case",
        remote_case_path,
        "--mode",
        mode,
        "--output-dir",
        remote_output_dir,
        "--run-id",
        run_id,
    ]
    if agent_output:
        parts.extend(["--agent-output", agent_output])
    if preflight:
        parts.append("--preflight")
        _append_option(parts, "--expected-provider", expected_provider)
        _append_option(parts, "--skillclaw-url", skillclaw_url)
        _append_option(parts, "--skillclaw-key", skillclaw_key)
        _append_option(parts, "--expected-skill-count", expected_skill_count)
    command = " ".join(_quote(part) for part in parts)
    return f"{_remote_env_prefix(path_profile)}{command}"


def build_remote_render_prompt_command(
    *,
    remote_case_path: str,
    mode: str,
    remote_prompt_path: str,
    path_profile: str | None = None,
) -> str:
    return (
        f"{_remote_env_prefix(path_profile)}python3 -m evaluation.utils.render_case_prompt "
        f"{_quote(remote_case_path)} --mode {_quote(mode)} > {_quote(remote_prompt_path)}"
    )


def _read_remote_json(result: dict[str, Any]) -> dict[str, Any]:
    raw = str(result.get("stdout") or "").strip()
    if not raw:
        raise ValueError("remote command returned empty stdout; expected JSON")
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("remote command did not return a JSON object")
    return value


def _sync_archive(repo_root: Path, include_paths: tuple[str, ...] = SYNC_PATHS) -> Path:
    tmp_dir = repo_root / "runtime" / "tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(prefix="remote-sync-", suffix=".tar.gz", dir=tmp_dir, delete=False)
    archive_path = Path(handle.name)
    handle.close()
    with tarfile.open(archive_path, "w:gz") as tar:
        for rel in include_paths:
            path = repo_root / rel
            if path.exists():
                tar.add(path, arcname=rel)
    return archive_path


def sync_remote_repo(
    client: RemoteExperimentVmClient,
    *,
    repo_root: Path,
    remote_repo_root: str,
) -> dict[str, Any]:
    archive_path = _sync_archive(repo_root)
    remote_archive = _join_remote("/tmp", archive_path.name)
    try:
        upload_result = client.upload(archive_path, remote_archive)
        cleanup_targets = " ".join(_quote(_join_remote(remote_repo_root, name)) for name in SYNC_PATHS)
        extract_command = " && ".join(
            [
                f"mkdir -p {_quote(remote_repo_root)}",
                f"rm -rf {cleanup_targets}",
                f"tar -xzf {_quote(remote_archive)} -C {_quote(remote_repo_root)}",
                f"rm -f {_quote(remote_archive)}",
            ]
        )
        extract_result = client.run(extract_command)
    finally:
        archive_path.unlink(missing_ok=True)
    return {
        "upload": upload_result,
        "extract": extract_result,
        "synced_paths": list(SYNC_PATHS),
    }


def _default_remote_repo_root() -> str:
    return str(os.environ.get("SKILLCLAW_REMOTE_REPO_ROOT") or "~/skillclaw-eval/SkillClaw")


def _default_remote_manual_root() -> str:
    return str(os.environ.get("SKILLCLAW_REMOTE_MANUAL_ROOT") or "~/skillclaw-eval/manual_runs")


def _default_remote_results_root() -> str:
    return str(os.environ.get("SKILLCLAW_REMOTE_RESULTS_ROOT") or "~/skillclaw-eval/SkillClaw/runtime/results/remote_vm")


def _default_local_import_root() -> Path:
    return _repo_root() / "runtime" / "imports" / "remote_vm"


def _default_local_session_dir() -> Path:
    return _repo_root() / ".local-share" / "default" / "sessions"


def _default_local_record_log() -> Path:
    return _repo_root() / "runtime" / "records" / "conversations.jsonl"


def _resolve_local_injection_source(path: Path) -> Path | None:
    if path.is_file():
        return path
    if path.is_dir():
        try:
            next(path.iterdir())
            return path
        except StopIteration:
            fallback = _default_local_record_log()
            return fallback if fallback.is_file() else path
    fallback = _default_local_record_log()
    return fallback if fallback.is_file() else None


def _load_local_injection_value(path: Path) -> Any:
    primary = _resolve_local_injection_source(path)
    if primary is None:
        return None

    primary_value = _load_optional_json(primary)
    if not path.is_dir():
        return primary_value

    fallback = _default_local_record_log()
    if not fallback.is_file():
        return primary_value
    try:
        if fallback.resolve() == primary.resolve():
            return primary_value
    except OSError:
        pass

    fallback_value = _load_optional_json(fallback)
    merged: list[Any] = []
    if isinstance(primary_value, list):
        merged.extend(primary_value)
    elif primary_value is not None:
        merged.append(primary_value)
    if isinstance(fallback_value, list):
        merged.extend(fallback_value)
    elif fallback_value is not None:
        merged.append(fallback_value)
    return merged


def _load_json_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def enrich_downloaded_final(
    *,
    case: dict[str, Any],
    downloaded_artifacts: dict[str, str],
    local_session_dir: Path,
) -> str | None:
    final_path_text = str(downloaded_artifacts.get("final") or "").strip()
    injection_value = _load_local_injection_value(local_session_dir)
    if not final_path_text or injection_value is None:
        return None

    final_path = Path(final_path_text)
    if not final_path.is_file():
        return None

    final_record = _load_json_object(final_path)
    enriched = build_finalized_record(
        case=case,
        final_record=final_record,
        injection_value=injection_value,
    )
    out_path = _default_finalized_out(final_path)
    out_path.write_text(json.dumps(enriched, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(out_path)


def prepare_manual_run(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = _repo_root()
    case = load_case_definition(args.case)
    case_id = str(case.get("case_id") or args.case.stem)
    run_id = args.run_id or make_run_id(case_id, args.mode)
    config = RemoteExperimentVmConfig.from_args(args)

    with RemoteExperimentVmClient(config) as client:
        remote_home = _get_remote_home(client)
        remote_repo_root = _expand_remote_path(args.remote_repo_root, remote_home)
        remote_manual_root = _expand_remote_path(args.remote_manual_root, remote_home)
        remote_results_root = _expand_remote_path(args.remote_results_root, remote_home)
        layout = build_remote_layout(
            repo_root=repo_root,
            case_path=args.case,
            run_id=run_id,
            remote_repo_root=remote_repo_root,
            remote_manual_root=remote_manual_root,
            remote_results_root=remote_results_root,
            local_import_root=args.local_import_root,
        )
        sync_result = sync_remote_repo(client, repo_root=repo_root, remote_repo_root=remote_repo_root) if args.sync_repo else None
        client.run(f"mkdir -p {_quote(layout.remote_manual_dir)} {_quote(layout.remote_output_dir)}")
        prepare_result = (
            client.run(
                build_remote_prepare_command(
                    remote_case_path=layout.remote_case_path,
                    path_profile=args.remote_path_profile,
                ),
                cwd=remote_repo_root,
            )
            if args.mode.startswith("blind-")
            else None
        )
        if prepare_result is not None:
            prepare_json = _read_remote_json(prepare_result)
            agent_root = str(prepare_json.get("blind_root") or "")
        else:
            agent_root = str(resolve_source_root(case))

        render_command = build_remote_render_prompt_command(
            remote_case_path=layout.remote_case_path,
            mode=args.mode,
            remote_prompt_path=layout.remote_prompt_path,
            path_profile=args.remote_path_profile,
        )
        render_result = client.run(render_command, cwd=remote_repo_root)

    result = {
        "action": "prepare-manual",
        "run_id": run_id,
        "sync": sync_result,
        "prepare": prepare_result,
        "render_prompt": render_result,
        "remote_case_path": layout.remote_case_path,
        "remote_output_dir": layout.remote_output_dir,
        "remote_manual_dir": layout.remote_manual_dir,
        "remote_prompt_path": layout.remote_prompt_path,
        "remote_raw_path": layout.remote_raw_path,
        "remote_agent_root": agent_root,
        "manual_claude_command": build_manual_claude_command(
            agent_root=agent_root,
            prompt_path=layout.remote_prompt_path,
            raw_path=layout.remote_raw_path,
        ),
        "local_import_dir": str(layout.local_import_dir),
    }
    return result


def _download_artifacts(
    client: RemoteExperimentVmClient,
    *,
    layout: RemoteRunLayout,
    remote_output_dir: str,
    remote_raw_path: str | None = None,
) -> dict[str, str]:
    local_dir = layout.local_import_dir
    local_dir.mkdir(parents=True, exist_ok=True)
    names = {
        "prompt": layout.remote_prompt_path,
        "raw": remote_raw_path or layout.remote_raw_path,
        "final": _join_remote(remote_output_dir, f"{layout.run_id}-final.json"),
        "score": _join_remote(remote_output_dir, f"{layout.run_id}-score.json"),
        "validation": _join_remote(remote_output_dir, f"{layout.run_id}-validation.json"),
        "agent_json": _join_remote(remote_output_dir, f"{layout.run_id}-agent.json"),
        "manifest": _join_remote(remote_output_dir, f"{layout.run_id}-manifest.json"),
    }
    downloaded: dict[str, str] = {}
    for label, remote_path in names.items():
        local_path = local_dir / PurePosixPath(remote_path).name
        try:
            client.download(remote_path, local_path)
        except Exception:  # pragma: no cover - remote filesystem variability.
            continue
        downloaded[label] = str(local_path)
    return downloaded


def finalize_manual_run(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = _repo_root()
    case = load_case_definition(args.case)
    case_id = str(case.get("case_id") or args.case.stem)
    run_id = args.run_id or make_run_id(case_id, args.mode)
    config = RemoteExperimentVmConfig.from_args(args)
    with RemoteExperimentVmClient(config) as client:
        remote_home = _get_remote_home(client)
        remote_repo_root = _expand_remote_path(args.remote_repo_root, remote_home)
        remote_manual_root = _expand_remote_path(args.remote_manual_root, remote_home)
        remote_results_root = _expand_remote_path(args.remote_results_root, remote_home)
        layout = build_remote_layout(
            repo_root=repo_root,
            case_path=args.case,
            run_id=run_id,
            remote_repo_root=remote_repo_root,
            remote_manual_root=remote_manual_root,
            remote_results_root=remote_results_root,
            local_import_root=args.local_import_root,
        )
        remote_raw_path = _expand_remote_path(args.remote_raw_path, remote_home) if args.remote_raw_path else layout.remote_raw_path
        command = build_remote_run_command(
            remote_case_path=layout.remote_case_path,
            mode=args.mode,
            remote_output_dir=layout.remote_output_dir,
            run_id=run_id,
            agent_output=remote_raw_path,
            preflight=args.preflight,
            expected_provider=args.expected_provider,
            skillclaw_url=args.skillclaw_url,
            skillclaw_key=args.skillclaw_key,
            expected_skill_count=args.expected_skill_count,
            path_profile=args.remote_path_profile,
        )
        run_result = client.run(command, cwd=remote_repo_root)
        downloaded = _download_artifacts(
            client,
            layout=layout,
            remote_output_dir=layout.remote_output_dir,
            remote_raw_path=remote_raw_path,
        )
    enriched_path = enrich_downloaded_final(
        case=case,
        downloaded_artifacts=downloaded,
        local_session_dir=args.local_session_dir,
    )
    return {
        "action": "finalize-manual",
        "run_id": run_id,
        "remote_command": command,
        "run_result": run_result,
        "downloaded_artifacts": downloaded,
        "local_final_enriched": enriched_path,
        "local_import_dir": str(layout.local_import_dir),
    }


def run_auto(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = _repo_root()
    case = load_case_definition(args.case)
    case_id = str(case.get("case_id") or args.case.stem)
    run_id = args.run_id or make_run_id(case_id, args.mode)
    config = RemoteExperimentVmConfig.from_args(args)
    with RemoteExperimentVmClient(config) as client:
        remote_home = _get_remote_home(client)
        remote_repo_root = _expand_remote_path(args.remote_repo_root, remote_home)
        remote_manual_root = _expand_remote_path(args.remote_manual_root, remote_home)
        remote_results_root = _expand_remote_path(args.remote_results_root, remote_home)
        layout = build_remote_layout(
            repo_root=repo_root,
            case_path=args.case,
            run_id=run_id,
            remote_repo_root=remote_repo_root,
            remote_manual_root=remote_manual_root,
            remote_results_root=remote_results_root,
            local_import_root=args.local_import_root,
        )
        command = build_remote_run_command(
            remote_case_path=layout.remote_case_path,
            mode=args.mode,
            remote_output_dir=layout.remote_output_dir,
            run_id=run_id,
            preflight=args.preflight,
            expected_provider=args.expected_provider,
            skillclaw_url=args.skillclaw_url,
            skillclaw_key=args.skillclaw_key,
            expected_skill_count=args.expected_skill_count,
            path_profile=args.remote_path_profile,
        )
        sync_result = sync_remote_repo(client, repo_root=repo_root, remote_repo_root=remote_repo_root) if args.sync_repo else None
        if args.mode.startswith("blind-"):
            client.run(
                build_remote_prepare_command(
                    remote_case_path=layout.remote_case_path,
                    path_profile=args.remote_path_profile,
                ),
                cwd=remote_repo_root,
            )
        run_result = client.run(command, cwd=remote_repo_root)
        downloaded = _download_artifacts(client, layout=layout, remote_output_dir=layout.remote_output_dir)
    enriched_path = enrich_downloaded_final(
        case=case,
        downloaded_artifacts=downloaded,
        local_session_dir=args.local_session_dir,
    )
    return {
        "action": "run-auto",
        "run_id": run_id,
        "sync": sync_result,
        "remote_command": command,
        "run_result": run_result,
        "downloaded_artifacts": downloaded,
        "local_final_enriched": enriched_path,
        "local_import_dir": str(layout.local_import_dir),
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", help="Remote VM host. Default: $env:SKILLCLAW_REMOTE_HOST")
    parser.add_argument("--user", help="Remote VM user. Default: $env:SKILLCLAW_REMOTE_USER")
    parser.add_argument("--port", type=int, default=None, help="SSH port.")
    parser.add_argument("--key-path", help="Private key path. Default: ~/.ssh/skillclaw_vm if present.")
    parser.add_argument("--password", help="Password. Default: $env:SKILLCLAW_REMOTE_PASSWORD")
    parser.add_argument("--connect-timeout", type=float, default=None)
    parser.add_argument("--remote-repo-root", default=_default_remote_repo_root())
    parser.add_argument("--remote-manual-root", default=_default_remote_manual_root())
    parser.add_argument("--remote-results-root", default=_default_remote_results_root())
    parser.add_argument("--local-import-root", type=Path, default=_default_local_import_root())
    parser.add_argument("--local-session-dir", type=Path, default=_default_local_session_dir())
    parser.add_argument("--sync-repo", action="store_true", help="Sync evaluation/ and benchmarks/ to the remote repo first.")
    parser.add_argument(
        "--remote-path-profile",
        default="",
        help="Optional SKILLCLAW_PATH_PROFILE value used only on the remote VM.",
    )

    subparsers = parser.add_subparsers(dest="action", required=True)

    prepare = subparsers.add_parser("prepare-manual", help="Prepare remote workspace and print the exact Claude command.")
    prepare.add_argument("case", type=Path)
    prepare.add_argument("--mode", default="blind-skillclaw-inline-guarded")
    prepare.add_argument("--run-id", default="")

    finalize = subparsers.add_parser("finalize-manual", help="Use an already-produced remote raw.txt to run remote scoring and validation.")
    finalize.add_argument("case", type=Path)
    finalize.add_argument("--mode", default="blind-skillclaw-inline-guarded")
    finalize.add_argument("--run-id", default="")
    finalize.add_argument("--remote-raw-path", default="")
    finalize.add_argument("--preflight", action="store_true")
    finalize.add_argument("--expected-provider", choices=["skillclaw", "deepseek", "unknown"], default=None)
    finalize.add_argument("--skillclaw-url", default="")
    finalize.add_argument("--skillclaw-key", default="")
    finalize.add_argument("--expected-skill-count", type=int, default=None)

    auto = subparsers.add_parser("run-auto", help="Run the whole case remotely through the existing remote-side runner.")
    auto.add_argument("case", type=Path)
    auto.add_argument("--mode", default="blind-skillclaw-inline-guarded")
    auto.add_argument("--run-id", default="")
    auto.add_argument("--preflight", action="store_true")
    auto.add_argument("--expected-provider", choices=["skillclaw", "deepseek", "unknown"], default=None)
    auto.add_argument("--skillclaw-url", default="")
    auto.add_argument("--skillclaw-key", default="")
    auto.add_argument("--expected-skill-count", type=int, default=None)

    check = subparsers.add_parser("check", help="Verify remote connectivity and repo presence.")
    check.add_argument("--cwd", default="")
    return parser


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.action == "prepare-manual":
        result = prepare_manual_run(args)
    elif args.action == "finalize-manual":
        result = finalize_manual_run(args)
    elif args.action == "run-auto":
        result = run_auto(args)
    elif args.action == "check":
        config = RemoteExperimentVmConfig.from_args(args)
        with RemoteExperimentVmClient(config) as client:
            remote_home = _get_remote_home(client)
            command = "hostname && whoami && pwd"
            if args.cwd:
                command = f"cd {_quote(_expand_remote_path(args.cwd, remote_home))} && hostname && whoami && pwd"
            result = client.run(command)
            result = {"action": "check", "result": result}
    else:  # pragma: no cover - guarded by argparse.
        raise AssertionError(f"unknown action: {args.action}")

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
