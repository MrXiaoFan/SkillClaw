import json
from pathlib import Path

from evaluation.runs.run_remote_case import (
    build_manual_claude_command,
    build_remote_layout,
    build_remote_prepare_command,
    build_remote_render_prompt_command,
    build_remote_run_command,
    enrich_downloaded_final,
)


def test_build_remote_layout_preserves_repo_relative_case_path(tmp_path):
    repo_root = tmp_path / "repo"
    case_path = repo_root / "benchmarks" / "cases" / "demo.json"
    case_path.parent.mkdir(parents=True)
    case_path.write_text("{}", encoding="utf-8")

    layout = build_remote_layout(
        repo_root=repo_root,
        case_path=case_path,
        run_id="demo-run",
        remote_repo_root="~/skillclaw-eval/SkillClaw",
        remote_manual_root="~/skillclaw-eval/manual_runs",
        remote_results_root="~/skillclaw-eval/SkillClaw/runtime/results/remote_vm",
        local_import_root=repo_root / "runtime" / "imports" / "remote_vm",
    )

    assert layout.remote_case_path == "~/skillclaw-eval/SkillClaw/benchmarks/cases/demo.json"
    assert layout.remote_manual_dir == "~/skillclaw-eval/manual_runs/demo-run"
    assert layout.remote_prompt_path.endswith("/demo-run/prompt.txt")
    assert layout.remote_raw_path.endswith("/demo-run/raw.txt")
    assert layout.local_import_dir == repo_root / "runtime" / "imports" / "remote_vm" / "demo-run"


def test_build_manual_claude_command_quotes_paths():
    command = build_manual_claude_command(
        agent_root="/home/li/skillclaw eval/work",
        prompt_path="/tmp/prompt file.txt",
        raw_path="/tmp/raw output.txt",
    )

    assert "cd '/home/li/skillclaw eval/work'" in command
    assert "< '/tmp/prompt file.txt'" in command
    assert "tee '/tmp/raw output.txt'" in command


def test_build_remote_commands_support_path_profile_and_preflight():
    prepare = build_remote_prepare_command(
        remote_case_path="~/repo/benchmarks/cases/demo.json",
        path_profile="remote_vm",
    )
    render = build_remote_render_prompt_command(
        remote_case_path="~/repo/benchmarks/cases/demo.json",
        mode="blind-skillclaw-inline-guarded",
        remote_prompt_path="~/manual/demo/prompt.txt",
        path_profile="remote_vm",
    )
    run = build_remote_run_command(
        remote_case_path="~/repo/benchmarks/cases/demo.json",
        mode="blind-skillclaw-inline-guarded",
        remote_output_dir="~/repo/runtime/results/remote_vm/demo-run",
        run_id="demo-run",
        agent_output="~/manual/demo/raw.txt",
        preflight=True,
        expected_provider="skillclaw",
        skillclaw_url="http://10.12.189.47:30000",
        skillclaw_key="sk-skillclaw-lab",
        expected_skill_count=35,
        path_profile="remote_vm",
    )

    assert prepare.startswith("env SKILLCLAW_PATH_PROFILE=remote_vm python3 -m evaluation.utils.prepare_blind_workspace")
    assert "render_case_prompt" in render
    assert "blind-skillclaw-inline-guarded" in render
    assert run.startswith("env SKILLCLAW_PATH_PROFILE=remote_vm python3 -m evaluation.runs.run_single_case")
    assert "--preflight" in run
    assert "--expected-provider" in run
    assert "--skillclaw-url" in run
    assert "--skillclaw-key" in run
    assert "--expected-skill-count" in run


def test_enrich_downloaded_final_uses_local_session_snapshots(tmp_path):
    final_path = tmp_path / "demo-final.json"
    session_dir = tmp_path / "sessions"
    session_dir.mkdir()
    (session_dir / "snapshot-session.json").write_text(
        json.dumps(
            {
                "session_id": "snapshot-session",
                "timestamp": "2026-07-25T12:07:02Z",
                "turns": [
                    {
                        "turn_num": 9,
                        "selected_skill_names": ["source-parser-state-machine-oob"],
                        "skill_injection": {
                            "injection_mode": "inline",
                            "top_k": 3,
                            "skill_prompt_hash": "abc123",
                            "available_skill_count": 35,
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    final_path.write_text(
        json.dumps(
            {
                "case_id": "demo-case",
                "run": {
                    "start": "2026-07-25T12:00:00+00:00",
                    "end": "2026-07-25T12:05:00+00:00",
                },
                "score": 10.0,
                "max_score": 10.0,
                "checks": {},
                "validation": {"status": "passed", "checks": []},
            }
        ),
        encoding="utf-8",
    )

    enriched_path = enrich_downloaded_final(
        case={"id": "demo-case"},
        downloaded_artifacts={"final": str(final_path)},
        local_session_dir=session_dir,
    )

    assert enriched_path is not None
    enriched = json.loads(Path(enriched_path).read_text(encoding="utf-8"))
    assert enriched["session_id"] == "snapshot-session"
    assert enriched["skill_injection"]["selected_skill_names"] == ["source-parser-state-machine-oob"]
