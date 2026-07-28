from __future__ import annotations

import json

from evaluation.postprocess.finalize_record import finalize_record, main


def test_finalize_record_attaches_injection(tmp_path):
    case = {"id": "demo-case"}
    final_record = {
        "case_id": "demo-case",
        "run": {
            "start": "2026-07-01T12:19:32+00:00",
            "end": "2026-07-01T12:20:47+00:00",
        },
        "score": 8.0,
        "max_score": 10.0,
        "checks": {},
        "validation": {"status": "passed", "checks": []},
    }
    injection_rows = [
        {
            "timestamp": "2026-07-01 20:20:31",
            "session_id": "target",
            "turn": 2,
            "selected_skill_names": ["source-parser-state-machine-oob"],
        }
    ]
    updated = finalize_record(case=case, final_record=final_record, injection_value=injection_rows)
    assert updated["session_id"] == "target"
    assert updated["session_id_source"] == "inferred_from_injection_log"
    assert updated["selected_skill_names"] == ["source-parser-state-machine-oob"]
    assert updated["skill_injection"]["selected_skill_names"] == ["source-parser-state-machine-oob"]


def test_finalize_record_accepts_session_snapshot(tmp_path):
    case = {"id": "demo-case"}
    final_record = {
        "case_id": "demo-case",
        "run": {
            "start": "2026-07-25T12:00:00+00:00",
            "end": "2026-07-25T12:05:00+00:00",
        },
        "score": 8.0,
        "max_score": 10.0,
        "checks": {},
        "validation": {"status": "passed", "checks": []},
    }
    session_snapshot = {
        "session_id": "snapshot-session",
        "timestamp": "2026-07-25T12:07:02Z",
        "turns": [
            {
                "turn_num": 9,
                "selected_skill_names": [
                    "source-parser-state-machine-oob",
                    "vuln-hunting",
                ],
                "skill_injection": {
                    "injection_mode": "inline",
                    "top_k": 3,
                    "skill_prompt_hash": "abc123",
                    "available_skill_count": 35,
                },
                "prm_score": 1.0,
            }
        ],
    }

    updated = finalize_record(case=case, final_record=final_record, injection_value=session_snapshot)
    assert updated["session_id"] == "snapshot-session"
    assert updated["session_id_source"] == "inferred_from_injection_log"
    assert updated["selected_skill_names"] == [
        "source-parser-state-machine-oob",
        "vuln-hunting",
    ]
    assert updated["injection_mode"] == "inline"
    assert updated["skill_top_k"] == 3
    assert updated["skill_prompt_hash"] == "abc123"
    assert updated["available_skill_count"] == 35
    assert updated["skill_injection"]["selected_skill_names"] == [
        "source-parser-state-machine-oob",
        "vuln-hunting",
    ]
    assert updated["skill_injection"]["injection_mode"] == "inline"
    assert updated["skill_injection"]["available_skill_count"] == 35


def test_finalize_main_writes_finalized_and_compare_outputs(tmp_path):
    case_path = tmp_path / "case.json"
    before_path = tmp_path / "before.json"
    final_path = tmp_path / "final.json"
    injection_path = tmp_path / "injection.json"
    case_path.write_text(json.dumps({"id": "demo-case"}), encoding="utf-8")
    before_path.write_text(
        json.dumps(
            {
                "case_id": "demo-case",
                "score": 8.0,
                "max_score": 10.0,
                "checks": {"cve": {"hit": False}},
                "validation": {"status": "passed", "checks": []},
                "feedback": {"decision": "neutral", "quality_flags": ["cve_identity_miss"]},
            }
        ),
        encoding="utf-8",
    )
    final_path.write_text(
        json.dumps(
            {
                "case_id": "demo-case",
                "run": {
                    "start": "2026-07-01T12:19:32+00:00",
                    "end": "2026-07-01T12:20:47+00:00",
                },
                "score": 10.0,
                "max_score": 10.0,
                "checks": {"cve": {"hit": True}},
                "validation": {"status": "passed", "checks": []},
            }
        ),
        encoding="utf-8",
    )
    injection_path.write_text(
        json.dumps(
            [
                {
                    "timestamp": "2026-07-01 20:20:31",
                    "session_id": "target",
                    "turn": 2,
                    "selected_skill_names": ["source-parser-state-machine-oob"],
                }
            ]
        ),
        encoding="utf-8",
    )

    finalized_path = tmp_path / "final-enriched.json"
    compare_json_path = tmp_path / "compare.json"
    compare_md_path = tmp_path / "compare.md"
    rc = main(
        [
            str(case_path),
            str(final_path),
            str(injection_path),
            "--out",
            str(finalized_path),
            "--before",
            str(before_path),
            "--compare-json-out",
            str(compare_json_path),
            "--compare-md-out",
            str(compare_md_path),
        ]
    )
    assert rc == 0
    assert finalized_path.exists()
    assert compare_json_path.exists()
    assert compare_md_path.exists()
    compare = json.loads(compare_json_path.read_text(encoding="utf-8"))
    assert compare["delta"]["exact_cve_improved"] is True


def test_finalize_main_accepts_session_snapshot_directory(tmp_path):
    case_path = tmp_path / "case.json"
    final_path = tmp_path / "final.json"
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()
    snapshot_path = sessions_dir / "snapshot-session.json"

    case_path.write_text(json.dumps({"id": "demo-case"}), encoding="utf-8")
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
    snapshot_path.write_text(
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

    finalized_path = tmp_path / "final-enriched.json"
    rc = main(
        [
            str(case_path),
            str(final_path),
            str(sessions_dir),
            "--out",
            str(finalized_path),
        ]
    )
    assert rc == 0
    finalized = json.loads(finalized_path.read_text(encoding="utf-8"))
    assert finalized["session_id"] == "snapshot-session"
    assert finalized["skill_injection"]["selected_skill_names"] == ["source-parser-state-machine-oob"]

