#!/usr/bin/env python3
"""Prepare an agent-visible blind workspace from a case definition.

This copies the target source tree into a separate workspace, removes
oracle-only paths, and runs case-declared neutral setup commands.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    from evaluation.cases.loader import load_case_definition, resolve_blind_agent_root, resolve_source_root
except ImportError:  # pragma: no cover - direct script execution.
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from evaluation.cases.loader import load_case_definition, resolve_blind_agent_root, resolve_source_root


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _expand_path(text: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(str(text)))).resolve()


def _default_source_root(case: dict[str, Any]) -> Path:
    return resolve_source_root(case)


def _default_blind_root(case: dict[str, Any]) -> Path:
    return resolve_blind_agent_root(case)


def _oracle_only_paths(case: dict[str, Any]) -> list[str]:
    blind = case.get("blind_workspace")
    if not isinstance(blind, dict):
        return []
    return [str(item).strip() for item in blind.get("oracle_only_paths") or [] if str(item).strip()]


def _setup_commands(case: dict[str, Any]) -> list[str]:
    blind = case.get("blind_workspace")
    if not isinstance(blind, dict):
        return []
    return [str(item).strip() for item in blind.get("setup_commands") or [] if str(item).strip()]


def _copy_tree(source_root: Path, blind_root: Path) -> None:
    if blind_root.exists():
        shutil.rmtree(blind_root)
    shutil.copytree(source_root, blind_root, symlinks=True)


def _remove_oracle_only_paths(blind_root: Path, rel_paths: list[str]) -> list[str]:
    removed: list[str] = []
    for rel in rel_paths:
        target = (blind_root / rel).resolve()
        try:
            target.relative_to(blind_root.resolve())
        except ValueError:
            continue
        if target.is_file() or target.is_symlink():
            target.unlink(missing_ok=True)
            removed.append(rel)
        elif target.is_dir():
            shutil.rmtree(target, ignore_errors=True)
            removed.append(rel)
    return removed


def _run_setup_commands(case_path: Path, blind_root: Path, commands: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    repo_root = case_path.resolve().parents[2]
    for command in commands:
        env = os.environ.copy()
        env["SKILLCLAW_CASE_PATH"] = str(case_path.resolve())
        env["SKILLCLAW_REPO_ROOT"] = str(repo_root)
        env["SKILLCLAW_BLIND_ROOT"] = str(blind_root.resolve())
        completed = subprocess.run(
            command,
            shell=True,
            cwd=blind_root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            check=False,
        )
        rows.append(
            {
                "command": command,
                "status": int(completed.returncode),
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            }
        )
        if completed.returncode != 0:
            raise RuntimeError(
                f"blind workspace setup command failed for {case_path.name}: {command}\n{completed.stderr}"
            )
    return rows


def prepare_blind_workspace(case_path: Path, source_root: Path | None = None, blind_root: Path | None = None) -> dict[str, Any]:
    case = load_case_definition(case_path)
    source_root = source_root or _default_source_root(case)
    blind_root = blind_root or _default_blind_root(case)
    commands = _setup_commands(case)

    _copy_tree(source_root, blind_root)
    removed = _remove_oracle_only_paths(blind_root, _oracle_only_paths(case))
    setup_rows = _run_setup_commands(case_path, blind_root, commands)

    return {
        "case_id": case.get("case_id"),
        "source_root": str(source_root),
        "blind_root": str(blind_root),
        "removed_paths": removed,
        "setup_commands": setup_rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", type=Path)
    parser.add_argument("--source-root", default=None)
    parser.add_argument("--blind-root", default=None)
    args = parser.parse_args(argv)

    result = prepare_blind_workspace(
        args.case,
        source_root=_expand_path(args.source_root) if args.source_root else None,
        blind_root=_expand_path(args.blind_root) if args.blind_root else None,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
