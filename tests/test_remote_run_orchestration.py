import json
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from evaluation.evolution import EvolutionHandoffError, build_run_feedback_bundle, handoff_validated_run
from evaluation.runs.run_remote_case import (
    _default_local_session_dir,
    _build_session_override_payload,
    _handoff_after_run,
    _persist_evolution_handoff,
    build_manual_claude_command,
    build_remote_layout,
    build_remote_prepare_command,
    build_remote_render_prompt_command,
    build_remote_run_command,
    enrich_downloaded_final,
)
from evolve_server.engines.workflow import EvolveServer
from skillclaw.object_store import LocalObjectStore
from skillclaw.replay_gate_worker import ReplayGateWorker
from skillclaw import skillspace


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


def test_default_local_session_dir_uses_skillspace_share_root(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "evaluation.runs.run_remote_case.skillspace.default_layout",
        lambda: SimpleNamespace(share_dir=tmp_path / "skillspace" / "share"),
    )

    assert _default_local_session_dir() == tmp_path / "skillspace" / "share" / "default" / "sessions"


def test_build_manual_claude_command_quotes_paths():
    session_id = "c4f36f5d-60e2-45e7-b135-1bd397152ca6"
    command = build_manual_claude_command(
        agent_root="/home/li/skillclaw eval/work",
        prompt_path="/tmp/prompt file.txt",
        raw_path="/tmp/raw output.txt",
        session_id=session_id,
    )

    assert "cd '/home/li/skillclaw eval/work'" in command
    assert "< '/tmp/prompt file.txt'" in command
    assert "tee '/tmp/raw output.txt'" in command
    assert f"--session-id {session_id}" in command


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
        session_id="c4f36f5d-60e2-45e7-b135-1bd397152ca6",
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
    assert "--session-id" in run


def test_build_session_override_payload_force_names():
    args = SimpleNamespace(
        server_disable_skills=False,
        server_force_skills="source-parser-state-machine-oob, elf-cwe120-plt-analysis ",
        server_inline_skill_json=None,
        server_override_note="ablation-force",
    )

    payload = _build_session_override_payload(args)

    assert payload == {
        "note": "ablation-force",
        "forced_skill_names": [
            "source-parser-state-machine-oob",
            "elf-cwe120-plt-analysis",
        ],
    }


def test_build_session_override_payload_inline_skill_json(tmp_path):
    skill_path = tmp_path / "candidate.json"
    skill_path.write_text(
        json.dumps(
            {
                "candidate_skill": {
                    "name": "candidate-skill",
                    "description": "desc",
                    "content": "# Candidate",
                    "category": "general",
                }
            }
        ),
        encoding="utf-8",
    )
    args = SimpleNamespace(
        server_disable_skills=False,
        server_force_skills="",
        server_inline_skill_json=skill_path,
        server_override_note="candidate-inline",
    )

    payload = _build_session_override_payload(args)

    assert payload is not None
    assert payload["note"] == "candidate-inline"
    assert payload["inline_skills"][0]["name"] == "candidate-skill"


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


def test_enrich_downloaded_final_backfills_prediction_fields_from_agent_json(tmp_path):
    final_path = tmp_path / "demo-final.json"
    agent_path = tmp_path / "demo-agent.json"
    session_dir = tmp_path / "sessions"
    session_dir.mkdir()
    (session_dir / "snapshot-session.json").write_text(
        json.dumps(
            {
                "session_id": "snapshot-session",
                "timestamp": "2026-07-25T12:07:02Z",
                "turns": [],
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
                "predictions": {"cves": ["CVE-legacy"]},
                "validation": {"status": "passed", "checks": []},
            }
        ),
        encoding="utf-8",
    )
    agent_path.write_text(
        json.dumps(
            {
                "predicted_cves": ["CVE-2016-3977"],
                "predicted_files": ["util/gif2rgb.c"],
                "predicted_functions": ["DumpScreen2RGB"],
                "root_cause": "unchecked color map index",
                "evidence": "line 304 uses GifRow[j] directly",
                "confidence": "high",
            }
        ),
        encoding="utf-8",
    )

    enriched_path = enrich_downloaded_final(
        case={"id": "demo-case"},
        downloaded_artifacts={"final": str(final_path), "agent_json": str(agent_path)},
        local_session_dir=session_dir,
    )

    enriched = json.loads(Path(enriched_path).read_text(encoding="utf-8"))
    assert enriched["predicted_cves"] == ["CVE-2016-3977"]
    assert enriched["predicted_files"] == ["util/gif2rgb.c"]
    assert enriched["predicted_functions"] == ["DumpScreen2RGB"]
    assert enriched["root_cause"] == "unchecked color map index"
    assert enriched["confidence"] == "high"


