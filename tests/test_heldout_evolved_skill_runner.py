from __future__ import annotations

import json
from pathlib import Path

from evaluation.runs.run_heldout_evolved_skill import (
    _audit_candidate_leakage,
    _audit_source_quality,
    _build_parser as _build_heldout_parser,
    _heldout_experiment_slug,
    _load_segment_sessions,
    _make_heldout_run_id,
    _require_successful_remote_run,
)
from evaluation.runs.run_remote_case import _build_parser as _build_remote_case_parser


def test_load_segment_sessions_respects_session_segment_id(tmp_path: Path) -> None:
    record_log = tmp_path / "conversations.jsonl"
    record_log.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "session_id": "sid-1",
                        "session_segment_id": "seg-a",
                        "turn": 1,
                        "timestamp": "2026-08-25 10:00:00",
                        "instruction_text": "find vuln",
                        "response_text": "first answer",
                        "selected_skill_names": ["skill-a"],
                    }
                ),
                json.dumps(
                    {
                        "session_id": "sid-1",
                        "session_segment_id": "seg-b",
                        "turn": 1,
                        "timestamp": "2026-08-25 10:05:00",
                        "instruction_text": "other task",
                        "response_text": "second answer",
                        "selected_skill_names": ["skill-b"],
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    sessions = _load_segment_sessions(
        record_log,
        allowed_segment_ids={"seg-a"},
        fallback_session_ids={"sid-1"},
    )

    assert len(sessions) == 1
    assert sessions[0]["session_id"] == "sid-1"
    assert sessions[0]["session_segment_id"] == "seg-a"
    assert sessions[0]["turns"][0]["injected_skills"] == ["skill-a"]


def test_audit_candidate_leakage_flags_direct_ground_truth_terms() -> None:
    candidate_skill = {
        "name": "candidate-skill",
        "description": "Focus on formWriteFacMac in Tenda F453.",
        "content": "Look for doSystemCmd, but also formWriteFacMac and CVE-2026-4554.",
    }
    heldout_case = {
        "case_id": "f453-httpd-cmdinject-formWriteFacMac",
        "ground_truth": {
            "cves": ["CVE-2026-4554"],
            "files": ["vul_file/httpd"],
            "functions": ["formWriteFacMac", "doSystemCmd"],
        },
    }

    audit = _audit_candidate_leakage(candidate_skill, [heldout_case])

    assert len(audit) == 1
    assert audit[0]["case_id"] == "f453-httpd-cmdinject-formWriteFacMac"
    assert audit[0]["blocked"] is True
    assert "CVE-2026-4554" in audit[0]["matched_terms"]
    assert "formWriteFacMac" in audit[0]["matched_terms"]


def test_audit_candidate_leakage_ignores_generic_binary_names() -> None:
    candidate_skill = {
        "name": "candidate-skill",
        "description": "Analyze embedded webs binaries carefully.",
        "content": "Look at vul_file/webs and confirm strcpy reachability before answering.",
    }
    heldout_case = {
        "case_id": "f9k1122-webs-overflow-formWlanSetup",
        "ground_truth": {
            "cves": ["CVE-2026-5608"],
            "files": ["vul_file/webs"],
            "functions": ["formWlanSetup", "strcpy"],
        },
    }

    audit = _audit_candidate_leakage(candidate_skill, [heldout_case])

    assert len(audit) == 1
    assert audit[0]["case_id"] == "f9k1122-webs-overflow-formWlanSetup"
    assert audit[0]["blocked"] is False
    assert audit[0]["matched_terms"] == []


def test_heldout_run_id_includes_experiment_namespace(tmp_path: Path) -> None:
    slug_a = _heldout_experiment_slug(tmp_path / "exp-a", "abc123")
    slug_b = _heldout_experiment_slug(tmp_path / "exp-b", "abc123")

    run_a = _make_heldout_run_id(
        experiment_slug=slug_a,
        case_slug="f9k1122-webs-overflow-formWlanSetup",
        condition="candidate-skill",
        repeat=1,
    )
    run_b = _make_heldout_run_id(
        experiment_slug=slug_b,
        case_slug="f9k1122-webs-overflow-formWlanSetup",
        condition="candidate-skill",
        repeat=1,
    )

    assert run_a != run_b
    assert "exp-a" in run_a
    assert "exp-b" in run_b


def test_remote_runners_default_to_vm_li_path_profile() -> None:
    heldout_parser = _build_heldout_parser()
    heldout_args = heldout_parser.parse_args(
        ["run-heldout", "--candidate-json", "candidate.json", "--heldout-case", "benchmarks/cases/demo.json"]
    )
    assert heldout_args.remote_path_profile == "vm-li"

    remote_parser = _build_remote_case_parser()
    remote_args = remote_parser.parse_args(["prepare-manual", "benchmarks/cases/demo.json"])
    assert remote_args.remote_path_profile == "vm-li"


def test_audit_source_quality_blocks_all_function_identity_miss() -> None:
    records = [
        (
            Path("a.json"),
            {
                "score": 2.0,
                "max_score": 10.0,
                "checks": {"function": {"hit": False}, "evidence": {"hit": False}, "root_cause": {"hit": False}},
                "feedback": {"quality_flags": ["function_identity_miss", "cve_identity_miss"]},
            },
        ),
        (
            Path("b.json"),
            {
                "score": 4.5,
                "max_score": 10.0,
                "checks": {"function": {"hit": True}, "evidence": {"hit": True}, "root_cause": {"hit": False}},
                "feedback": {"quality_flags": ["function_identity_miss"]},
            },
        ),
    ]

    audit = _audit_source_quality(records)

    assert audit["blocked"] is True
    assert "all_source_runs_have_function_identity_miss" in audit["issues"]
    assert audit["summary"]["source_run_count"] == 2
    assert audit["summary"]["function_identity_miss_count"] == 2


def test_audit_source_quality_allows_mixed_source_quality() -> None:
    records = [
        (
            Path("a.json"),
            {
                "score": 4.5,
                "max_score": 10.0,
                "checks": {"function": {"hit": True}, "evidence": {"hit": True}, "root_cause": {"hit": False}},
                "feedback": {"quality_flags": ["function_identity_miss"]},
            },
        ),
        (
            Path("b.json"),
            {
                "score": 8.0,
                "max_score": 10.0,
                "checks": {"function": {"hit": True}, "evidence": {"hit": True}, "root_cause": {"hit": True}},
                "feedback": {"quality_flags": []},
            },
        ),
    ]

    audit = _audit_source_quality(records)

    assert audit["blocked"] is False
    assert "all_source_runs_have_function_identity_miss" not in audit["issues"]
    assert audit["summary"]["root_cause_hit_count"] == 1


def test_audit_source_quality_blocks_without_any_root_cause_hit() -> None:
    records = [
        (
            Path("a.json"),
            {
                "score": 6.0,
                "max_score": 10.0,
                "checks": {"function": {"hit": True}, "evidence": {"hit": True}, "root_cause": {"hit": False}},
                "feedback": {"quality_flags": ["cve_identity_miss"]},
            },
        ),
        (
            Path("b.json"),
            {
                "score": 2.0,
                "max_score": 10.0,
                "checks": {"function": {"hit": False}, "evidence": {"hit": False}, "root_cause": {"hit": False}},
                "feedback": {"quality_flags": ["function_identity_miss", "cve_identity_miss"]},
            },
        ),
    ]

    audit = _audit_source_quality(records)

    assert audit["blocked"] is True
    assert "no_source_run_has_root_cause_hit" in audit["issues"]
    assert audit["summary"]["root_cause_hit_count"] == 0


def test_require_successful_remote_run_accepts_downloaded_final(tmp_path: Path) -> None:
    final_path = tmp_path / "final.json"
    final_path.write_text("{}", encoding="utf-8")

    _require_successful_remote_run(
        {"run_result": {"exit_status": 0}, "local_final_enriched": str(final_path)},
        run_id="run-ok",
        output_dir=tmp_path,
    )


def test_require_successful_remote_run_records_failed_preflight(tmp_path: Path) -> None:
    result = {"run_result": {"exit_status": 1, "stderr": "preflight failed"}}

    try:
        _require_successful_remote_run(result, run_id="run-failed", output_dir=tmp_path)
    except RuntimeError as exc:
        assert "run-failed" in str(exc)
    else:
        raise AssertionError("failed remote run must raise")

    failure_path = tmp_path / "failed_run-failed.json"
    assert failure_path.is_file()
    assert "preflight failed" in failure_path.read_text(encoding="utf-8")
