import json
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from evaluation.evolution import EvolutionHandoffError, build_run_feedback_bundle, handoff_validated_run
from evaluation.runs.run_remote_case import (
    _default_local_session_dir,
    build_manual_claude_command,
    build_remote_layout,
    build_remote_prepare_command,
    build_remote_render_prompt_command,
    build_remote_run_command,
    enrich_downloaded_final,
)
from evolve_server.engines.workflow import EvolveServer
from skillclaw.object_store import LocalObjectStore
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