def test_enrich_downloaded_final_falls_back_to_conversation_log_when_session_dir_empty(tmp_path, monkeypatch):
    final_path = tmp_path / "demo-final.json"
    session_dir = tmp_path / "sessions"
    session_dir.mkdir()
    records_dir = tmp_path / "runtime" / "records"
    records_dir.mkdir(parents=True)
    conversations_path = records_dir / "conversations.jsonl"
    conversations_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "session_id": "remote-session",
                        "timestamp": "2026-07-28 15:15:27",
                        "turn": 5,
                        "selected_skill_names": [
                            "source-parser-state-machine-oob",
                            "vuln-hunting",
                        ],
                        "skill_injection": {
                            "injection_mode": "inline",
                            "top_k": 3,
                            "skill_prompt_hash": "abc123",
                            "available_skill_count": 35,
                            "selected_skill_names": [
                                "source-parser-state-machine-oob",
                                "vuln-hunting",
                            ],
                        },
                    }
                )
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    final_path.write_text(
        json.dumps(
            {
                "case_id": "demo-case",
                "run": {
                    "start": "2026-07-28T07:14:45+00:00",
                    "end": "2026-07-28T07:16:59+00:00",
                },
                "score": 10.0,
                "max_score": 10.0,
                "checks": {},
                "validation": {"status": "passed", "checks": []},
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr("evaluation.runs.run_remote_case._repo_root", lambda: tmp_path)
    enriched_path = enrich_downloaded_final(
        case={"id": "demo-case"},
        downloaded_artifacts={"final": str(final_path)},
        local_session_dir=session_dir,
    )

    assert enriched_path is not None
    enriched = json.loads(Path(enriched_path).read_text(encoding="utf-8"))
    assert enriched["session_id"] == "remote-session"
    assert enriched["session_id_source"] == "inferred_from_injection_log"
    assert enriched["skill_injection"]["selected_skill_names"] == [
        "source-parser-state-machine-oob",
        "vuln-hunting",
    ]


def test_enrich_downloaded_final_merges_session_snapshots_with_conversation_log(tmp_path, monkeypatch):
    final_path = tmp_path / "demo-final.json"
    session_dir = tmp_path / "sessions"
    session_dir.mkdir()
    (session_dir / "stale-snapshot.json").write_text(
        json.dumps(
            {
                "session_id": "snapshot-old",
                "timestamp": "2026-07-28T08:43:54Z",
                "turns": [
                    {
                        "turn_num": 8,
                        "selected_skill_names": [
                            "source-parser-state-machine-oob",
                            "elf-plt-reloc-sink-scan",
                            "cwe120-analysis-verification",
                        ],
                        "skill_injection": {
                            "injection_mode": "inline",
                            "top_k": 3,
                            "skill_prompt_hash": "old123",
                            "available_skill_count": 35,
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    records_dir = tmp_path / "runtime" / "records"
    records_dir.mkdir(parents=True)
    conversations_path = records_dir / "conversations.jsonl"
    conversations_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "session_id": "target-direct",
                        "timestamp": "2026-07-28 16:43:43",
                        "turn": 7,
                        "selected_skill_names": [
                            "source-parser-state-machine-oob",
                            "elf-plt-reloc-sink-scan",
                            "elf-cwe120-plt-analysis",
                        ],
                        "skill_injection": {
                            "injection_mode": "inline",
                            "top_k": 3,
                            "skill_prompt_hash": "new456",
                            "available_skill_count": 35,
                            "selected_skill_names": [
                                "source-parser-state-machine-oob",
                                "elf-plt-reloc-sink-scan",
                                "elf-cwe120-plt-analysis",
                            ],
                        },
                    }
                )
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    final_path.write_text(
        json.dumps(
            {
                "case_id": "demo-case",
                "run": {
                    "start": "2026-07-28T08:42:49+00:00",
                    "end": "2026-07-28T08:44:33+00:00",
                },
                "score": 7.0,
                "max_score": 10.0,
                "checks": {},
                "validation": {"status": "failed", "checks": []},
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr("evaluation.runs.run_remote_case._repo_root", lambda: tmp_path)
    enriched_path = enrich_downloaded_final(
        case={"id": "demo-case"},
        downloaded_artifacts={"final": str(final_path)},
        local_session_dir=session_dir,
    )

    assert enriched_path is not None
    enriched = json.loads(Path(enriched_path).read_text(encoding="utf-8"))
    assert enriched["session_id"] == "target-direct"
    assert enriched["session_id_source"] == "inferred_from_injection_log"
    assert enriched["skill_prompt_hash"] == "new456"
    assert enriched["skill_injection"]["selected_skill_names"] == [
        "source-parser-state-machine-oob",
        "elf-plt-reloc-sink-scan",
        "elf-cwe120-plt-analysis",
    ]


def test_enrich_downloaded_final_prefers_latest_attribution_eligible_turn(tmp_path, monkeypatch):
    final_path = tmp_path / "demo-final.json"
    session_dir = tmp_path / "sessions"
    session_dir.mkdir()
    records_dir = tmp_path / "runtime" / "records"
    records_dir.mkdir(parents=True)
    conversations_path = records_dir / "conversations.jsonl"
    session_id = "remote-session"
    conversations_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "session_id": session_id,
                        "client_session_id": session_id,
                        "timestamp": "2026-07-28 16:15:45",
                        "turn": 2,
                        "selected_skill_names": [
                            "source-parser-state-machine-oob",
                            "elf-cwe120-plt-analysis",
                        ],
                        "skill_injection": {
                            "selected_skill_names": [
                                "source-parser-state-machine-oob",
                                "elf-cwe120-plt-analysis",
                            ],
                            "skill_prompt_hash": "abc123",
                            "attribution_eligible": True,
                        },
                    }
                ),
                json.dumps(
                    {
                        "session_id": session_id,
                        "client_session_id": session_id,
                        "timestamp": "2026-07-28 16:19:43",
                        "turn": 12,
                        "selected_skill_names": [],
                        "skill_injection": {
                            "selected_skill_names": [],
                            "skill_prompt_hash": "abc123",
                            "attribution_eligible": False,
                        },
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    final_path.write_text(
        json.dumps(
            {
                "case_id": "demo-case",
                "run": {
                    "start": "2026-07-28T08:15:35+00:00",
                    "end": "2026-07-28T08:20:01+00:00",
                },
                "score": 8.0,
                "max_score": 10.0,
                "checks": {},
                "validation": {"status": "passed", "checks": []},
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr("evaluation.runs.run_remote_case._repo_root", lambda: tmp_path)
    enriched_path = enrich_downloaded_final(
        case={"id": "demo-case"},
        downloaded_artifacts={"final": str(final_path)},
        local_session_dir=session_dir,
    )

    assert enriched_path is not None
    enriched = json.loads(Path(enriched_path).read_text(encoding="utf-8"))
    assert enriched["selected_skill_names"] == [
        "source-parser-state-machine-oob",
        "elf-cwe120-plt-analysis",
    ]
    assert enriched["skill_injection"]["turn"] == 2


def _write_evolution_record(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "case_id": "demo-case",
                "mode": "blind-skillclaw-inline-guarded",
                "run_id": "demo-run",
                "session_id": "session-demo",
                "score": 9.0,
                "max_score": 10.0,
                "checks": {
                    "file": {"hit": True, "expected": ["parser.c"], "matched": ["parser.c"]},
                    "function": {"hit": True, "expected": ["parse"], "matched": ["parse"]},
                    "evidence": {"hit": True},
                    "root_cause": {"hit": True},
                },
                "validation": {"status": "passed", "checks": []},
                "feedback": {"decision": "positive", "suggested_action": "keep"},
                "skill_relevance": {
                    "status": "has_task_relevant_skill",
                    "relevant_skills": ["source-parser-state-machine-oob"],
                    "mismatched_skills": [],
                    "infra_skills": [],
                },
                "skill_injection": {"selected_skill_names": ["source-parser-state-machine-oob"]},
            }
        ),
        encoding="utf-8",
    )


def test_build_run_feedback_bundle_is_compact_and_run_scoped(tmp_path):
    final_path = tmp_path / "final.json"
    output_path = tmp_path / "runtime" / "evolve" / "feedback.json"
    _write_evolution_record(final_path)

    result = build_run_feedback_bundle(final_path, output_path)

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert result["session_id"] == "session-demo"
    assert result["skills"] == ["source-parser-state-machine-oob"]
    assert payload[0]["summary"]["selected_runs"] == 1
    assert payload[0]["dimensions"]["validator_passed"] == 1


def test_handoff_routes_no_skill_control_through_feedback_receipt_and_closes_session(tmp_path):
    final_path = tmp_path / "final.json"
    final_path.write_text(
        json.dumps(
            {
                "case_id": "demo-case",
                "mode": "blind-skillclaw-inline-guarded",
                "run_id": "demo-run",
                "session_id": "session-demo",
                "session_segment_id": "c4f36f5d-60e2-45e7-b135-1bd397152ca6",
                "score": 5.0,
                "max_score": 10.0,
                "checks": {},
                "validation": {"status": "passed", "checks": []},
                "skill_injection": {"selected_skill_names": []},
            }
        ),
        encoding="utf-8",
    )
    calls = []
    trigger_count = 0

    def fake_request(url, *, method="GET", api_key="", timeout=30.0, json_body=None):
        nonlocal trigger_count
        calls.append((method, url, api_key, timeout, json_body))
        if url.endswith("/status"):
            return {"engine": "workflow", "publish_mode": "validated"}
        if url.endswith("/v1/sessions"):
            return {
                "sessions": [
                    {
                        "session_id": "session-demo",
                        "client_session_id": "session-demo",
                        "session_segment_id": "c4f36f5d-60e2-45e7-b135-1bd397152ca6",
                    }
                ]
            }
        if url.endswith("/v1/run-feedback"):
            assert json_body["run_id"] == "demo-run"
            assert json_body["skill_feedback"] == []
            assert json_body["attribution_status"] == "no_selected_skills_control"
            return {"queued": True, "session_segment_id": "c4f36f5d-60e2-45e7-b135-1bd397152ca6"}
        if "/v1/run-feedback/status?" in url:
            return {"status": "consumed" if trigger_count >= 1 else "pending"}
        if method == "DELETE":
            return {
                "deleted": True,
                "session_id": "session-demo",
                "session_segment_id": "c4f36f5d-60e2-45e7-b135-1bd397152ca6",
            }
        if url.endswith("/trigger"):
            trigger_count += 1
            return {
                "sessions": 1,
                "uploaded_skills": 0,
                "candidates_queued": 0,
                "evolutions": [],
            }
        raise AssertionError(f"unexpected request: {method} {url}")

    result = handoff_validated_run(
        final_path,
        repo_root=tmp_path,
        skillclaw_url="http://skillclaw.test",
        skillclaw_api_key="secret",
        evolve_url="http://evolve.test",
        request=fake_request,
    )

    assert result["status"] == "handed_off"
    assert result["feedback"]["skills"] == []
    assert result["feedback"]["selected_skills"] == []
    assert result["feedback"]["attribution_status"] == "no_selected_skills_control"
    assert result["next_stage"] == "no_candidate"
    assert result["session_close"]["deleted"] is True
    assert result["runtime_feedback_bundle"] is None
    assert any(url.endswith("/v1/run-feedback") for _, url, _, _, _ in calls)


def test_handoff_requires_validated_mode_and_queues_without_publish(tmp_path):
    final_path = tmp_path / "final.json"
    feedback_path = tmp_path / "runtime" / "evolve" / "feedback.json"
    _write_evolution_record(final_path)
    calls = []
    trigger_count = 0

    segment_id = "c4f36f5d-60e2-45e7-b135-1bd397152ca6"

    def fake_request(url, *, method="GET", api_key="", timeout=30.0, json_body=None):
        nonlocal trigger_count
        calls.append((method, url, api_key, timeout, json_body))
        if url.endswith("/status"):
            return {
                "engine": "workflow",
                "publish_mode": "validated",
                "pending_sessions": 0,
                "feedback_bundle_path": str(feedback_path),
            }
        if url.endswith("/v1/sessions"):
            return {
                "sessions": [
                    {
                        "session_id": "session-demo",
                        "client_session_id": "session-demo",
                        "session_segment_id": segment_id,
                    }
                ]
            }
        if url.endswith("/v1/run-feedback"):
            assert json_body["run_id"] == "demo-run"
            assert json_body["session_segment_id"] == segment_id
            return {"queued": True, "session_segment_id": segment_id}
        if "/v1/run-feedback/status?" in url:
            return {"status": "consumed" if trigger_count >= 2 else "pending"}
        if method == "DELETE":
            return {"deleted": True, "session_id": "session-demo", "session_segment_id": segment_id}
        trigger_count += 1
        if trigger_count == 1:
            return {"sessions": 0, "uploaded_skills": 0, "candidates_queued": 0}
        return {"sessions": 1, "uploaded_skills": 0, "candidates_queued": 1}

    result = handoff_validated_run(
        final_path,
        repo_root=tmp_path,
        skillclaw_url="http://skillclaw.test",
        skillclaw_api_key="secret",
        evolve_url="http://evolve.test",
        request=fake_request,
        trigger_delay_seconds=0,
    )

    assert result["status"] == "handed_off"
    assert result["next_stage"] == "candidate_validation"
    assert result["session_segment_id"] == segment_id
    assert result["runtime_feedback_bundle"]["path"] == str(feedback_path)
    assert feedback_path.is_file()
    runtime_bundle = json.loads(feedback_path.read_text(encoding="utf-8"))
    assert runtime_bundle[0]["skill"] == "source-parser-state-machine-oob"
    assert any(method == "DELETE" and url.endswith("/v1/sessions/session-demo") for method, url, _, _, _ in calls)
    assert any(url.endswith("/v1/run-feedback") for _, url, _, _, _ in calls)


def test_handoff_refuses_direct_publish_mode(tmp_path):
    final_path = tmp_path / "final.json"
    _write_evolution_record(final_path)

    def fake_request(_url, **_kwargs):
        return {
            "engine": "workflow",
            "publish_mode": "direct",
            "pending_sessions": 0,
            "feedback_bundle_path": str(tmp_path / "runtime" / "feedback.json"),
        }

    with pytest.raises(EvolutionHandoffError, match="validated"):
        handoff_validated_run(
            final_path,
            repo_root=tmp_path,
            skillclaw_url="http://skillclaw.test",
            skillclaw_api_key="secret",
            evolve_url="http://evolve.test",
            request=fake_request,
        )


def test_handoff_requires_consumed_receipt_even_if_evolve_saw_session(tmp_path):
    final_path = tmp_path / "final.json"
    _write_evolution_record(final_path)
    segment_id = "c4f36f5d-60e2-45e7-b135-1bd397152ca6"

    def fake_request(url, *, method="GET", api_key="", timeout=30.0, json_body=None):
        if url.endswith("/status"):
            return {"engine": "workflow", "publish_mode": "validated"}
        if url.endswith("/v1/sessions"):
            return {
                "sessions": [
                    {
                        "session_id": "session-demo",
                        "client_session_id": "session-demo",
                        "session_segment_id": segment_id,
                    }
                ]
            }
        if url.endswith("/v1/run-feedback"):
            return {"queued": True, "session_segment_id": segment_id}
        if method == "DELETE":
            return {"deleted": True, "session_id": "session-demo", "session_segment_id": segment_id}
        if "/v1/run-feedback/status?" in url:
            return {"status": "pending"}
        if url.endswith("/trigger"):
            return {
                "sessions": 1,
                "uploaded_skills": 0,
                "candidates_queued": 0,
                "had_processing_error": True,
            }
        raise AssertionError(f"unexpected request: {method} {url}")

    with pytest.raises(EvolutionHandoffError, match="failed during processing"):
        handoff_validated_run(
            final_path,
            repo_root=tmp_path,
            skillclaw_url="http://skillclaw.test",
            skillclaw_api_key="secret",
            evolve_url="http://evolve.test",
            request=fake_request,
            trigger_attempts=1,
            trigger_delay_seconds=0,
        )


def test_handoff_does_not_close_a_newer_segment_of_the_same_client_session(tmp_path):
    final_path = tmp_path / "final.json"
    _write_evolution_record(final_path)
    record = json.loads(final_path.read_text(encoding="utf-8"))
    old_segment = "c4f36f5d-60e2-45e7-b135-1bd397152ca6"
    new_segment = "c6e56f89-203f-4676-b528-ab172c0a027e"
    record["session_segment_id"] = old_segment
    final_path.write_text(json.dumps(record), encoding="utf-8")
    calls = []

    def fake_request(url, *, method="GET", api_key="", timeout=30.0, json_body=None):
        calls.append((method, url, json_body))
        if url.endswith("/status"):
            return {"engine": "workflow", "publish_mode": "validated"}
        if url.endswith("/v1/sessions"):
            return {"sessions": [{"session_id": "session-demo", "session_segment_id": new_segment}]}
        if url.endswith("/v1/run-feedback"):
            assert json_body["session_segment_id"] == old_segment
            return {"queued": True, "session_segment_id": old_segment}
        if "/v1/run-feedback/status?" in url:
            return {"status": "consumed", "session_segment_id": old_segment}
        if url.endswith("/trigger"):
            return {"sessions": 1, "uploaded_skills": 0, "candidates_queued": 1, "evolutions": []}
        raise AssertionError(f"unexpected request: {method} {url}")

    result = handoff_validated_run(
        final_path,
        repo_root=tmp_path,
        skillclaw_url="http://skillclaw.test",
        skillclaw_api_key="secret",
        evolve_url="http://evolve.test",
        request=fake_request,
        trigger_delay_seconds=0,
    )

    assert result["session_close"]["reason"] == "client_session_has_newer_segment"
    assert not any(method == "DELETE" for method, _, _ in calls)


def test_handoff_drives_local_validation_followup_for_current_candidate_jobs(tmp_path, monkeypatch):
    final_path = tmp_path / "final.json"
    _write_evolution_record(final_path)
    segment_id = "c4f36f5d-60e2-45e7-b135-1bd397152ca6"
    trigger_count = 0
    followup_calls = []

    def fake_followup(*, job_ids, evolve_url, request, max_attempts, attempt_delay_seconds):
        followup_calls.append(
            {
                "job_ids": list(job_ids),
                "evolve_url": evolve_url,
                "max_attempts": max_attempts,
                "attempt_delay_seconds": attempt_delay_seconds,
            }
        )
        return {
            "status": "completed",
            "job_ids": list(job_ids),
            "attempts": 2,
            "validation_runs": [{"validated_jobs": 1}, {"validated_jobs": 1}],
            "trigger_runs": [{"actions": 1}, {"actions": 1}],
            "decisions": {
                job_id: {"status": "rejected", "job_id": job_id}
                for job_id in job_ids
            },
            "pending_job_ids": [],
        }

    monkeypatch.setattr("evaluation.evolution._finalize_candidate_validation_jobs", fake_followup)

    def fake_request(url, *, method="GET", api_key="", timeout=30.0, json_body=None):
        nonlocal trigger_count
        if url.endswith("/status"):
            return {"engine": "workflow", "publish_mode": "validated"}
        if url.endswith("/v1/sessions"):
            return {
                "sessions": [
                    {
                        "session_id": "session-demo",
                        "client_session_id": "session-demo",
                        "session_segment_id": segment_id,
                    }
                ]
            }
        if url.endswith("/v1/run-feedback"):
            return {"queued": True, "session_segment_id": segment_id}
        if "/v1/run-feedback/status?" in url:
            return {"status": "consumed"}
        if method == "DELETE":
            return {"deleted": True, "session_id": "session-demo", "session_segment_id": segment_id}
        if url.endswith("/trigger"):
            trigger_count += 1
            return {
                "sessions": 1,
                "uploaded_skills": 0,
                "candidates_queued": 2,
                "evolutions": [
                    {
                        "action": "queued_for_validation",
                        "validation_job_id": "job-a",
                        "session_ids": [segment_id],
                        "uploaded": False,
                    },
                    {
                        "action": "queued_for_validation",
                        "validation_job_id": "job-b",
                        "session_ids": [segment_id],
                        "uploaded": False,
                    },
                ],
            }
        raise AssertionError(f"unexpected request: {method} {url}")

    result = handoff_validated_run(
        final_path,
        repo_root=tmp_path,
        skillclaw_url="http://skillclaw.test",
        skillclaw_api_key="secret",
        evolve_url="http://evolve.test",
        request=fake_request,
        trigger_delay_seconds=0,
    )

    assert result["status"] == "handed_off"
    assert result["validation_followup"]["status"] == "completed"
    assert result["validation_followup"]["pending_job_ids"] == []
    assert followup_calls == [
        {
            "job_ids": ["job-a", "job-b"],
            "evolve_url": "http://evolve.test",
            "max_attempts": 4,
            "attempt_delay_seconds": 0,
        }
    ]


def test_persist_evolution_handoff_writes_back_to_finalized_record(tmp_path):
    final_path = tmp_path / "demo-final-enriched.json"
    final_path.write_text(json.dumps({"run_id": "demo-run", "status": "passed"}), encoding="utf-8")

    _persist_evolution_handoff(
        str(final_path),
        {
            "status": "handed_off",
            "session_id": "session-demo",
            "validation_followup": {"status": "completed"},
        },
    )

    record = json.loads(final_path.read_text(encoding="utf-8"))
    assert record["run_id"] == "demo-run"
    assert record["evolution_handoff"]["status"] == "handed_off"
    assert record["evolution_handoff"]["validation_followup"]["status"] == "completed"


def test_handoff_after_run_passes_through_handed_off_no_skill_control_metadata(tmp_path, monkeypatch):
    enriched_path = tmp_path / "final-enriched.json"
    enriched_path.write_text(
        json.dumps(
            {
                "case_id": "demo-case",
                "run_id": "demo-run",
                "session_id": "session-demo",
                "session_segment_id": "c4f36f5d-60e2-45e7-b135-1bd397152ca6",
                "validation": {"status": "passed", "checks": []},
                "skill_injection": {"selected_skill_names": []},
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "evaluation.runs.run_remote_case.handoff_validated_run",
        lambda *_args, **_kwargs: {
            "status": "handed_off",
            "next_stage": "no_candidate",
            "feedback": {"selected_skills": [], "attribution_status": "no_selected_skills_control"},
            "session_id": "session-demo",
            "session_segment_id": "c4f36f5d-60e2-45e7-b135-1bd397152ca6",
        },
    )
    args = SimpleNamespace(
        evolve_after_run=True,
        skillclaw_url="http://127.0.0.1:30000",
        skillclaw_key="secret",
        evolve_url="http://127.0.0.1:8787",
    )

    result = _handoff_after_run(args, tmp_path, str(enriched_path))

    assert result["status"] == "handed_off"
    assert result["next_stage"] == "no_candidate"


@pytest.mark.anyio
async def test_validated_queue_only_returns_closed_session_feedback_pairs(tmp_path):
    server = object.__new__(EvolveServer)
    server.config = SimpleNamespace(storage_backend="local", local_root=str(tmp_path))
    server._mock = False
    server._bucket = LocalObjectStore(tmp_path)
    server._prefix = "default/"

    paired_segment = "c4f36f5d-60e2-45e7-b135-1bd397152ca6"
    waiting_segment = "c6e56f89-203f-4676-b528-ab172c0a027e"
    active_segment = "e47f0af2-daa8-4690-95ad-93458532d89c"
    server._bucket.put_object(
        f"default/sessions/{paired_segment}.json",
        json.dumps({"session_id": paired_segment, "session_segment_id": paired_segment, "segment_status": "closed"}),
    )
    server._bucket.put_object(
        f"default/sessions/{waiting_segment}.json",
        json.dumps({"session_id": waiting_segment, "session_segment_id": waiting_segment, "segment_status": "closed"}),
    )
    server._bucket.put_object(
        f"default/sessions/{active_segment}.json",
        json.dumps({"session_id": active_segment, "session_segment_id": active_segment, "segment_status": "active"}),
    )
    server._bucket.put_object(
        f"default/run_feedback/{paired_segment}/run.json",
        json.dumps(
            {
                "run_id": "run-1",
                "client_session_id": "client-1",
                "session_segment_id": paired_segment,
                "skill_feedback": [{"skill": "source-parser-state-machine-oob"}],
            }
        ),
    )

    sessions, session_keys, feedback_keys, queue = await server._load_validated_pairs()

    assert [item["session_segment_id"] for item in sessions] == [paired_segment]
    assert len(session_keys) == len(feedback_keys) == 1
    assert queue == {
        "ready_pairs": 1,
        "active_sessions": 1,
        "closed_sessions_waiting_feedback": 1,
        "stale_closed_sessions_without_feedback": 0,
        "feedback_waiting_session": 0,
    }


@pytest.mark.anyio
async def test_validated_queue_separates_stale_closed_sessions_without_feedback(tmp_path):
    server = object.__new__(EvolveServer)
    server.config = SimpleNamespace(storage_backend="local", local_root=str(tmp_path))
    server._mock = False
    server._bucket = LocalObjectStore(tmp_path)
    server._prefix = "default/"

    stale_segment = "c6e56f89-203f-4676-b528-ab172c0a027e"
    server._bucket.put_object(
        f"default/sessions/{stale_segment}.json",
        json.dumps(
            {
                "session_id": stale_segment,
                "session_segment_id": stale_segment,
                "segment_status": "closed",
                "segment_closed_at": "2020-01-01T00:00:00+00:00",
            }
        ),
    )

    sessions, session_keys, feedback_keys, queue = await server._load_validated_pairs()

    assert sessions == []
    assert session_keys == []
    assert feedback_keys == []
    assert queue == {
        "ready_pairs": 0,
        "active_sessions": 0,
        "closed_sessions_waiting_feedback": 0,
        "stale_closed_sessions_without_feedback": 1,
        "feedback_waiting_session": 0,
    }


@pytest.mark.anyio
async def test_evolve_accepts_run_scoped_feedback(tmp_path):
    server = object.__new__(EvolveServer)
    server.config = SimpleNamespace(storage_backend="local", local_root=str(tmp_path))
    server._mock = False
    server._bucket = LocalObjectStore(tmp_path)
    server._prefix = "default/"
    segment_id = "c4f36f5d-60e2-45e7-b135-1bd397152ca6"
    app = server.create_http_app()

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/v1/run-feedback",
            json={
                "run_id": "run-1",
                "client_session_id": "client-1",
                "session_segment_id": segment_id,
                "skill_feedback": [],
            },
        )

    assert response.status_code == 200
    assert response.json()["session_segment_id"] == segment_id
    stored = list((tmp_path / "default" / "run_feedback" / segment_id).glob("*.json"))
    assert len(stored) == 1

    await server._write_consumption_receipts(
        [
            {
                "validator_feedback": [
                    {
                        "run_id": "run-1",
                        "client_session_id": "client-1",
                        "session_segment_id": segment_id,
                    }
                ]
            }
        ],
        [{"action": "queued_for_validation", "uploaded": False, "session_ids": [segment_id]}],
    )
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        receipt = await client.get(
            "/v1/run-feedback/status",
            params={"run_id": "run-1", "session_segment_id": segment_id},
        )
    assert receipt.json()["status"] == "consumed"
    assert receipt.json()["candidate_count"] == 1


def test_build_replay_cases_prefers_final_json_turns():
    server = object.__new__(EvolveServer)
    sessions = [
        {
            "session_id": "session-a",
            "turns": [
                {
                    "turn_num": 1,
                    "prompt_text": "analyze binary",
                    "response_text": "I'll first inspect the workspace structure and identify CGI binaries.",
                    "raw_turn_kind": "final",
                    "attribution_eligible": True,
                    "tool_calls": [],
                    "tool_results": [],
                },
                {
                    "turn_num": 7,
                    "prompt_text": "analyze binary",
                    "response_text": "<bash>\nls -la\n</bash>",
                    "raw_turn_kind": "final",
                    "attribution_eligible": True,
                    "tool_calls": [],
                    "tool_results": [],
                },
                {
                    "turn_num": 9,
                    "prompt_text": "analyze binary",
                    "response_text": json.dumps(
                        {
                            "predicted_cves": ["CVE-2026-2529"],
                            "predicted_files": ["vul_file/wireless.cgi"],
                            "predicted_functions": ["sub_402E04"],
                            "root_cause": "unsanitized command construction",
                            "evidence": "page=DeleteMac flows into system()",
                            "confidence": "high",
                        }
                    ),
                    "raw_turn_kind": "final",
                    "attribution_eligible": True,
                    "tool_calls": [],
                    "tool_results": [],
                },
            ],
        }
    ]

    cases = server._build_replay_cases(sessions)

    assert len(cases) == 1
    assert cases[0]["turn_num"] == 9
    assert "predicted_cves" in cases[0]["reference_response"]


def test_build_replay_cases_skips_shell_only_turns_even_without_json():
    server = object.__new__(EvolveServer)
    sessions = [
        {
            "session_id": "session-b",
            "turns": [
                {
                    "turn_num": 2,
                    "prompt_text": "analyze firmware cgi",
                    "response_text": "<bash>\nfind . -type f | head -20\n</bash>",
                    "raw_turn_kind": "final",
                    "attribution_eligible": True,
                    "tool_calls": [],
                    "tool_results": [],
                },
                {
                    "turn_num": 8,
                    "prompt_text": "analyze firmware cgi",
                    "response_text": (
                        "The likely command-injection path sits in wireless.cgi. "
                        "The handler branches on page, reads HTTP parameters from the POST body, "
                        "formats a shell command, and then executes it through system()."
                    ),
                    "raw_turn_kind": "final",
                    "attribution_eligible": True,
                    "tool_calls": [],
                    "tool_results": [],
                },
            ],
        }
    ]

    cases = server._build_replay_cases(sessions)

    assert len(cases) == 1
    assert cases[0]["turn_num"] == 8


def test_replay_messages_include_reference_response_and_no_tool_retry():
    messages = ReplayGateWorker._build_replay_messages(
        {
            "instruction": "Return one JSON object with predicted_files and root_cause.",
            "reference_response": "{\"predicted_files\": [\"wireless.cgi\"], \"root_cause\": \"unsanitized system() path\"}",
        },
        {
            "name": "embedded-cgi-command-injection-triage",
            "description": "desc",
            "content": "- focus on dispatch to sink",
            "category": "general",
        },
    )

    assert messages[0]["role"] == "system"
    assert "Do not emit tool calls" in messages[0]["content"]
    assert "Return only the final answer" in messages[0]["content"]
    assert messages[1]["role"] == "user"
    assert "predicted_files" in messages[2]["content"]
    assert "Do not output bash" in messages[2]["content"]


def test_replay_messages_add_direct_answer_fallback_without_reference():
    messages = ReplayGateWorker._build_replay_messages(
        {"instruction": "Find the vulnerability and answer in JSON."},
        None,
    )

    assert len(messages) == 3
    assert messages[-1]["role"] == "user"
    assert "Replay this task without tools" in messages[-1]["content"]
    assert "Do not output bash" in messages[-1]["content"]


def test_replay_gate_acceptance_requires_strict_improvement():
    assert ReplayGateWorker._accept_replay_candidate(
        candidate_mean=1.0,
        baseline_mean=0.9,
        threshold=0.75,
    )
    assert not ReplayGateWorker._accept_replay_candidate(
        candidate_mean=1.0,
        baseline_mean=1.0,
        threshold=0.75,
    )
    assert not ReplayGateWorker._accept_replay_candidate(
        candidate_mean=0.7,
        baseline_mean=0.2,
        threshold=0.75,
    )
