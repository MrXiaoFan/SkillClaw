from __future__ import annotations

import json

from experiment_scripts.finalize_experiment_record import finalize_record, main


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
    assert updated["skill_injection"]["selected_skill_names"] == ["source-parser-state-machine-oob"]


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
                "feedback": {"decision": "neutral", "quality_flags": ["cve_calibration_miss"]},
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

    finalized_path = tmp_path / "final-with-injection.json"
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
