import json
import shutil
import subprocess
import sys
from argparse import Namespace
from datetime import datetime, timedelta
from pathlib import Path

from evaluation.cases.loader import DEFAULT_SCORING, load_case_definition, resolve_blind_agent_root, resolve_source_root
from evaluation.utils.check_case_runtime import check_case_environment, infer_claude_provider
from evaluation.postprocess.compare_records import compare_records, render_markdown
from evaluation.postprocess.finalize_record import attach_injection
from evaluation.utils.audit_run_layout import audit_run_layout
from evaluation.utils.backfill_run_manifests import backfill_run_manifest
from evaluation.runs.run_single_case import extract_json_object, infer_session_id_from_injection, run_case
from evaluation.runs.run_case_validation import run_validators
from evaluation.utils.smoke_check_cases import smoke_cases
from evaluation.runs.score_case_output import score_output
from evaluation.postprocess.finalize_record import _select_injection, _select_injection_history, _select_validation
from evaluation.reporting.feedback.build_gate_report import build_gate_report, decide_gate
from evaluation.reporting.feedback.build_feedback_bundle import (
    build_feedback_bundles,
    write_json as write_bundle_json,
    write_markdown as write_bundle_markdown,
)
from evaluation.utils.render_case_prompt import FINAL_ANSWER_GUARD, get_case_prompt, render_guide
from evaluation.reporting.current.refresh_reports import refresh_reports
from evaluation.runs.run_case_batch import run_batch
from evaluation.utils.bundle_script_bridge import resolve_bundle_script, run_bundle_script
from evaluation.reporting.research.build_research_claims import build_claims, write_markdown as write_claim_markdown
from evaluation.reporting.current.build_result_matrix import collect_rows, write_csv, write_markdown
from evaluation.reporting.feedback.build_skill_summary import build_skill_feedback
from evaluation.validation.core import assess_skill_relevance, build_feedback
from skillclaw.skill_manager import SkillManager


def _write_test_skill(skills_dir, name, description, body="workflow"):
    skill_dir = skills_dir / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        "\n".join(
            [
                "---",
                f"name: {name}",
                f'description: "{description}"',
                "category: general",
                "---",
                "",
                f"# {name}",
                "",
                body,
            ]
        ),
        encoding="utf-8",
    )


def test_load_case_definition_applies_default_scoring(tmp_path):
    case_path = tmp_path / "case.json"
    case_path.write_text(
        json.dumps(
            {
                "case_id": "demo-default-score",
                "target": {"project": "demo", "version": "1.0"},
                "ground_truth": {
                    "files": ["demo.c"],
                    "functions": ["demo"],
                    "vulnerability_type": "demo",
                },
            }
        ),
        encoding="utf-8",
    )

    case = load_case_definition(case_path)

    assert case["scoring"] == DEFAULT_SCORING


def test_resolve_source_root_prefers_profiled_or_existing_candidate(tmp_path, monkeypatch):
    local_root = tmp_path / "local-target"
    local_root.mkdir()
    case_path = tmp_path / "case.json"
    case_path.write_text(
        json.dumps(
            {
                "case_id": "demo-path-profile",
                "target": {
                    "project": "demo",
                    "version": "1.0",
                    "source_root": "/remote/demo",
                    "source_root_candidates": [str(local_root)],
                    "source_root_by_profile": {
                        "vm": "/vm/demo",
                        "local": str(local_root),
                    },
                },
                "ground_truth": {
                    "files": [],
                    "functions": ["demo"],
                    "vulnerability_type": "demo",
                },
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("SKILLCLAW_PATH_PROFILE", "local")
    case = load_case_definition(case_path)

    assert resolve_source_root(case) == local_root.resolve()


def test_resolve_blind_agent_root_defaults_to_sibling_workspace(tmp_path):
    source_root = tmp_path / "tcpdump-4.9.1"
    source_root.mkdir()
    case_path = tmp_path / "case.json"
    case_path.write_text(
        json.dumps(
            {
                "case_id": "tcpdump-4.9.1-cve-2018-14469",
                "target": {
                    "project": "tcpdump",
                    "version": "4.9.1",
                    "source_root": str(source_root),
                },
                "ground_truth": {
                    "files": ["print-isakmp.c"],
                    "functions": ["ikev1_n_print"],
                    "vulnerability_type": "buffer over-read",
                },
            }
        ),
        encoding="utf-8",
    )

    case = load_case_definition(case_path)

    assert resolve_blind_agent_root(case) == (
        tmp_path / "blind_workspaces" / "tcpdump-4.9.1-cve-2018-14469"
    ).resolve()
    assert resolve_blind_agent_root(case) != source_root.resolve()


def test_load_case_definition_applies_validator_defaults(tmp_path):
    case_path = tmp_path / "case.json"
    case_path.write_text(
        json.dumps(
            {
                "case_id": "demo-default-validator",
                "target": {"project": "demo", "version": "1.0"},
                "ground_truth": {
                    "files": ["demo.c"],
                    "functions": ["demo"],
                    "vulnerability_type": "demo",
                },
                "validators": [
                    {"name": "match", "type": "content_match"},
                    {"name": "asan", "type": "asan_command", "command": "true"},
                ],
            }
        ),
        encoding="utf-8",
    )

    case = load_case_definition(case_path)

    assert case["validators"][0]["source"] == "agent_output"
    assert case["validators"][0]["use_ground_truth"] is True
    assert case["validators"][0]["match"] == "any"
    assert case["validators"][0]["enabled"] is True
    assert case["validators"][0]["allow_failure"] is False
    assert case["validators"][1]["expect_crash"] is True
    assert case["validators"][1]["stack_match"] == "any"


def test_score_case_output_hits_ground_truth():
    case = {
        "case_id": "demo",
        "ground_truth": {
            "cves": ["CVE-0000-0001"],
            "files": ["HTMLparser.c"],
            "functions": ["htmlParseTryOrFinish"],
            "root_cause": "avail guard before in->cur[2]",
            "required_evidence": ["avail", "in->cur[2]"],
        },
        "scoring": {
            "max_score": 10,
            "weights": {"cve": 2, "file": 2, "function": 3, "root_cause": 2, "evidence": 1},
        },
    }
    output = """{
      "predicted_cves": ["CVE-0000-0001"],
      "predicted_files": ["HTMLparser.c"],
      "predicted_functions": ["htmlParseTryOrFinish"],
      "root_cause": "avail guard is too weak before in->cur[2]",
      "evidence": ["avail", "in->cur[2]"]
    }"""

    result = score_output(case, output)

    assert result["score"] == 10
    assert result["checks"]["function"]["hit"] is True


def test_score_case_output_extracts_claude_json_result_field():
    case = {
        "case_id": "demo",
        "ground_truth": {
            "cves": ["CVE-0000-0001"],
            "files": ["HTMLparser.c"],
            "functions": ["htmlParseTryOrFinish"],
            "root_cause": "weak avail guard before in->cur[2]",
            "required_evidence": ["avail", "in->cur[2]"],
        },
        "scoring": {
            "max_score": 10,
            "weights": {"cve": 2, "file": 2, "function": 3, "root_cause": 2, "evidence": 1},
        },
    }
    output = json.dumps(
        {
            "type": "result",
            "subtype": "success",
            "result": """```json
{
  "predicted_cves": ["CVE-0000-0001"],
  "predicted_files": ["HTMLparser.c"],
  "predicted_functions": ["htmlParseTryOrFinish"],
  "root_cause": "weak avail guard before in->cur[2]",
  "evidence": ["avail", "in->cur[2]"]
}
```""",
        }
    )

    result = score_output(case, output)

    assert result["score"] == 10
    assert result["predictions"]["cves"] == ["CVE-0000-0001"]


def test_score_case_output_ignores_unscoreable_claude_error_wrapper():
    case = {
        "case_id": "demo",
        "ground_truth": {
            "cves": ["CVE-0000-0001"],
            "files": ["HTMLparser.c"],
            "functions": ["htmlParseTryOrFinish"],
            "root_cause": "parser state machine lookahead reads",
            "required_evidence": ["in->cur[2]", "avail"],
        },
        "scoring": {
            "max_score": 10,
            "weights": {"cve": 2, "file": 2, "function": 3, "root_cause": 2, "evidence": 1},
        },
    }
    output = json.dumps(
        {
            "type": "result",
            "subtype": "error_max_budget_usd",
            "is_error": True,
            "num_turns": 12,
            "fast_mode_state": "off",
            "errors": ["Reached maximum budget"],
        }
    )

    result = score_output(case, output)

    assert result["score"] == 0
    assert result["predictions"]["raw_text"] == []


def test_run_case_validation_source_contains(tmp_path):
    (tmp_path / "HTMLparser.c").write_text(
        "static void htmlParseTryOrFinish(void) { if (avail < 2) in->cur[2]; }\n",
        encoding="utf-8",
    )
    case = {
        "case_id": "demo",
        "validators": [
            {
                "name": "source",
                "type": "source_contains",
                "file": "HTMLparser.c",
                "patterns": ["htmlParseTryOrFinish", "avail", "in->cur[2]"],
            }
        ],
    }

    result = run_validators(case, tmp_path, skip_commands=True)

    assert result["status"] == "passed"
    assert result["checks"][0]["status"] == "passed"


def test_run_case_validation_artifact_exists(tmp_path):
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()
    payload = artifacts_dir / "demo.bin"
    payload.write_bytes(b"A" * 32)
    case = {
        "case_id": "demo-artifact",
        "validators": [
            {
                "name": "artifact",
                "type": "artifact_exists",
                "path": "artifacts/demo.bin",
                "min_size_bytes": 16,
            }
        ],
    }

    result = run_validators(case, tmp_path, skip_commands=True)

    assert result["status"] == "passed"
    assert result["checks"][0]["status"] == "passed"
    assert result["checks"][0]["size_bytes"] == 32


def test_run_case_validation_artifact_exec(tmp_path):
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()
    script = artifacts_dir / "run.py"
    script.write_text("print('TRIGGER_OK')\n", encoding="utf-8")
    case = {
        "case_id": "demo-artifact-exec",
        "validators": [
            {
                "name": "artifact-exec",
                "type": "artifact_exec",
                "path": "artifacts/run.py",
                "exec_mode": "python",
                "success_markers": ["TRIGGER_OK"],
                "require_markers": True,
                "timeout_seconds": 10,
            }
        ],
    }

    result = run_validators(case, tmp_path, skip_commands=False)

    assert result["status"] == "passed"
    assert result["checks"][0]["status"] == "passed"
    assert "TRIGGER_OK" in result["checks"][0]["matched_markers"]


def test_run_case_validation_artifact_exec_expect_crash(tmp_path):
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()
    script = artifacts_dir / "run.py"
    script.write_text(
        "import sys\n"
        "sys.stderr.write('AddressSanitizer: heap-buffer-overflow in DemoFrame\\n')\n"
        "raise SystemExit(134)\n",
        encoding="utf-8",
    )
    case = {
        "case_id": "demo-artifact-crash",
        "validators": [
            {
                "name": "artifact-exec-crash",
                "type": "artifact_exec",
                "path": "artifacts/run.py",
                "exec_mode": "python",
                "success_markers": ["AddressSanitizer", "DemoFrame"],
                "require_markers": True,
                "expect_crash": True,
                "timeout_seconds": 10,
            }
        ],
    }

    result = run_validators(case, tmp_path, skip_commands=False)

    assert result["status"] == "passed"
    assert result["checks"][0]["status"] == "passed"
    assert result["checks"][0]["returncode"] == 134
    assert result["checks"][0]["expect_crash"] is True


def test_run_case_validation_artifact_exec_requires_all_markers_by_default(tmp_path):
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()
    script = artifacts_dir / "run.py"
    script.write_text(
        "import sys\n"
        "sys.stderr.write('AddressSanitizer: heap-buffer-overflow only\\n')\n"
        "raise SystemExit(134)\n",
        encoding="utf-8",
    )
    case = {
        "case_id": "demo-artifact-crash-missing-markers",
        "validators": [
            {
                "name": "artifact-exec-crash-missing",
                "type": "artifact_exec",
                "path": "artifacts/run.py",
                "exec_mode": "python",
                "success_markers": ["AddressSanitizer", "DemoFrame"],
                "expect_crash": True,
                "timeout_seconds": 10,
            }
        ],
    }

    result = run_validators(case, tmp_path, skip_commands=False)

    assert result["status"] == "failed"
    assert result["checks"][0]["status"] == "failed"
    assert result["checks"][0]["marker_match"] == "all"
    assert result["checks"][0]["missing_markers"] == ["DemoFrame"]
    assert result["checks"][0]["reason"] == "missing required success markers"


def test_run_case_validation_artifact_exec_supports_any_marker_mode(tmp_path):
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()
    script = artifacts_dir / "run.py"
    script.write_text(
        "import sys\n"
        "sys.stderr.write('AddressSanitizer: heap-buffer-overflow only\\n')\n"
        "raise SystemExit(134)\n",
        encoding="utf-8",
    )
    case = {
        "case_id": "demo-artifact-crash-any-marker",
        "validators": [
            {
                "name": "artifact-exec-crash-any",
                "type": "artifact_exec",
                "path": "artifacts/run.py",
                "exec_mode": "python",
                "success_markers": ["AddressSanitizer", "DemoFrame"],
                "marker_match": "any",
                "expect_crash": True,
                "timeout_seconds": 10,
            }
        ],
    }

    result = run_validators(case, tmp_path, skip_commands=False)

    assert result["status"] == "passed"
    assert result["checks"][0]["status"] == "passed"
    assert result["checks"][0]["marker_match"] == "any"
    assert "AddressSanitizer" in result["checks"][0]["matched_markers"]


def test_run_case_validation_command_validator(tmp_path):
    code = "print('LOGIC_CONFIRM_OK libxml2-state-machine-window')"
    case = {
        "case_id": "demo-command",
        "validators": [
            {
                "name": "logic-confirm",
                "type": "command",
                "command": f'"{sys.executable}" -c {json.dumps(code)}',
                "timeout_seconds": 10,
            }
        ],
    }

    result = run_validators(case, tmp_path, skip_commands=False)

    assert result["status"] == "passed"
    check = result["checks"][0]
    assert check["status"] == "passed"
    assert "LOGIC_CONFIRM_OK" in check["stdout_tail"]


def test_tcpdump_frag6_poc_generator_writes_truncated_fragment_header_pcap(tmp_path):
    script = (
        Path(__file__).resolve().parents[1]
        / "benchmarks"
        / "confirmations"
        / "tcpdump-4.9.1-cve-2017-13031"
        / "generate_confirmation_input.py"
    )
    output = tmp_path / "frag6.pcap"

    subprocess.run([sys.executable, str(script), str(output)], check=True)

    blob = output.read_bytes()
    assert len(blob) >= 64
    assert blob[:4] == bytes.fromhex("d4c3b2a1")
    assert bytes.fromhex("86dd") in blob


def test_tcpdump_isakmp_poc_generator_writes_udp500_replay_status_pcap(tmp_path):
    script = (
        Path(__file__).resolve().parents[1]
        / "benchmarks"
        / "confirmations"
        / "tcpdump-4.9.1-cve-2018-14469"
        / "generate_confirmation_input.py"
    )
    output = tmp_path / "isakmp.pcap"

    subprocess.run([sys.executable, str(script), str(output)], check=True)

    blob = output.read_bytes()
    assert len(blob) >= 80
    assert blob[:4] == bytes.fromhex("d4c3b2a1")
    assert bytes.fromhex("0800") in blob
    assert bytes.fromhex("01f401f4") in blob


def test_finalize_record_selects_session_injection():
    rows = [
        {"session_id": "a", "selected_skill_names": ["old"]},
        {"session_id": "b", "selected_skill_names": ["new"]},
    ]

    result = _select_injection(rows, "b")

    assert result == rows[1]


def test_finalize_record_selects_session_injection_history():
    rows = [
        {"session_id": "a", "selected_skill_names": ["old"]},
        {"session_id": "b", "selected_skill_names": ["first"]},
        {"session_id": "b", "selected_skill_names": ["latest"]},
    ]

    result = _select_injection_history(rows, "b")

    assert result == rows[1:]


def test_finalize_record_selects_latest_case_validation():
    rows = [
        {"case_id": "other", "validator_mode": "case-level", "status": "failed"},
        {"case_id": "demo", "validator_mode": "case-level", "status": "partial"},
        {"case_id": "demo", "validator_mode": "case-level", "status": "passed"},
    ]

    result = _select_validation(rows, "demo")

    assert result == rows[2]


def test_attach_skill_injection_updates_final_record_feedback():
    case = {
        "case_id": "demo",
        "target": {"project": "parser", "binary": "demo"},
        "ground_truth": {
            "vulnerability_type": "state machine oob",
            "root_cause": "source parser state machine out-of-bounds read",
        },
    }
    final_record = {
        "case_id": "demo",
        "score": 8,
        "max_score": 10,
        "validation": {"status": "passed"},
        "skill_injection": None,
        "skill_relevance": {"status": "no_selected_skills"},
    }
    injection_rows = [
        {"session_id": "old", "selected_skill_names": ["other"]},
        {
            "session_id": "target",
            "injection_mode": "inline",
            "selected_skill_names": ["source-parser-state-machine-oob"],
            "available_skill_count": 35,
        },
    ]

    updated = attach_injection(
        final_record=final_record,
        case=case,
        injection_value=injection_rows,
        session_id="target",
    )

    assert updated["session_id"] == "target"
    assert updated["skill_injection"] == injection_rows[1]
    assert updated["skill_injection_history"] == [injection_rows[1]]
    assert updated["skill_relevance"]["status"] == "has_task_relevant_skill"
    assert updated["feedback"]["selected_skills"] == ["source-parser-state-machine-oob"]
    assert updated["session_id_source"] == "explicit"


def test_attach_skill_injection_can_infer_session_id_from_run_window():
    case = {
        "case_id": "demo",
        "target": {"project": "parser", "binary": "demo"},
        "ground_truth": {
            "vulnerability_type": "state machine oob",
            "root_cause": "source parser state machine out-of-bounds read",
        },
    }
    final_record = {
        "case_id": "demo",
        "score": 8,
        "max_score": 10,
        "validation": {"status": "passed"},
        "run": {
            "start": "2026-07-01T12:19:32+00:00",
            "end": "2026-07-01T12:20:47+00:00",
        },
        "skill_injection": None,
        "skill_relevance": {"status": "no_selected_skills"},
    }
    injection_rows = [
        {"session_id": "old", "timestamp": "2026-07-01 20:00:00", "turn": 8, "selected_skill_names": ["other"]},
        {
            "session_id": "target",
            "timestamp": "2026-07-01 20:20:31",
            "turn": 7,
            "injection_mode": "inline",
            "selected_skill_names": ["source-parser-state-machine-oob"],
            "available_skill_count": 35,
        },
    ]

    updated = attach_injection(
        final_record=final_record,
        case=case,
        injection_value=injection_rows,
        session_id="",
    )

    assert updated["session_id"] == "target"
    assert updated["session_id_source"] == "inferred_from_injection_log"
    assert updated["skill_injection"]["selected_skill_names"] == ["source-parser-state-machine-oob"]


def test_infer_session_id_from_injection_uses_run_window():
    injection_rows = [
        {"session_id": "old", "timestamp": "2026-07-01 14:30:00", "turn": 8},
        {"session_id": "target", "timestamp": "2026-07-01 15:43:09", "turn": 1},
        {"session_id": "target", "timestamp": "2026-07-01 15:48:23", "turn": 24},
    ]
    run_meta = {
        "start": "2026-07-01T07:43:10+00:00",
        "end": "2026-07-01T07:48:24+00:00",
    }

    session_id = infer_session_id_from_injection(injection_rows, run_meta)

    assert session_id == "target"


def test_infer_session_id_from_injection_prefers_turn_rows_over_snapshot_rows():
    injection_rows = [
        {
            "session_id": "snapshot-old",
            "timestamp": "2026-07-28T08:10:29Z",
            "turn": 8,
            "source": "session_snapshot",
        },
        {
            "session_id": "target-direct",
            "timestamp": "2026-07-28 16:12:43",
            "turn": 1,
        },
        {
            "session_id": "target-direct",
            "timestamp": "2026-07-28 16:13:32",
            "turn": 7,
        },
    ]
    run_meta = {
        "start": "2026-07-28T08:12:35+00:00",
        "end": "2026-07-28T08:13:47+00:00",
    }

    session_id = infer_session_id_from_injection(injection_rows, run_meta)

    assert session_id == "target-direct"


def test_summarize_skill_feedback_aggregates_selected_skills(tmp_path):
    records = [
        (
            tmp_path / "a.json",
            {
                "case_id": "case-a",
                "mode": "skillclaw-inline",
                "score": 8,
                "max_score": 10,
                "checks": {"file": {"hit": True}, "function": {"hit": True}, "cve": {"hit": False}},
                "validation": {
                    "status": "passed",
                    "checks": [
                        {"name": "artifact", "type": "artifact_exists", "status": "passed"},
                        {"name": "artifact-exec", "type": "artifact_exec", "status": "passed"},
                    ],
                },
                "skill_injection": {"selected_skill_names": ["source-parser-state-machine-oob"]},
                "feedback": {"decision": "positive", "suggested_action": "keep_or_promote_skill"},
            },
        ),
        (
            tmp_path / "b.json",
            {
                "case_id": "case-b",
                "mode": "skillclaw-inline",
                "score": 2,
                "max_score": 10,
                "checks": {"file": {"hit": False}, "function": {"hit": False}},
                "validation": {"status": "failed"},
                "skill_injection": {"selected_skill_names": ["source-parser-state-machine-oob"]},
                "feedback": {"decision": "negative", "suggested_action": "inspect_skill_mismatch_or_deprecate"},
            },
        ),
    ]

    rows = build_skill_feedback(records)

    assert len(rows) == 1
    row = rows[0]
    assert row["skill"] == "source-parser-state-machine-oob"
    assert row["selected_count"] == 2
    assert row["positive"] == 1
    assert row["negative"] == 1
    assert row["mean_score"] == 0.5
    assert row["validation_passed"] == 1
    assert row["validation_failed"] == 1
    assert row["artifact_generated"] == 1
    assert row["artifact_execution_passed"] == 1


def test_summarize_skill_feedback_does_not_credit_mismatched_skill(tmp_path):
    records = [
        (
            tmp_path / "mixed.json",
            {
                "case_id": "case-mixed",
                "mode": "skillclaw-inline",
                "score": 10,
                "max_score": 10,
                "checks": {"file": {"hit": True}, "function": {"hit": True}},
                "validation": {"status": "passed", "checks": []},
                "skill_injection": {
                    "selected_skill_names": [
                        "source-parser-state-machine-oob",
                        "ida-headless-cwe120-sink-analysis",
                    ]
                },
                "skill_relevance": {
                    "status": "mixed_task_relevance",
                    "relevant_skills": ["source-parser-state-machine-oob"],
                    "mismatched_skills": ["ida-headless-cwe120-sink-analysis"],
                    "infra_skills": [],
                },
                "feedback": {
                    "decision": "positive",
                    "suggested_action": "keep_skill_but_prune_extraneous_selection",
                },
            },
        ),
    ]

    rows = {row["skill"]: row for row in build_skill_feedback(records)}

    assert rows["source-parser-state-machine-oob"]["positive"] == 1
    assert rows["source-parser-state-machine-oob"]["relevant_selected"] == 1
    assert rows["ida-headless-cwe120-sink-analysis"]["positive"] == 0
    assert rows["ida-headless-cwe120-sink-analysis"]["neutral"] == 1
    assert rows["ida-headless-cwe120-sink-analysis"]["mismatched_selected"] == 1


def test_skill_gate_revises_high_score_without_cve_calibration():
    row = {
        "skill": "source-parser-state-machine-oob",
        "selected_count": "3",
        "positive": "3",
        "neutral": "0",
        "negative": "0",
        "mean_score": "0.8",
        "validation_passed": "1",
        "validation_failed": "0",
        "cve_hits": "0",
        "file_hits": "3",
        "function_hits": "3",
        "evidence_hits": "3",
        "root_cause_hits": "3",
    }

    decision = decide_gate(row)

    assert decision["gate_decision"] == "revise"
    assert any("CVE" in reason for reason in decision["reasons"])


def test_skill_gate_demotes_infrastructure_skill():
    row = {
        "skill": "skillclaw-proxy-introspection",
        "selected_count": "2",
        "positive": "1",
        "neutral": "1",
        "negative": "0",
        "mean_score": "0.8",
    }

    decision = decide_gate(row)

    assert decision["gate_decision"] == "demote"
    assert "框架" in decision["reasons"][0]


def test_skill_gate_demotes_repeated_mismatched_skill():
    row = {
        "skill": "ida-headless-cwe120-sink-analysis",
        "selected_count": "2",
        "positive": "0",
        "neutral": "2",
        "negative": "0",
        "mean_score": "1.0",
        "validation_passed": "2",
        "validation_failed": "0",
        "relevant_selected": "0",
        "mismatched_selected": "2",
        "infra_selected": "0",
        "cve_hits": "0",
        "file_hits": "2",
        "function_hits": "2",
        "evidence_hits": "2",
        "root_cause_hits": "2",
    }

    decision = decide_gate(row)

    assert decision["gate_decision"] == "demote"
    assert "错配" in decision["reasons"][0]


def test_build_skill_feedback_bundle_tracks_dimension_flags(tmp_path):
    record = {
        "case_id": "libxml2-demo",
        "mode": "skillclaw-inline",
        "model": "skillclaw-model",
        "session_id": "session-a",
        "score": 8,
        "max_score": 10,
        "checks": {
            "cve": {"hit": False, "expected": ["CVE-0000-0001"], "matched": []},
            "file": {"hit": True, "expected": ["HTMLparser.c"], "matched": ["HTMLparser.c"]},
            "function": {
                "hit": True,
                "expected": ["htmlParseTryOrFinish"],
                "matched": ["htmlParseTryOrFinish"],
            },
            "evidence": {"hit": True},
            "root_cause": {"hit": True},
        },
        "predictions": {"cves": ["CVE-0000-9999"]},
        "validation": {
            "status": "passed",
            "checks": [
                {"name": "artifact", "type": "artifact_exists", "status": "passed"},
                {"name": "artifact-exec", "type": "artifact_exec", "status": "passed"},
                {"name": "bundle", "type": "bundle_script", "status": "passed"},
            ],
        },
        "skill_injection": {
            "selected_skill_names": ["source-parser-state-machine-oob"],
        },
        "feedback": {
            "decision": "neutral",
            "suggested_action": "revise_cve_identity_before_promotion",
            "quality_flags": ["cve_identity_miss"],
        },
    }
    gate = {
        "source-parser-state-machine-oob": {
            "gate_decision": "revise",
            "suggestions": ["add advisory evidence requirement"],
            "reasons": ["localization evidence exists but exact CVE identity is absent"],
        }
    }

    bundles = build_feedback_bundles([(tmp_path / "final.json", record)], gate_map=gate)

    assert len(bundles) == 1
    bundle = bundles[0]
    assert bundle["skill"] == "source-parser-state-machine-oob"
    assert bundle["gate_decision"] == "revise"
    assert bundle["summary"]["neutral"] == 1
    assert bundle["dimensions"]["localization_success"] == 1
    assert bundle["dimensions"]["cve_success"] == 0
    assert bundle["dimensions"]["cve_identity_miss"] == 1
    assert bundle["dimensions"]["dynamic_or_bundle_validation_passed"] == 1
    assert bundle["dimensions"]["artifact_generated"] == 1
    assert bundle["dimensions"]["artifact_execution_passed"] == 1
    assert any("CVE" in item for item in bundle["revision_directives"])
    assert bundle["revision_templates"][0]["template_id"] == "cve_identity_miss"
    assert "uncertain" in bundle["revision_templates"][0]["required_changes"][2]

    json_path = tmp_path / "bundle.json"
    md_path = tmp_path / "bundle.md"
    write_bundle_json(bundles, json_path)
    write_bundle_markdown(bundles, md_path)
    assert "source-parser-state-machine-oob" in json_path.read_text(encoding="utf-8")
    assert "cve_miss" in md_path.read_text(encoding="utf-8")
    assert "cve_identity_miss" in md_path.read_text(encoding="utf-8")


def test_build_skill_gate_report_orders_promote_before_revise():
    rows = [
        {
            "skill": "needs-revision",
            "selected_count": "3",
            "positive": "3",
            "mean_score": "0.8",
            "cve_hits": "0",
            "file_hits": "3",
            "function_hits": "3",
        },
        {
            "skill": "promotable",
            "selected_count": "3",
            "positive": "3",
            "mean_score": "0.9",
            "cve_hits": "3",
            "file_hits": "3",
            "function_hits": "3",
            "evidence_hits": "3",
            "root_cause_hits": "3",
        },
    ]

    report = build_gate_report(rows)

    assert [item["skill"] for item in report] == ["promotable", "needs-revision"]
    assert report[0]["gate_decision"] == "promote"


def test_build_feedback_bundle_filters_skill_and_case(tmp_path):
    record = {
        "case_id": "libxml2-2.9.4-cve-2017-8872",
        "score": 8.0,
        "max_score": 10.0,
        "checks": {
            "cve": {"hit": False, "expected": ["CVE-2017-8872"], "matched": []},
            "file": {"hit": True, "expected": ["HTMLparser.c"], "matched": ["HTMLparser.c"]},
            "function": {
                "hit": True,
                "expected": ["htmlParseTryOrFinish"],
                "matched": ["htmlParseTryOrFinish"],
            },
            "evidence": {"hit": True},
            "root_cause": {"hit": True},
        },
        "predictions": {"cves": ["CVE-2016-1839"]},
        "validation": {"status": "passed", "checks": []},
        "skill_injection": {
            "selected_skill_names": ["source-parser-state-machine-oob", "vuln-hunting"],
        },
        "feedback": {
            "decision": "neutral",
            "suggested_action": "revise_cve_identity_before_promotion",
            "quality_flags": ["cve_identity_miss"],
        },
    }
    gate = {
        "source-parser-state-machine-oob": {
            "gate_decision": "revise",
            "suggestions": ["add advisory evidence requirement"],
            "reasons": ["localization evidence exists but exact CVE identity is absent"],
        }
    }

    bundles = build_feedback_bundles(
        [(tmp_path / "final.json", record)],
        gate_map=gate,
        only_skills={"source-parser-state-machine-oob"},
        only_case_ids={"libxml2-2.9.4-cve-2017-8872"},
    )

    assert len(bundles) == 1
    assert bundles[0]["skill"] == "source-parser-state-machine-oob"

    bundles = build_feedback_bundles(
        [(tmp_path / "final.json", record)],
        gate_map=gate,
        only_skills={"vuln-hunting"},
        only_case_ids={"tcpdump-4.9.1-cve-2017-13031"},
    )

    assert bundles == []


def test_render_case_prompt_selects_mode():
    case = {
        "case_id": "demo",
        "prompt": {
            "recommended_skillclaw": "use skillclaw",
            "recommended_direct": "direct baseline",
            "recommended_blind_skillclaw": "blind skillclaw",
            "recommended_blind_direct": "blind direct",
        },
    }

    assert get_case_prompt(case, "skillclaw-inline") == "use skillclaw"
    assert get_case_prompt(case, "direct-deepseek") == "direct baseline"
    assert get_case_prompt(case, "blind-skillclaw-inline") == "blind skillclaw"
    assert get_case_prompt(case, "blind-direct-deepseek") == "blind direct"


def test_compare_records_reports_key_deltas():
    before = {
        "case_id": "libxml2-demo",
        "mode": "skillclaw-inline",
        "model": "skillclaw-model",
        "score": 8,
        "max_score": 10,
        "checks": {
            "cve": {"hit": False},
            "file": {"hit": True},
            "function": {"hit": True},
            "evidence": {"hit": True},
            "root_cause": {"hit": True},
        },
        "validation": {
            "status": "passed",
            "checks": [
                {"type": "artifact_exec", "status": "failed"},
                {"type": "asan_command", "status": "passed"},
            ],
        },
        "feedback": {"decision": "neutral", "quality_flags": ["cve_identity_miss"]},
        "skill_injection": {"selected_skill_names": ["source-parser-state-machine-oob"]},
    }
    after = {
        "case_id": "libxml2-demo",
        "mode": "skillclaw-inline",
        "model": "skillclaw-model",
        "score": 10,
        "max_score": 10,
        "checks": {
            "cve": {"hit": True},
            "file": {"hit": True},
            "function": {"hit": True},
            "evidence": {"hit": True},
            "root_cause": {"hit": True},
        },
        "validation": {
            "status": "passed",
            "checks": [
                {"type": "artifact_exec", "status": "passed"},
                {"type": "asan_command", "status": "passed"},
            ],
        },
        "feedback": {"decision": "positive", "quality_flags": []},
        "skill_injection": {"selected_skill_names": ["source-parser-state-machine-oob", "vuln-hunting"]},
    }

    result = compare_records(before, after)

    assert result["delta"]["score_delta"] == 2.0
    assert result["delta"]["exact_cve_improved"] is True
    assert result["delta"]["localization_regressed"] is False
    assert result["delta"]["artifact_exec_change"] == "failed -> passed"
    assert result["delta"]["quality_flags_removed"] == ["cve_identity_miss"]
    assert result["delta"]["selected_skills_added"] == ["vuln-hunting"]

    markdown = render_markdown(result)
    assert "Experiment Compare: libxml2-demo" in markdown
    assert "artifact exec change" in markdown


def test_render_case_prompt_guarded_mode_appends_execution_constraints():
    case = {
        "case_id": "demo",
        "prompt": {
            "recommended_skillclaw": "use skillclaw",
            "recommended_direct": "direct baseline",
        },
    }

    guarded = get_case_prompt(case, "skillclaw-inline-guarded")

    assert guarded.startswith("use skillclaw")
    assert FINAL_ANSWER_GUARD in guarded
    assert "at most 8 tool calls" in guarded


def test_render_case_prompt_appends_confirmation_contract():
    case = {
        "case_id": "gif-demo",
        "prompt": {
            "recommended_skillclaw": "analyze target",
        },
        "expected_artifacts": [
            {
                "name": "poc",
                "path": "artifacts/poc.gif",
                "type": "binary",
                "description": "minimal trigger input",
            }
        ],
        "repro": {
            "build": ["make -j"],
            "run": ["./target artifacts/poc.gif"],
            "success_markers": ["AddressSanitizer", "heap-buffer-overflow"],
            "target_frames": ["DumpScreen2RGB"],
        },
    }

    prompt = get_case_prompt(case, "skillclaw-inline")

    assert "Artifact generation requirements:" in prompt
    assert "artifacts/poc.gif" in prompt
    assert "Confirmation / repro targets:" in prompt
    assert "AddressSanitizer" in prompt
    assert "DumpScreen2RGB" in prompt
    assert "preserve the target exit status" in prompt


def test_render_case_prompt_blind_mode_does_not_append_confirmation_contract():
    case = {
        "case_id": "gif-demo",
        "prompt": {
            "recommended_blind_skillclaw": "blind analyze target",
        },
        "expected_artifacts": [
            {
                "name": "poc",
                "path": "artifacts/poc.gif",
                "type": "binary",
                "description": "minimal trigger input",
            }
        ],
        "repro": {
            "build": ["make -j"],
            "run": ["./target artifacts/poc.gif"],
            "success_markers": ["AddressSanitizer", "heap-buffer-overflow"],
            "target_frames": ["DumpScreen2RGB"],
        },
        "confirmation": {
            "maturity": "asan-backed",
            "current_claim": "known good path",
        },
    }

    prompt = get_case_prompt(case, "blind-skillclaw-inline")

    assert prompt == "blind analyze target"
    assert "Artifact generation requirements:" not in prompt
    assert "Confirmation / repro targets:" not in prompt
    assert "Current confirmation state:" not in prompt


def test_render_case_prompt_ignores_task_profile_by_default():
    case = {
        "case_id": "gif-demo",
        "task_profile": {
            "workspace": "source_tree",
            "target_component": "file_parser",
            "analysis_mode": "source_analysis",
            "bug_class": "memory_safety",
            "input_vector": "crafted_file",
        },
        "prompt": {
            "recommended_blind_skillclaw": "blind analyze target",
        },
    }

    prompt = get_case_prompt(case, "blind-skillclaw-inline")

    assert prompt == "blind analyze target"


def test_render_case_prompt_prepends_task_profile_when_enabled(monkeypatch):
    monkeypatch.setenv("SKILLCLAW_ENABLE_TASK_PROFILE", "1")
    case = {
        "case_id": "gif-demo",
        "task_profile": {
            "workspace": "source_tree",
            "target_component": "file_parser",
            "analysis_mode": "source_analysis",
            "bug_class": "memory_safety",
            "input_vector": "crafted_file",
        },
        "prompt": {
            "recommended_blind_skillclaw": "blind analyze target",
        },
    }

    prompt = get_case_prompt(case, "blind-skillclaw-inline")

    assert prompt.startswith("Task profile:")
    assert "Keep the focus on the userland source tree rather than environment-wide exploration." in prompt
    assert "Prefer source-level reasoning over reverse-engineering workflows" in prompt
    assert "blind analyze target" in prompt


def test_render_case_prompt_appends_confirmation_state():
    case = {
        "case_id": "exiv2-demo",
        "prompt": {
            "recommended_skillclaw": "analyze target",
        },
        "confirmation": {
            "maturity": "intermediate-confirmed-path",
            "current_claim": "current path is readMetadata -> memcpy",
            "target_claim": "final promotion requires getULong/types.cpp evidence",
            "confirmed_path": {
                "summary": "stable ASan path in JP2 ICC parsing",
                "markers": ["EXIV2_READMETADATA_MEMCPY_OK", "EXIV2_ASAN_OOB_OK"],
                "stack_frames": ["src/jp2image.cpp:277", "Exiv2::Jp2Image::readMetadata()"],
            },
            "promotion_blockers": ["stack does not yet show getULong"],
            "promotion_targets": ["recover getULong/types.cpp stack evidence"],
        },
    }

    prompt = get_case_prompt(case, "skillclaw-inline")

    assert "Current confirmation state:" in prompt
    assert "intermediate-confirmed-path" in prompt
    assert "readMetadata -> memcpy" in prompt
    assert "getULong/types.cpp evidence" in prompt
    assert "EXIV2_READMETADATA_MEMCPY_OK" in prompt
    assert "src/jp2image.cpp:277" in prompt


def test_print_case_guide_includes_artifacts_repro_and_commands(tmp_path):
    case_path = tmp_path / "demo.json"
    case = {
        "case_id": "gif-demo",
        "target": {
            "project": "giflib",
            "version": "5.1.2",
            "source_root": "/home/li/skillclaw-eval/giflib-5.1.2",
        },
        "expected_artifacts": [
            {"path": "artifacts/poc.gif", "type": "binary", "description": "trigger input"},
            {"path": "artifacts/run.sh", "type": "shell", "description": "repro helper"},
        ],
        "repro": {
            "build": ["make -j"],
            "run": ["./target artifacts/poc.gif"],
            "success_markers": ["AddressSanitizer"],
            "target_frames": ["DumpScreen2RGB"],
        },
    }
    case_path.write_text(json.dumps(case, ensure_ascii=False), encoding="utf-8")

    text = render_guide(
        case,
        case_path=case_path,
        root_override=None,
        output_dir="~/skillclaw-eval/runs/demo",
    )

    assert "# Execution Guide: gif-demo" in text
    assert "artifacts/poc.gif" in text
    assert "AddressSanitizer" in text
    assert "skillclaw-inline-guarded" in text
    assert "direct-deepseek-guarded" in text
    assert "evaluation.runs.run_single_case" in text


def test_print_case_guide_includes_confirmation_state(tmp_path):
    case_path = tmp_path / "demo.json"
    case = {
        "case_id": "confirm-demo",
        "target": {
            "project": "demo",
            "version": "1.0",
            "source_root": "/tmp/demo",
        },
        "confirmation": {
            "maturity": "behavior-backed",
            "current_claim": "current path is behavior confirmed",
            "target_claim": "promotion requires stronger crash evidence",
            "confirmed_path": {
                "summary": "runtime marker path",
                "markers": ["MARKER_OK"],
                "stack_frames": ["demo.c", "demo_fn"],
            },
            "promotion_blockers": ["no sanitizer crash yet"],
            "promotion_targets": ["recover ASan path"],
        },
    }
    case_path.write_text(json.dumps(case, ensure_ascii=False), encoding="utf-8")

    text = render_guide(
        case,
        case_path=case_path,
        root_override=None,
        output_dir="~/skillclaw-eval/runs/demo",
    )

    assert "## Current Confirmation State" in text
    assert "behavior-backed" in text
    assert "MARKER_OK" in text
    assert "demo_fn" in text


def test_repository_cases_include_confirmation_metadata_for_mature_confirmation_cases():
    expected_cases = {
        "tcpdump-4.9.1-cve-2017-13031.json",
        "tcpdump-4.9.1-cve-2018-14469.json",
        "libarchive-3.8.0-cve-2025-60753.json",
        "exiv2-0.26-cve-2017-17725.json",
    }
    for case_name in expected_cases:
        case = json.loads((Path("benchmarks") / "cases" / case_name).read_text(encoding="utf-8-sig"))
        confirmation = case.get("confirmation")
        assert isinstance(confirmation, dict), case_name
        assert str(confirmation.get("maturity") or "").strip(), case_name
        assert str(confirmation.get("current_claim") or "").strip(), case_name


def test_repository_case_prompts_are_not_mojibake():
    suspicious_fragments = ["锟", "閿", "闁", "鈫?"]
    for case_path in (Path("benchmarks") / "cases").glob("*.json"):
        case = json.loads(case_path.read_text(encoding="utf-8-sig"))
        prompts = case.get("prompt", {})
        for key, prompt in prompts.items():
            assert not any(fragment in str(prompt) for fragment in suspicious_fragments), (
                case_path,
                key,
            )


def test_check_case_runtime_passes_with_root_override(tmp_path):
    root = tmp_path / "target"
    root.mkdir()
    (root / "demo-bin").write_text("binary\n", encoding="utf-8")
    (root / "vuln.c").write_text("void vuln(void) {}\n", encoding="utf-8")
    case_path = tmp_path / "case.json"
    case_path.write_text(
        json.dumps(
            {
                "case_id": "demo",
                "target": {"source_root": "/missing/default", "binary": "demo-bin"},
                "ground_truth": {
                    "files": ["vuln.c"],
                    "functions": ["vuln"],
                    "vulnerability_type": "demo",
                },
                "scoring": {"max_score": 10, "weights": {}},
            }
        ),
        encoding="utf-8",
    )

    result = check_case_environment(case_path=case_path, root_override=str(root), settings_path=None)

    assert result["status"] == "passed"
    assert all(item["status"] == "ok" for item in result["checks"])


def test_check_case_runtime_reports_missing_ground_truth_file(tmp_path):
    root = tmp_path / "target"
    root.mkdir()
    case_path = tmp_path / "case.json"
    case_path.write_text(
        json.dumps(
            {
                "case_id": "demo",
                "target": {"source_root": str(root)},
                "ground_truth": {
                    "files": ["missing.c"],
                    "functions": ["vuln"],
                    "vulnerability_type": "demo",
                },
                "scoring": {"max_score": 10, "weights": {}},
            }
        ),
        encoding="utf-8",
    )

    result = check_case_environment(case_path=case_path, settings_path=None)

    assert result["status"] == "failed"
    assert any(item["name"] == "ground_truth_file" and item["status"] == "failed" for item in result["checks"])


def test_check_case_runtime_infers_claude_provider(tmp_path):
    settings = tmp_path / "settings.json"
    settings.write_text(
        json.dumps(
            {
                "env": {
                    "ANTHROPIC_BASE_URL": "http://10.12.189.47:30000",
                    "ANTHROPIC_MODEL": "skillclaw-model",
                }
            }
        ),
        encoding="utf-8",
    )

    result = infer_claude_provider(settings)

    assert result["status"] == "ok"
    assert result["provider"] == "skillclaw"


def test_check_case_runtime_infers_claude_provider_from_env(monkeypatch, tmp_path):
    settings = tmp_path / "missing-settings.json"
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://127.0.0.1:30000")
    monkeypatch.setenv("ANTHROPIC_MODEL", "skillclaw-model")

    result = infer_claude_provider(settings)

    assert result["status"] == "ok"
    assert result["provider"] == "skillclaw"
    assert result["source"] == "env"


def test_bundle_script_bridge_executes_script(tmp_path):
    bundle = tmp_path / "bundle"
    script = bundle / "scripts" / "demo.py"
    script.parent.mkdir(parents=True)
    script.write_text(
        "import json\nprint(json.dumps({'status': 'passed', 'value': 7}))\n",
        encoding="utf-8",
    )

    script_path = resolve_bundle_script(script="demo.py", bundle_root=bundle)
    result = run_bundle_script(script_path=script_path, timeout_seconds=10)

    assert result["status"] == "passed"
    assert result["parsed_json"]["value"] == 7


def test_run_case_validation_bundle_script_validator(tmp_path):
    bundle = tmp_path / "case-bundles" / "demo"
    script = bundle / "scripts" / "demo.py"
    script.parent.mkdir(parents=True)
    script.write_text(
        "import json\nprint(json.dumps({'status': 'passed', 'checker': 'demo'}))\n",
        encoding="utf-8",
    )
    case = {
        "case_id": "demo",
        "validators": [
            {
                "name": "bundle",
                "type": "bundle_script",
                "bundle_root": str(bundle),
                "script": "demo.py",
            }
        ],
    }

    result = run_validators(case, tmp_path, skip_commands=False)

    assert result["status"] == "passed"
    assert result["checks"][0]["parsed_json"]["checker"] == "demo"


def test_run_case_validation_bundle_script_validator_resolves_benchmark_relative_bundle_root(tmp_path):
    benchmarks_root = tmp_path / "benchmarks"
    case_dir = benchmarks_root / "cases"
    bundle = benchmarks_root / "skill_bundles" / "demo"
    script = bundle / "scripts" / "demo.py"
    script.parent.mkdir(parents=True)
    case_dir.mkdir(parents=True)
    script.write_text(
        "import json\nprint(json.dumps({'status': 'passed', 'checker': 'demo-relative'}))\n",
        encoding="utf-8",
    )
    case_path = case_dir / "demo.json"
    case_path.write_text(
        json.dumps(
            {
                "case_id": "demo-relative",
                "validators": [
                    {
                        "name": "bundle",
                        "type": "bundle_script",
                        "bundle_root": "skill_bundles/demo",
                        "script": "demo.py",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    case = load_case_definition(case_path)

    result = run_validators(case, tmp_path, skip_commands=False, case_path=case_path)

    assert result["status"] == "passed"
    assert result["checks"][0]["parsed_json"]["checker"] == "demo-relative"


def test_content_match_validator_uses_agent_output(tmp_path):
    output = tmp_path / "answer.json"
    output.write_text('{"predicted_files":["HTMLparser.c"]}', encoding="utf-8")
    case = {
        "case_id": "demo",
        "ground_truth": {"files": ["HTMLparser.c"], "functions": ["htmlParseTryOrFinish"]},
        "validators": [
            {
                "name": "answer",
                "type": "content_match",
                "use_ground_truth": True,
                "match": "any",
            }
        ],
    }

    result = run_validators(case, tmp_path, agent_output_path=output)

    assert result["status"] == "passed"
    assert result["checks"][0]["hit_count"] >= 1


def test_build_feedback_marks_positive_high_score_with_validation():
    relevance = assess_skill_relevance(
        case={"ground_truth": {"root_cause": "parser state machine out of bounds read"}},
        selected_skills=["source-parser-state-machine-oob"],
    )
    feedback = build_feedback(
        score_result={"score": 8, "max_score": 10},
        validation_result={"status": "passed"},
        skill_injection={"selected_skill_names": ["source-parser-state-machine-oob"]},
        skill_relevance=relevance,
    )

    assert feedback["decision"] == "positive"
    assert feedback["suggested_action"] == "keep_or_promote_skill"


def test_build_feedback_flags_cve_miss_with_source_localization():
    relevance = assess_skill_relevance(
        case={"ground_truth": {"root_cause": "parser state machine out of bounds read"}},
        selected_skills=["source-parser-state-machine-oob"],
    )
    feedback = build_feedback(
        score_result={
            "score": 8,
            "max_score": 10,
            "checks": {
                "cve": {"hit": False},
                "file": {"hit": True},
                "function": {"hit": True},
                "evidence": {"hit": True},
                "root_cause": {"hit": True},
            },
        },
        validation_result={"status": "passed"},
        skill_injection={"selected_skill_names": ["source-parser-state-machine-oob"]},
        skill_relevance=relevance,
    )

    assert feedback["decision"] == "neutral"
    assert feedback["suggested_action"] == "revise_cve_identity_before_promotion"
    assert "cve_identity_miss" in feedback["quality_flags"]


def test_build_feedback_does_not_promote_infra_skills():
    relevance = assess_skill_relevance(
        case={"target": {"project": "tcpdump"}, "ground_truth": {"functions": ["frag6_print"]}},
        selected_skills=["skillclaw-proxy-introspection", "skillclaw-skill-discovery"],
    )

    feedback = build_feedback(
        score_result={"score": 8, "max_score": 10},
        validation_result={"status": "passed"},
        skill_injection={"selected_skill_names": ["skillclaw-proxy-introspection", "skillclaw-skill-discovery"]},
        skill_relevance=relevance,
    )

    assert relevance["status"] == "only_infra_skills"
    assert feedback["decision"] == "neutral"
    assert feedback["suggested_action"] == "inspect_retrieval_before_promoting_skill"


def test_build_feedback_marks_mixed_relevance_without_penalizing_relevant_skill():
    relevance = assess_skill_relevance(
        case={
            "target": {"project": "demo-parser", "source_root": "/tmp/demo-parser"},
            "ground_truth": {"root_cause": "parser state machine out of bounds read"},
        },
        selected_skills=["source-parser-state-machine-oob", "ida-headless-cwe120-sink-analysis"],
    )

    feedback = build_feedback(
        score_result={"score": 8, "max_score": 10},
        validation_result={"status": "passed"},
        skill_injection={
            "selected_skill_names": ["source-parser-state-machine-oob", "ida-headless-cwe120-sink-analysis"]
        },
        skill_relevance=relevance,
    )

    assert relevance["status"] == "mixed_task_relevance"
    assert "ida-headless-cwe120-sink-analysis" in relevance["mismatched_skills"]
    assert feedback["decision"] == "positive"
    assert feedback["suggested_action"] == "keep_skill_but_prune_extraneous_selection"
    assert "extraneous_skill_selection" in feedback["quality_flags"]


def test_assess_skill_relevance_marks_firmware_skills_mismatched_for_source_parser_case():
    relevance = assess_skill_relevance(
        case={
            "target": {"project": "tcpdump", "binary": "./tcpdump", "source_root": "/tmp/tcpdump"},
            "ground_truth": {
                "files": ["print-frag6.c"],
                "functions": ["frag6_print"],
                "root_cause": "parser lookahead over-read in IPv6 fragmentation handling",
            },
        },
        selected_skills=[
            "source-parser-state-machine-oob",
            "vuln-hunting",
            "verify-rootfs-full-enumeration",
        ],
    )

    assert relevance["status"] == "mixed_task_relevance"
    assert relevance["relevant_skills"] == ["source-parser-state-machine-oob"]
    assert "vuln-hunting" in relevance["mismatched_skills"]
    assert "verify-rootfs-full-enumeration" in relevance["mismatched_skills"]


def test_assess_skill_relevance_ignores_task_profile_by_default():
    relevance = assess_skill_relevance(
        case={
            "target": {"project": "giflib", "binary": "util/gif2rgb", "source_root": "/tmp/giflib"},
            "ground_truth": {
                "files": ["util/gif2rgb.c"],
                "functions": ["DumpScreen2RGB"],
                "root_cause": "background color index reaches color map without bounds validation",
            },
            "task_profile": {
                "workspace": "source_tree",
                "target_component": "file_parser",
                "analysis_mode": "source_analysis",
                "bug_class": "memory_safety",
                "input_vector": "crafted_file",
            },
        },
        selected_skills=[
            "source-parser-state-machine-oob",
            "vuln-hunting",
            "verify-rootfs-full-enumeration",
        ],
    )

    assert relevance["status"] == "no_task_relevant_skill"
    assert relevance["relevant_skills"] == []


def test_assess_skill_relevance_uses_task_profile_when_enabled(monkeypatch):
    monkeypatch.setenv("SKILLCLAW_ENABLE_TASK_PROFILE", "1")
    relevance = assess_skill_relevance(
        case={
            "target": {"project": "giflib", "binary": "util/gif2rgb", "source_root": "/tmp/giflib"},
            "ground_truth": {
                "files": ["util/gif2rgb.c"],
                "functions": ["DumpScreen2RGB"],
                "root_cause": "background color index reaches color map without bounds validation",
            },
            "task_profile": {
                "workspace": "source_tree",
                "target_component": "file_parser",
                "analysis_mode": "source_analysis",
                "bug_class": "memory_safety",
                "input_vector": "crafted_file",
            },
        },
        selected_skills=[
            "source-parser-state-machine-oob",
            "vuln-hunting",
            "verify-rootfs-full-enumeration",
        ],
    )

    assert relevance["status"] == "mixed_task_relevance"
    assert relevance["relevant_skills"] == ["source-parser-state-machine-oob"]
    assert "vuln-hunting" in relevance["mismatched_skills"]
    assert "verify-rootfs-full-enumeration" in relevance["mismatched_skills"]


def test_build_feedback_marks_no_skill_as_baseline_positive():
    relevance = assess_skill_relevance(
        case={"target": {"project": "tcpdump"}},
        selected_skills=[],
    )

    feedback = build_feedback(
        score_result={"score": 8, "max_score": 10},
        validation_result={"status": "passed"},
        skill_injection=None,
        skill_relevance=relevance,
    )

    assert relevance["status"] == "no_selected_skills"
    assert feedback["decision"] == "positive"
    assert feedback["suggested_action"] == "use_as_baseline_positive"


def test_asan_command_treats_sanitizer_crash_as_pass(tmp_path):
    code = (
        "import sys; "
        "sys.stderr.write('ERROR: AddressSanitizer: heap-buffer-overflow\\n"
        "#0 HTMLparser.c htmlParseTryOrFinish\\n'); "
        "sys.exit(1)"
    )
    case = {
        "case_id": "demo",
        "ground_truth": {"files": ["HTMLparser.c"], "functions": ["htmlParseTryOrFinish"]},
        "validators": [
            {
                "name": "asan",
                "type": "asan_command",
                "command": f'"{sys.executable}" -c {json.dumps(code)}',
                "timeout_seconds": 10,
            }
        ],
    }

    result = run_validators(case, tmp_path, skip_commands=False)

    assert result["status"] == "passed"
    check = result["checks"][0]
    assert check["status"] == "passed"
    assert check["sanitizer_marker_hit"] is True
    assert check["stack_hit"] is True
    assert "HTMLparser.c" in check["matched_stack_patterns"]


def test_asan_command_fails_when_expected_crash_does_not_happen(tmp_path):
    code = "print('clean run')"
    case = {
        "case_id": "demo",
        "ground_truth": {"files": ["HTMLparser.c"], "functions": ["htmlParseTryOrFinish"]},
        "validators": [
            {
                "name": "asan",
                "type": "asan_command",
                "command": f'"{sys.executable}" -c {json.dumps(code)}',
                "timeout_seconds": 10,
                "expect_crash": True,
            }
        ],
    }

    result = run_validators(case, tmp_path, skip_commands=False)

    assert result["status"] == "failed"
    assert result["checks"][0]["status"] == "failed"


def test_run_single_case_extracts_fenced_json():
    text = """analysis first

```json
{"predicted_files": ["HTMLparser.c"], "score": 7}
```
"""

    result = extract_json_object(text)

    assert result["predicted_files"] == ["HTMLparser.c"]


def test_inline_retrieval_prefers_source_parser_skill_for_tcpdump_prompt(tmp_path):
    skills_dir = tmp_path / "skills"
    _write_test_skill(
        skills_dir,
        "source-parser-state-machine-oob",
        "Find out-of-bounds reads in C parser state machines by tracing source-level bounds guards.",
        "Inspect parser source, lookahead reads, fragment headers, ND_TCHECK, and guard dominance.",
    )
    _write_test_skill(
        skills_dir,
        "ida-headless-cwe120-sink-analysis",
        "Run CWE-120 deep static analysis with IDA Pro headless mode for ELF binaries.",
        "Use IDA, Hex-Rays, PLT sinks, and xrefs.",
    )
    _write_test_skill(
        skills_dir,
        "elf-cwe120-firmware-triage",
        "Scan ELF firmware binaries for CWE-120 dangerous function imports.",
    )
    _write_test_skill(
        skills_dir,
        "skillclaw-proxy-introspection",
        "Use when asked to list available skills or probe SkillClaw proxy APIs.",
        "Explain SkillClaw server-side skill catalog and proxy endpoints.",
    )

    manager = SkillManager(str(skills_dir), retrieval_mode="template")
    prompt = (
        "Do not use WebSearch. Do not invoke Claude Code local Skill(...). "
        "You are using SkillClaw server-side inline skills through the API proxy. "
        "The current working directory is tcpdump-4.9.1 and the target program is ./tcpdump. "
        "Use server-side skills to locate a known buffer over-read vulnerability related to the "
        "IPv6 fragmentation header parser. Analyze source code and build artifacts. "
        "Finish with a single JSON object."
    )

    names = [skill["name"] for skill in manager._keyword_retrieve_for_inline(prompt, top_k=3)]

    assert names[0] == "source-parser-state-machine-oob"
    assert "skillclaw-proxy-introspection" not in names
    assert "ida-headless-cwe120-sink-analysis" not in names


def test_inline_retrieval_keeps_skillclaw_meta_for_catalog_task(tmp_path):
    skills_dir = tmp_path / "skills"
    _write_test_skill(
        skills_dir,
        "skillclaw-proxy-introspection",
        "Use when asked to list available skills or probe SkillClaw proxy APIs.",
        "Explain SkillClaw server-side skill catalog and proxy endpoints.",
    )
    _write_test_skill(
        skills_dir,
        "source-parser-state-machine-oob",
        "Find out-of-bounds reads in C parser state machines.",
    )

    manager = SkillManager(str(skills_dir), retrieval_mode="template")
    names = [
        skill["name"]
        for skill in manager._keyword_retrieve_for_inline(
            "Return the SkillClaw server-side skill count from the catalog.",
            top_k=2,
        )
    ]

    assert names == ["skillclaw-proxy-introspection"]


def test_inline_retrieval_ignores_incidental_ssh_noise_in_vulnerability_task(tmp_path):
    skills_dir = tmp_path / "skills"
    _write_test_skill(
        skills_dir,
        "source-parser-state-machine-oob",
        "Find out-of-bounds reads in C parser state machines by tracing source-level bounds guards.",
        "Inspect parser source, lookahead reads, fragment headers, ND_TCHECK, and guard dominance.",
    )
    _write_test_skill(
        skills_dir,
        "ssh-password-recon-workflow",
        "Use when performing remote reconnaissance via SSH with password authentication.",
        "Use paramiko for SSH password login and command execution.",
    )
    _write_test_skill(
        skills_dir,
        "vuln-hunting",
        "General vulnerability hunting workflow for source and binary analysis.",
    )

    manager = SkillManager(str(skills_dir), retrieval_mode="template")
    prompt = (
        "Remote SSH transport is only how this experiment is launched. "
        "Do not use WebSearch. Locate a buffer over-read vulnerability in a tcpdump "
        "IPv6 fragmentation parser by analyzing source code and build artifacts."
    )

    names = [skill["name"] for skill in manager._keyword_retrieve_for_inline(prompt, top_k=3)]

    assert "source-parser-state-machine-oob" in names
    assert "ssh-password-recon-workflow" not in names


def test_inline_retrieval_skips_firmware_workflows_for_source_parser_task(tmp_path):
    skills_dir = tmp_path / "skills"
    _write_test_skill(
        skills_dir,
        "source-parser-state-machine-oob",
        "Find out-of-bounds reads in C parser state machines by tracing source-level bounds guards.",
        "Inspect parser source, lookahead reads, fragment headers, ND_TCHECK, and guard dominance.",
    )
    _write_test_skill(
        skills_dir,
        "vuln-hunting",
        "Use for firmware, binary, and web-exposed target hunting with IDA-assisted workflows. NOT for pure source-code SAST.",
    )
    _write_test_skill(
        skills_dir,
        "verify-rootfs-full-enumeration",
        "Use during extracted firmware or rootfs static analysis before Phase 2 deep dive.",
    )
    _write_test_skill(
        skills_dir,
        "elf-cwe120-firmware-triage",
        "Use when analyzing extracted Linux firmware or rootfs ELF binaries for CWE-120 buffer overflow.",
    )
    _write_test_skill(
        skills_dir,
        "ida-headless-cwe120-sink-analysis",
        "Use IDA headless triage for ELF binaries and CWE-120 sinks.",
    )

    manager = SkillManager(str(skills_dir), retrieval_mode="template")
    prompt = (
        "Locate a source-level buffer over-read in the tcpdump IPv6 fragmentation parser. "
        "Analyze C source code, cur/end guards, and ND_TCHECK coverage."
    )

    names = [skill["name"] for skill in manager._keyword_retrieve_for_inline(prompt, top_k=5)]

    assert "source-parser-state-machine-oob" in names
    assert "vuln-hunting" not in names
    assert "verify-rootfs-full-enumeration" not in names
    assert "elf-cwe120-firmware-triage" not in names
    assert "ida-headless-cwe120-sink-analysis" not in names


def test_inline_retrieval_uses_task_profile_preamble_for_source_only_prompt(tmp_path, monkeypatch):
    monkeypatch.setenv("SKILLCLAW_ENABLE_TASK_PROFILE", "1")
    skills_dir = tmp_path / "skills"
    _write_test_skill(
        skills_dir,
        "source-parser-state-machine-oob",
        "Find out-of-bounds reads in C parser state machines by tracing source-level bounds guards.",
        "Inspect parser source, lookahead reads, fragment headers, ND_TCHECK, and guard dominance.",
    )
    _write_test_skill(
        skills_dir,
        "vuln-hunting",
        "Use for firmware, binary, and web-exposed target hunting with IDA-assisted workflows. NOT for pure source-code SAST.",
    )
    _write_test_skill(
        skills_dir,
        "verify-rootfs-full-enumeration",
        "Use during extracted firmware or rootfs static analysis before Phase 2 deep dive.",
    )
    _write_test_skill(
        skills_dir,
        "ida-headless-cwe120-sink-analysis",
        "Use IDA headless triage for ELF binaries and CWE-120 sinks.",
    )

    manager = SkillManager(str(skills_dir), retrieval_mode="template")
    case = {
        "task_profile": {
            "workspace": "source_tree",
            "target_component": "file_parser",
            "analysis_mode": "source_analysis",
            "bug_class": "memory_safety",
            "input_vector": "crafted_file",
        },
        "prompt": {
            "recommended_blind_skillclaw": (
                "Analyze this target for a memory-safety vulnerability that can be demonstrated "
                "with a crafted GIF input."
            )
        },
    }

    prompt = get_case_prompt(case, "blind-skillclaw-inline")
    names = [skill["name"] for skill in manager._keyword_retrieve_for_inline(prompt, top_k=5)]

    assert "source-parser-state-machine-oob" in names
    assert "vuln-hunting" not in names
    assert "verify-rootfs-full-enumeration" not in names
    assert "ida-headless-cwe120-sink-analysis" not in names


def test_run_single_case_with_existing_agent_output(tmp_path):
    root = tmp_path / "target"
    root.mkdir()
    (root / "HTMLparser.c").write_text(
        "static void htmlParseTryOrFinish(void) { if (avail < 2) in->cur[2]; }\n",
        encoding="utf-8",
    )
    case_path = tmp_path / "case.json"
    case_path.write_text(
        json.dumps(
            {
                "case_id": "demo-case",
                "target": {"source_root": str(root)},
                "ground_truth": {
                    "cves": ["CVE-0000-0001"],
                    "files": ["HTMLparser.c"],
                    "functions": ["htmlParseTryOrFinish"],
                    "root_cause": "weak avail guard before in->cur[2]",
                    "required_evidence": ["avail", "in->cur[2]"],
                },
                "validators": [
                    {
                        "name": "source",
                        "type": "source_contains",
                        "file": "HTMLparser.c",
                        "patterns": ["htmlParseTryOrFinish", "avail", "in->cur[2]"],
                    }
                ],
                "prompt": {"recommended_direct": "analyze target"},
            }
        ),
        encoding="utf-8",
    )
    answer = tmp_path / "answer.txt"
    answer.write_text(
        json.dumps(
            {
                "predicted_cves": ["CVE-0000-0001"],
                "predicted_files": ["HTMLparser.c"],
                "predicted_functions": ["htmlParseTryOrFinish"],
                "root_cause": "weak avail guard before in->cur[2]",
                "evidence": ["avail", "in->cur[2]"],
            }
        ),
        encoding="utf-8",
    )

    final = run_case(
        Namespace(
            case=case_path,
            mode="direct-deepseek",
            root=None,
            output_dir=str(tmp_path / "results"),
            run_id="demo-run",
            model="test-model",
            session_id="",
            injection_json=None,
            agent_output=str(answer),
            no_run_agent=False,
            claude_cmd="claude",
            timeout_seconds=10,
            skip_commands=False,
            final_records=str(tmp_path / "results" / "run_records.jsonl"),
        )
    )

    assert final["score"] == 10
    assert final["validation"]["status"] == "passed"
    assert (tmp_path / "results" / "demo-run-final.json").is_file()
    assert (tmp_path / "results" / "demo-run-manifest.json").is_file()
    index_path = tmp_path / "results" / "run_index.json"
    assert index_path.is_file()
    index_rows = json.loads(index_path.read_text(encoding="utf-8"))
    assert index_rows[0]["run_id"] == "demo-run"
    assert index_rows[0]["validation_status"] == "passed"
    assert final["artifacts"]["manifest"].endswith("demo-run-manifest.json")
    assert final["artifacts"]["run_index"].endswith("run_index.json")


def test_run_single_case_blind_mode_uses_blind_workspace_root(tmp_path):
    source_root = tmp_path / "target"
    source_root.mkdir()
    (source_root / "HTMLparser.c").write_text(
        "static void htmlParseTryOrFinish(void) { if (avail < 2) in->cur[2]; }\n",
        encoding="utf-8",
    )
    blind_root = tmp_path / "blind-target"
    blind_root.mkdir()
    case_path = tmp_path / "case.json"
    case_path.write_text(
        json.dumps(
            {
                "case_id": "demo-blind-case",
                "target": {"source_root": str(source_root)},
                "blind_workspace": {
                    "agent_root": str(blind_root),
                    "validator_root": str(source_root),
                },
                "ground_truth": {
                    "files": ["HTMLparser.c"],
                    "functions": ["htmlParseTryOrFinish"],
                    "vulnerability_type": "oob read",
                    "root_cause": "weak avail guard before in->cur[2]",
                    "required_evidence": ["avail", "in->cur[2]"],
                },
                "validators": [
                    {
                        "name": "source",
                        "type": "source_contains",
                        "file": "HTMLparser.c",
                        "patterns": ["htmlParseTryOrFinish", "avail", "in->cur[2]"],
                    }
                ],
                "prompt": {"recommended_blind_skillclaw": "blind analyze target"},
            }
        ),
        encoding="utf-8",
    )
    answer = tmp_path / "answer.txt"
    answer.write_text(
        json.dumps(
            {
                "predicted_files": ["HTMLparser.c"],
                "predicted_functions": ["htmlParseTryOrFinish"],
                "root_cause": "weak avail guard before in->cur[2]",
                "evidence": ["avail", "in->cur[2]"],
            }
        ),
        encoding="utf-8",
    )

    final = run_case(
        Namespace(
            case=case_path,
            mode="blind-skillclaw-inline-guarded",
            root=None,
            output_dir=str(tmp_path / "results"),
            run_id="demo-blind-run",
            model="test-model",
            session_id="",
            injection_json=None,
            agent_output=str(answer),
            no_run_agent=False,
            claude_cmd="claude",
            timeout_seconds=10,
            skip_commands=False,
            final_records=str(tmp_path / "results" / "run_records.jsonl"),
        )
    )

    assert final["run"]["target_root"] == str(blind_root)
    assert final["run"]["agent_root"] == str(blind_root)
    assert final["run"]["validator_root"] == str(source_root)
    assert final["validation"]["status"] == "passed"


def test_run_single_case_blind_mode_prefers_existing_candidate_roots(tmp_path):
    source_root = tmp_path / "target"
    source_root.mkdir()
    (source_root / "HTMLparser.c").write_text(
        "static void htmlParseTryOrFinish(void) { if (avail < 2) in->cur[2]; }\n",
        encoding="utf-8",
    )
    blind_root = tmp_path / "blind-target"
    blind_root.mkdir()
    case_path = tmp_path / "case.json"
    case_path.write_text(
        json.dumps(
            {
                "case_id": "demo-blind-case-candidates",
                "target": {
                    "project": "demo",
                    "version": "1.0",
                    "source_root": "/missing/remote/target",
                    "source_root_candidates": [str(source_root)],
                },
                "blind_workspace": {
                    "agent_root": "/missing/remote/blind",
                    "agent_root_candidates": [str(blind_root)],
                    "validator_root": "/missing/remote/oracle",
                    "validator_root_candidates": [str(source_root)],
                },
                "ground_truth": {
                    "files": ["HTMLparser.c"],
                    "functions": ["htmlParseTryOrFinish"],
                    "vulnerability_type": "oob read",
                    "root_cause": "weak avail guard before in->cur[2]",
                    "required_evidence": ["avail", "in->cur[2]"],
                },
                "validators": [
                    {
                        "name": "source",
                        "type": "source_contains",
                        "file": "HTMLparser.c",
                        "patterns": ["htmlParseTryOrFinish", "avail", "in->cur[2]"],
                    }
                ],
                "prompt": {"recommended_blind_skillclaw": "blind analyze target"},
            }
        ),
        encoding="utf-8",
    )
    answer = tmp_path / "answer.txt"
    answer.write_text(
        json.dumps(
            {
                "predicted_files": ["HTMLparser.c"],
                "predicted_functions": ["htmlParseTryOrFinish"],
                "root_cause": "weak avail guard before in->cur[2]",
                "evidence": ["avail", "in->cur[2]"],
            }
        ),
        encoding="utf-8",
    )

    final = run_case(
        Namespace(
            case=case_path,
            mode="blind-skillclaw-inline-guarded",
            root=None,
            output_dir=str(tmp_path / "results"),
            run_id="demo-blind-candidate-run",
            model="test-model",
            session_id="",
            injection_json=None,
            agent_output=str(answer),
            no_run_agent=False,
            claude_cmd="claude",
            timeout_seconds=10,
            skip_commands=False,
            final_records=str(tmp_path / "results" / "run_records.jsonl"),
        )
    )

    assert final["run"]["target_root"] == str(blind_root.resolve())
    assert final["run"]["agent_root"] == str(blind_root.resolve())
    assert final["run"]["validator_root"] == str(source_root.resolve())
    assert final["validation"]["status"] == "passed"


def test_run_single_case_can_preflight_before_existing_output(tmp_path):
    root = tmp_path / "target"
    root.mkdir()
    (root / "demo-bin").write_text("binary\n", encoding="utf-8")
    (root / "HTMLparser.c").write_text(
        "static void htmlParseTryOrFinish(void) { if (avail < 2) in->cur[2]; }\n",
        encoding="utf-8",
    )
    case_path = tmp_path / "case.json"
    case_path.write_text(
        json.dumps(
            {
                "case_id": "demo-case",
                "target": {"source_root": str(root), "binary": "demo-bin"},
                "ground_truth": {
                    "cves": ["CVE-0000-0001"],
                    "files": ["HTMLparser.c"],
                    "functions": ["htmlParseTryOrFinish"],
                    "root_cause": "weak avail guard before in->cur[2]",
                    "required_evidence": ["avail", "in->cur[2]"],
                },
                "validators": [
                    {
                        "name": "source",
                        "type": "source_contains",
                        "file": "HTMLparser.c",
                        "patterns": ["htmlParseTryOrFinish", "avail", "in->cur[2]"],
                    }
                ],
                "scoring": {
                    "max_score": 10,
                    "weights": {"cve": 2, "file": 2, "function": 3, "root_cause": 2, "evidence": 1},
                },
                "prompt": {"recommended_direct": "analyze target"},
            }
        ),
        encoding="utf-8",
    )
    settings = tmp_path / "settings.json"
    settings.write_text(
        json.dumps({"env": {"ANTHROPIC_BASE_URL": "https://api.deepseek.com/anthropic", "ANTHROPIC_MODEL": "deepseek-v4-pro"}}),
        encoding="utf-8",
    )
    answer = tmp_path / "answer.txt"
    answer.write_text(
        json.dumps(
            {
                "predicted_cves": ["CVE-0000-0001"],
                "predicted_files": ["HTMLparser.c"],
                "predicted_functions": ["htmlParseTryOrFinish"],
                "root_cause": "weak avail guard before in->cur[2]",
                "evidence": ["avail", "in->cur[2]"],
            }
        ),
        encoding="utf-8",
    )

    final = run_case(
        Namespace(
            case=case_path,
            mode="direct-deepseek",
            root=None,
            output_dir=str(tmp_path / "results"),
            run_id="demo-preflight",
            model="test-model",
            session_id="",
            injection_json=None,
            agent_output=str(answer),
            no_run_agent=False,
            claude_cmd="claude",
            timeout_seconds=10,
            skip_commands=False,
            preflight=True,
            preflight_allow_fail=False,
            preflight_timeout=1.0,
            settings=settings,
            no_claude_settings=False,
            expected_provider="deepseek",
            skillclaw_url="",
            skillclaw_key="",
            expected_skill_count=None,
            final_records=str(tmp_path / "results" / "run_records.jsonl"),
        )
    )

    assert final["preflight"]["status"] == "passed"
    assert final["preflight"]["claude"]["provider"] == "deepseek"
    assert (tmp_path / "results" / "demo-preflight-preflight.json").is_file()


def test_run_single_case_refreshes_directory_index_across_multiple_runs(tmp_path):
    root = tmp_path / "target"
    root.mkdir()
    (root / "HTMLparser.c").write_text(
        "static void htmlParseTryOrFinish(void) { if (avail < 2) in->cur[2]; }\n",
        encoding="utf-8",
    )
    case_path = tmp_path / "case.json"
    case_path.write_text(
        json.dumps(
            {
                "case_id": "demo-case",
                "target": {"source_root": str(root)},
                "ground_truth": {
                    "cves": ["CVE-0000-0001"],
                    "files": ["HTMLparser.c"],
                    "functions": ["htmlParseTryOrFinish"],
                    "root_cause": "weak avail guard before in->cur[2]",
                    "required_evidence": ["avail", "in->cur[2]"],
                },
                "validators": [
                    {
                        "name": "source",
                        "type": "source_contains",
                        "file": "HTMLparser.c",
                        "patterns": ["htmlParseTryOrFinish", "avail", "in->cur[2]"],
                    }
                ],
                "scoring": {
                    "max_score": 10,
                    "weights": {"cve": 2, "file": 2, "function": 3, "root_cause": 2, "evidence": 1},
                },
                "prompt": {"recommended_direct": "analyze target"},
            }
        ),
        encoding="utf-8",
    )
    answer = tmp_path / "answer.txt"
    answer.write_text(
        json.dumps(
            {
                "predicted_cves": ["CVE-0000-0001"],
                "predicted_files": ["HTMLparser.c"],
                "predicted_functions": ["htmlParseTryOrFinish"],
                "root_cause": "weak avail guard before in->cur[2]",
                "evidence": ["avail", "in->cur[2]"],
            }
        ),
        encoding="utf-8",
    )

    for run_id in ["demo-run-a", "demo-run-b"]:
        run_case(
            Namespace(
                case=case_path,
                mode="direct-deepseek",
                root=None,
                output_dir=str(tmp_path / "results"),
                run_id=run_id,
                model="test-model",
                session_id="",
                injection_json=None,
                agent_output=str(answer),
                no_run_agent=False,
                claude_cmd="claude",
                timeout_seconds=10,
                skip_commands=False,
                final_records=str(tmp_path / "results" / "run_records.jsonl"),
            )
        )

    index_rows = json.loads((tmp_path / "results" / "run_index.json").read_text(encoding="utf-8"))
    run_ids = {row["run_id"] for row in index_rows}
    assert {"demo-run-a", "demo-run-b"} <= run_ids


def test_run_case_batch_runs_multiple_manifest_entries(tmp_path):
    root = tmp_path / "target"
    root.mkdir()
    (root / "HTMLparser.c").write_text(
        "static void htmlParseTryOrFinish(void) { if (avail < 2) in->cur[2]; }\n",
        encoding="utf-8",
    )
    case_path = tmp_path / "case.json"
    case_path.write_text(
        json.dumps(
            {
                "case_id": "demo-case",
                "target": {"source_root": str(root)},
                "ground_truth": {
                    "cves": ["CVE-0000-0001"],
                    "files": ["HTMLparser.c"],
                    "functions": ["htmlParseTryOrFinish"],
                    "root_cause": "weak avail guard before in->cur[2]",
                    "required_evidence": ["avail", "in->cur[2]"],
                },
                "validators": [
                    {
                        "name": "source",
                        "type": "source_contains",
                        "file": "HTMLparser.c",
                        "patterns": ["htmlParseTryOrFinish", "avail", "in->cur[2]"],
                    }
                ],
                "scoring": {
                    "max_score": 10,
                    "weights": {"cve": 2, "file": 2, "function": 3, "root_cause": 2, "evidence": 1},
                },
                "prompt": {
                    "recommended_direct": "analyze target",
                    "recommended_skillclaw": "analyze target with skills",
                },
            }
        ),
        encoding="utf-8",
    )
    answer = tmp_path / "answer.txt"
    answer.write_text(
        json.dumps(
            {
                "predicted_cves": ["CVE-0000-0001"],
                "predicted_files": ["HTMLparser.c"],
                "predicted_functions": ["htmlParseTryOrFinish"],
                "root_cause": "weak avail guard before in->cur[2]",
                "evidence": ["avail", "in->cur[2]"],
            }
        ),
        encoding="utf-8",
    )
    manifest = tmp_path / "batch.json"
    manifest.write_text(
        json.dumps(
            {
                "defaults": {
                    "output_dir": "batch-results",
                    "agent_output": "answer.txt",
                    "skip_commands": False,
                    "mode": "direct-deepseek",
                },
                "runs": [
                    {"case": "case.json", "run_id": "demo-a"},
                    {"case": "case.json", "run_id": "demo-b", "mode": "skillclaw-inline"},
                ],
            }
        ),
        encoding="utf-8",
    )

    summary = run_batch(manifest)

    assert summary["failure_count"] == 0
    assert summary["run_count"] == 2
    assert summary["rows"][0]["status"] == "ok"
    assert summary["rows"][1]["mode"] == "skillclaw-inline"
    assert (tmp_path / "batch-results" / "demo-a-final.json").is_file()
    assert (tmp_path / "batch-results" / "demo-b-final.json").is_file()


def test_exiv2_prepare_artifacts_and_wrapper_smoke(tmp_path):
    root = tmp_path / "exiv2-0.26"
    (root / "artifacts").mkdir(parents=True)
    (root / "bin").mkdir(parents=True)
    (root / "bin" / "exiv2").write_text("placeholder\n", encoding="utf-8")

    prepare_script = (
        Path("benchmarks")
        / "confirmations"
        / "exiv2-0.26-cve-2017-17725"
        / "prepare_confirmation_artifacts.sh"
    ).resolve()
    generate_input_script = (
        Path("benchmarks")
        / "confirmations"
        / "exiv2-0.26-cve-2017-17725"
        / "generate_confirmation_input.py"
    ).resolve()

    poc_path = root / "artifacts" / "poc-cve-2017-17725.jp2"
    legacy_alias_path = root / "artifacts" / "poc-cve-2017-17725.tiff"
    wrapper_path = root / "artifacts" / "run_exiv2_poc.sh"
    if shutil.which("bash"):
        subprocess.run(
            f'bash "{prepare_script}"',
            cwd=root,
            shell=True,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        assert poc_path.is_file()
        assert poc_path.stat().st_size >= 32
        assert legacy_alias_path.is_file()
        poc_bytes = poc_path.read_bytes()
        assert b"jP  " in poc_bytes
        assert b"jp2h" in poc_bytes
        assert b"colr" in poc_bytes
        assert wrapper_path.is_file()

        proc = subprocess.run(
            'bash "artifacts/run_exiv2_poc.sh" --smoke-only',
            cwd=root,
            shell=True,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        combined = f"{proc.stdout}\n{proc.stderr}"
        assert "RUN_EXIV2_POC" in combined
        assert "WRAPPER_SMOKE_OK" in combined

        probe = subprocess.run(
            'bash "artifacts/run_exiv2_poc.sh" --probe-only',
            cwd=root,
            shell=True,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        combined_probe = f"{probe.stdout}\n{probe.stderr}"
        assert "RUN_EXIV2_POC" in combined_probe
        assert "WRAPPER_PROBE_OK" in combined_probe
        assert "TARGET_EXECUTION_RC=" in combined_probe

        behavior = subprocess.run(
            'bash "artifacts/run_exiv2_poc.sh"',
            cwd=root,
            shell=True,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        combined_behavior = f"{behavior.stdout}\n{behavior.stderr}"
        assert "RUN_EXIV2_POC" in combined_behavior
        assert "EXIV2_JP2_ICC_PATH_OK" in combined_behavior
        assert "EXIV2_ASAN_OOB_OK" in combined_behavior
        assert "TARGET_EXECUTION_RC=" in combined_behavior
        assert behavior.returncode != 0
    else:
        subprocess.run(
            [sys.executable, str(generate_input_script), str(poc_path)],
            cwd=root,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert poc_path.is_file()
        assert poc_path.stat().st_size >= 32
        assert not legacy_alias_path.exists()
        poc_bytes = poc_path.read_bytes()
        assert b"jP  " in poc_bytes
        assert b"jp2h" in poc_bytes
        assert b"colr" in poc_bytes
        wrapper_text = prepare_script.read_text(encoding="utf-8")
        helper_text = (
            Path("benchmarks")
            / "confirmations"
            / "common"
            / "confirmation_helpers.sh"
        ).read_text(encoding="utf-8")
        assert "--smoke-only" in wrapper_text
        assert "WRAPPER_SMOKE_OK" in wrapper_text
        assert "--probe-only" in wrapper_text
        assert "WRAPPER_PROBE_OK" in wrapper_text
        assert "TARGET_EXECUTION_RC=" in helper_text
        assert "behavior" in wrapper_text
        assert "EXIV2_JP2_ICC_PATH_OK" in wrapper_text
        assert "EXIV2_ICC_SIZE" in wrapper_text


def test_exiv2_generate_confirmation_input_supports_tunable_icc_size(tmp_path):
    script = (
        Path("benchmarks")
        / "confirmations"
        / "exiv2-0.26-cve-2017-17725"
        / "generate_confirmation_input.py"
    ).resolve()
    out_default = tmp_path / "default.jp2"
    out_large = tmp_path / "large.jp2"

    subprocess.run(
        [sys.executable, str(script), str(out_default)],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    subprocess.run(
        [sys.executable, str(script), str(out_large), "--icc-size", "12"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    default_bytes = out_default.read_bytes()
    large_bytes = out_large.read_bytes()
    assert b"colr" in default_bytes
    assert b"colr" in large_bytes
    assert len(large_bytes) > len(default_bytes)


def test_plan_exiv2_confirmation_parameter_scan_renders_commands(tmp_path):
    script = (
        Path("benchmarks")
        / "confirmations"
        / "exiv2-0.26-cve-2017-17725"
        / "sweep_confirmation_parameters.py"
    ).resolve()
    case_path = (
        Path("benchmarks")
        / "cases"
        / "exiv2-0.26-cve-2017-17725.json"
    ).resolve()
    out_path = tmp_path / "sweep.md"

    subprocess.run(
        [
            sys.executable,
            str(script),
            "plan",
            str(case_path),
            "--root",
            "/tmp/exiv2-0.26",
            "--icc-sizes",
            "4,5",
            "--colr-methods",
            "2,3",
            "--out",
            str(out_path),
        ],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    text = out_path.read_text(encoding="utf-8")
    assert "Total combinations: `4`" in text
    assert "EXIV2_ICC_SIZE=4" in text
    assert "EXIV2_ICC_SIZE=5" in text
    assert "EXIV2_COLR_METHOD=3" in text
    assert "EXIV2_JP2_ICC_PATH_OK" in text


def test_record_and_summarize_exiv2_sweep(tmp_path):
    script = (
        Path("benchmarks")
        / "confirmations"
        / "exiv2-0.26-cve-2017-17725"
        / "sweep_confirmation_parameters.py"
    ).resolve()
    stdout_path = tmp_path / "stdout.txt"
    stderr_path = tmp_path / "stderr.txt"
    jsonl_path = tmp_path / "sweep.jsonl"
    summary_path = tmp_path / "summary.md"

    stdout_path.write_text("synthetic stdout\n", encoding="utf-8")
    stderr_path.write_text(
        "\n".join(
            [
                "Jp2Image::readMetadata DataBuf(5)",
                "AddressSanitizer: heap-buffer-overflow in getULong (types.cpp)",
                "EXIV2_JP2_ICC_PATH_OK jp2-readmetadata-getulong",
                "EXIV2_ASAN_OOB_OK heap-buffer-overflow",
                "TARGET_EXECUTION_RC=134",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    subprocess.run(
        [
            sys.executable,
            str(script),
            "record",
            "--icc-size",
            "5",
            "--colr-method",
            "2",
            "--stdout-file",
            str(stdout_path),
            "--stderr-file",
            str(stderr_path),
            "--returncode",
            "134",
            "--label",
            "combo-5",
            "--out",
            str(jsonl_path),
        ],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    subprocess.run(
        [
            sys.executable,
            str(script),
            "summarize",
            str(jsonl_path),
            "--out",
            str(summary_path),
        ],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    text = summary_path.read_text(encoding="utf-8")
    assert "combo-5" in text
    assert "EXIV2_JP2_ICC_PATH_OK" in text
    assert "EXIV2_ASAN_OOB_OK" in text
    assert "134" in text


def test_judge_exiv2_sweep_candidates(tmp_path):
    judge_script = (
        Path("benchmarks")
        / "confirmations"
        / "exiv2-0.26-cve-2017-17725"
        / "sweep_confirmation_parameters.py"
    ).resolve()
    jsonl_path = tmp_path / "sweep.jsonl"
    out_md = tmp_path / "rank.md"
    out_json = tmp_path / "rank.json"

    rows = [
        {
            "label": "weak",
            "params": {"icc_size": 4, "colr_method": 2, "width": 1, "height": 1},
            "returncode": 1,
            "matched_markers": ["Jp2Image::readMetadata"],
        },
        {
            "label": "strong",
            "params": {"icc_size": 5, "colr_method": 2, "width": 1, "height": 1},
            "returncode": 134,
            "matched_markers": [
                "EXIV2_JP2_ICC_PATH_OK",
                "EXIV2_ASAN_OOB_OK",
                "TARGET_EXECUTION_RC=",
                "AddressSanitizer",
                "Jp2Image::readMetadata",
                "getULong",
            ],
        },
    ]
    with jsonl_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    subprocess.run(
        [
            sys.executable,
            str(judge_script),
            "judge",
            str(jsonl_path),
            "--out",
            str(out_md),
            "--out-json",
            str(out_json),
        ],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    md_text = out_md.read_text(encoding="utf-8")
    json_text = out_json.read_text(encoding="utf-8")
    assert "strong_candidate" in md_text
    assert "Best Current Candidate" in md_text
    assert "\"label\": \"strong\"" in json_text


def test_run_case_infers_session_id_and_attaches_injection(tmp_path):
    root = tmp_path / "target"
    root.mkdir()
    (root / "HTMLparser.c").write_text(
        "static void htmlParseTryOrFinish(void) { if (avail < 2) in->cur[2]; }\n",
        encoding="utf-8",
    )
    case_path = tmp_path / "case.json"
    case_path.write_text(
        json.dumps(
            {
                "case_id": "demo-case",
                "target": {"source_root": str(root), "project": "parser"},
                "ground_truth": {
                    "cves": ["CVE-0000-0001"],
                    "files": ["HTMLparser.c"],
                    "functions": ["htmlParseTryOrFinish"],
                    "root_cause": "weak avail guard before in->cur[2]",
                    "required_evidence": ["avail", "in->cur[2]"],
                },
                "validators": [
                    {
                        "name": "source",
                        "type": "source_contains",
                        "file": "HTMLparser.c",
                        "patterns": ["htmlParseTryOrFinish", "avail", "in->cur[2]"],
                    }
                ],
                "scoring": {
                    "max_score": 10,
                    "weights": {"cve": 2, "file": 2, "function": 3, "root_cause": 2, "evidence": 1},
                },
                "prompt": {
                    "recommended_direct": "analyze target",
                    "recommended_skillclaw": "analyze target with skills",
                },
            }
        ),
        encoding="utf-8",
    )
    answer = tmp_path / "answer.txt"
    answer.write_text(
        json.dumps(
            {
                "predicted_cves": ["CVE-0000-0001"],
                "predicted_files": ["HTMLparser.c"],
                "predicted_functions": ["htmlParseTryOrFinish"],
                "root_cause": "weak avail guard before in->cur[2]",
                "evidence": ["avail", "in->cur[2]"],
            }
        ),
        encoding="utf-8",
    )
    now_local = datetime.now().astimezone()
    ts_old = (now_local - timedelta(minutes=20)).strftime("%Y-%m-%d %H:%M:%S")
    ts_target = (now_local - timedelta(seconds=2)).strftime("%Y-%m-%d %H:%M:%S")
    injection_json = tmp_path / "conversations.jsonl"
    injection_json.write_text(
        "\n".join(
            [
                json.dumps({"session_id": "older", "timestamp": ts_old, "turn": 8, "selected_skill_names": ["other"]}),
                json.dumps(
                    {
                        "session_id": "target",
                        "timestamp": ts_target,
                        "turn": 1,
                        "injection_mode": "inline",
                        "selected_skill_names": ["source-parser-state-machine-oob"],
                        "available_skill_count": 35,
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    final = run_case(
        Namespace(
            case=case_path,
            mode="skillclaw-inline",
            root=None,
            output_dir=str(tmp_path / "results"),
            run_id="demo-infer-session",
            model="skillclaw-model",
            session_id="",
            injection_json=injection_json,
            agent_output=str(answer),
            no_run_agent=False,
            claude_cmd="claude",
            timeout_seconds=10,
            skip_commands=False,
            preflight=False,
            preflight_allow_fail=False,
            preflight_timeout=1.0,
            settings=tmp_path / "settings.json",
            no_claude_settings=True,
            expected_provider=None,
            skillclaw_url="",
            skillclaw_key="",
            expected_skill_count=None,
            final_records=str(tmp_path / "results" / "run_records.jsonl"),
        )
    )

    assert final["session_id"] == "target"
    assert final["session_id_source"] == "inferred_from_injection_log"
    assert final["skill_injection"]["selected_skill_names"] == ["source-parser-state-machine-oob"]


def test_smoke_check_cases_runs_repository_cases():
    results = smoke_cases(Path("benchmarks"))

    statuses = {item["case_id"]: item["status"] for item in results}
    assert statuses["exiv2-0.26-cve-2017-17725"] == "passed"
    assert statuses["giflib-5.1.2-cve-2016-3977"] == "passed"
    assert statuses["libxml2-2.9.4-cve-2017-8872"] == "passed"
    assert statuses["libarchive-3.8.0-cve-2025-60753"] == "passed"
    assert statuses["tcpdump-4.9.1-cve-2017-13031"] == "passed"


def test_build_result_matrix_writes_matrix(tmp_path):
    final_record = tmp_path / "demo-final.json"
    final_record.write_text(
        json.dumps(
            {
                "case_id": "demo-case",
                "mode": "skillclaw-inline",
                "model": "skillclaw-model",
                "score": 8,
                "max_score": 10,
                "checks": {
                    "cve": {"hit": False},
                    "file": {"hit": True},
                    "function": {"hit": True},
                    "evidence": {"hit": True},
                    "root_cause": {"hit": True},
                },
                "skill_injection": {
                    "selected_skill_names": ["skillclaw-proxy-introspection"],
                },
                "skill_relevance": {
                    "status": "only_infra_skills",
                    "relevant_skills": [],
                },
                "confirmation_maturity": "behavior-backed",
                "confirmation_current_claim": "runtime marker path is confirmed",
                "validation": {"status": "passed"},
                "feedback": {
                    "decision": "neutral",
                    "suggested_action": "inspect_retrieval_before_promoting_skill",
                },
            }
        ),
        encoding="utf-8",
    )

    rows = collect_rows([final_record])
    md_path = tmp_path / "result_matrix.md"
    csv_path = tmp_path / "matrix.csv"
    write_markdown(rows, md_path)
    write_csv(rows, csv_path)

    assert rows[0]["score_text"] == "8/10"
    assert rows[0]["file_hit"] == "Y"
    assert rows[0]["cve_hit"] == "N"
    assert rows[0]["confirmation_maturity"] == "behavior-backed"
    assert "only_infra_skills" in md_path.read_text(encoding="utf-8")
    assert "confirmation_maturity" in md_path.read_text(encoding="utf-8")
    assert "inspect_retrieval_before_promoting_skill" in csv_path.read_text(encoding="utf-8")
    assert "behavior-backed" in csv_path.read_text(encoding="utf-8")


def test_refresh_latest_runset_reports_rebuilds_outputs_in_order(tmp_path):
    record_a = tmp_path / "case-a-final.json"
    record_b = tmp_path / "case-b-final.json"
    record_a.write_text(
        json.dumps(
            {
                "case_id": "case-a",
                "mode": "skillclaw-inline",
                "model": "skillclaw-model",
                "score": 10,
                "max_score": 10,
                "checks": {
                    "cve": {"hit": True},
                    "file": {"hit": True},
                    "function": {"hit": True},
                    "evidence": {"hit": True},
                    "root_cause": {"hit": True},
                },
                "skill_injection": {"selected_skill_names": ["source-parser-state-machine-oob"]},
                "skill_relevance": {
                    "status": "has_task_relevant_skill",
                    "relevant_skills": ["source-parser-state-machine-oob"],
                    "mismatched_skills": [],
                    "infra_skills": [],
                },
                "validation": {"status": "passed", "checks": []},
                "confirmation_maturity": "behavior-backed",
                "feedback": {"decision": "positive", "suggested_action": "keep_or_promote_skill"},
            }
        ),
        encoding="utf-8",
    )
    record_b.write_text(
        json.dumps(
            {
                "case_id": "case-b",
                "mode": "skillclaw-inline",
                "model": "skillclaw-model",
                "score": 10,
                "max_score": 10,
                "checks": {
                    "cve": {"hit": True},
                    "file": {"hit": True},
                    "function": {"hit": True},
                    "evidence": {"hit": True},
                    "root_cause": {"hit": True},
                },
                "skill_injection": {"selected_skill_names": ["vuln-hunting"]},
                "skill_relevance": {
                    "status": "mixed_task_relevance",
                    "relevant_skills": [],
                    "mismatched_skills": ["vuln-hunting"],
                    "infra_skills": [],
                },
                "validation": {"status": "passed", "checks": []},
                "confirmation_maturity": "intermediate-confirmed-path",
                "feedback": {
                    "decision": "neutral",
                    "suggested_action": "keep_skill_but_prune_extraneous_selection",
                },
            }
        ),
        encoding="utf-8",
    )
    manifest = tmp_path / "runset_manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "name": "test-runset",
                "min_samples": 1,
                "promote_samples": 2,
                "records": [record_a.name, record_b.name],
                "outputs": {
                    "matrix_md": "result_matrix.md",
                    "matrix_csv": "matrix.csv",
                    "feedback_md": "feedback.md",
                    "feedback_csv": "feedback.csv",
                    "gate_md": "gate.md",
                    "gate_json": "gate.json",
                    "bundle_md": "bundle.md",
                    "bundle_json": "bundle.json",
                    "runset_md": "runset.md",
                },
            }
        ),
        encoding="utf-8",
    )

    result = refresh_reports(manifest)
    gate = json.loads((tmp_path / "gate.json").read_text(encoding="utf-8"))

    assert Path(result["outputs"]["matrix_md"]).is_file()
    assert Path(result["outputs"]["runset_md"]).is_file()
    runset_text = (tmp_path / "runset.md").read_text(encoding="utf-8")
    assert "confirmation" in runset_text
    assert "source_type" in runset_text
    assert "record" in runset_text
    assert "behavior-backed" in runset_text
    assert str(tmp_path).replace("\\", "/") not in runset_text
    by_skill = {row["skill"]: row for row in gate}
    assert by_skill["source-parser-state-machine-oob"]["gate_decision"] == "keep"
    assert by_skill["vuln-hunting"]["gate_decision"] == "demote"


def test_refresh_latest_runset_reports_accepts_run_manifests(tmp_path):
    record = tmp_path / "case-a-final.json"
    record.write_text(
        json.dumps(
            {
                "case_id": "case-a",
                "mode": "skillclaw-inline",
                "model": "skillclaw-model",
                "score": 10,
                "max_score": 10,
                "checks": {
                    "cve": {"hit": True},
                    "file": {"hit": True},
                    "function": {"hit": True},
                    "evidence": {"hit": True},
                    "root_cause": {"hit": True},
                },
                "skill_injection": {"selected_skill_names": ["source-parser-state-machine-oob"]},
                "skill_relevance": {
                    "status": "matched_task_skill",
                    "relevant_skills": ["source-parser-state-machine-oob"],
                    "mismatched_skills": [],
                    "infra_skills": [],
                },
                "validation": {"status": "passed", "checks": []},
                "confirmation_maturity": "behavior-backed",
                "feedback": {"decision": "positive", "suggested_action": "keep_and_expand_cases"},
            }
        ),
        encoding="utf-8",
    )
    run_manifest = tmp_path / "case-a-manifest.json"
    run_manifest.write_text(
        json.dumps(
            {
                "run_id": "case-a-run",
                "artifacts": {
                    "final": str(record.resolve()),
                },
            }
        ),
        encoding="utf-8",
    )
    manifest = tmp_path / "runset_manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "name": "test-runset-manifest-input",
                "min_samples": 1,
                "promote_samples": 2,
                "manifests": [run_manifest.name],
                "outputs": {
                    "matrix_md": "result_matrix.md",
                    "matrix_csv": "matrix.csv",
                    "feedback_md": "feedback.md",
                    "feedback_csv": "feedback.csv",
                    "gate_md": "gate.md",
                    "gate_json": "gate.json",
                    "bundle_md": "bundle.md",
                    "bundle_json": "bundle.json",
                    "runset_md": "runset.md",
                },
            }
        ),
        encoding="utf-8",
    )

    result = refresh_reports(manifest)

    assert Path(result["outputs"]["matrix_md"]).is_file()
    runset_text = (tmp_path / "runset.md").read_text(encoding="utf-8")
    assert "case-a" in runset_text
    assert "manifest" in runset_text
    assert "behavior-backed" in runset_text
    assert str(tmp_path).replace("\\", "/") not in runset_text
    record_sources = result["record_sources"]
    assert next(iter(record_sources.values()))["input_type"] == "manifest"


def test_refresh_latest_runset_reports_accepts_run_indexes(tmp_path):
    record_a = tmp_path / "case-a-final.json"
    record_b = tmp_path / "case-b-final.json"
    for path, case_id, skill, confirmation in [
        (record_a, "case-a", "source-parser-state-machine-oob", "behavior-backed"),
        (record_b, "case-b", "vuln-hunting", "intermediate-confirmed-path"),
    ]:
        path.write_text(
            json.dumps(
                {
                    "case_id": case_id,
                    "mode": "skillclaw-inline",
                    "model": "skillclaw-model",
                    "score": 10,
                    "max_score": 10,
                    "checks": {
                        "cve": {"hit": True},
                        "file": {"hit": True},
                        "function": {"hit": True},
                        "evidence": {"hit": True},
                        "root_cause": {"hit": True},
                    },
                    "skill_injection": {"selected_skill_names": [skill]},
                    "skill_relevance": {
                        "status": "matched_task_skill" if skill.startswith("source-parser") else "mixed_task_relevance",
                        "relevant_skills": [skill] if skill.startswith("source-parser") else [],
                        "mismatched_skills": [] if skill.startswith("source-parser") else [skill],
                        "infra_skills": [],
                    },
                    "validation": {"status": "passed", "checks": []},
                    "confirmation_maturity": confirmation,
                    "feedback": {
                        "decision": "positive" if skill.startswith("source-parser") else "neutral",
                        "suggested_action": "keep_and_expand_cases",
                    },
                }
            ),
            encoding="utf-8",
        )
    run_index = tmp_path / "run_index.json"
    run_index.write_text(
        json.dumps(
            [
                {"run_id": "a", "artifacts": {"final": str(record_a.resolve())}},
                {"run_id": "b", "artifacts": {"final": str(record_b.resolve())}},
            ]
        ),
        encoding="utf-8",
    )
    manifest = tmp_path / "runset_manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "name": "test-runset-index-input",
                "min_samples": 1,
                "promote_samples": 2,
                "run_indexes": [run_index.name],
                "outputs": {
                    "matrix_md": "result_matrix.md",
                    "matrix_csv": "matrix.csv",
                    "feedback_md": "feedback.md",
                    "feedback_csv": "feedback.csv",
                    "gate_md": "gate.md",
                    "gate_json": "gate.json",
                    "bundle_md": "bundle.md",
                    "bundle_json": "bundle.json",
                    "runset_md": "runset.md",
                },
            }
        ),
        encoding="utf-8",
    )

    result = refresh_reports(manifest)

    assert Path(result["outputs"]["matrix_md"]).is_file()
    runset_text = (tmp_path / "runset.md").read_text(encoding="utf-8")
    assert "case-a" in runset_text
    assert "case-b" in runset_text
    assert "run_index" in runset_text
    assert "intermediate-confirmed-path" in runset_text
    assert str(tmp_path).replace("\\", "/") not in runset_text


def test_refresh_latest_runset_reports_falls_back_to_case_confirmation_metadata(tmp_path):
    repo_root = tmp_path / "repo"
    (repo_root / "benchmarks" / "cases").mkdir(parents=True)
    (repo_root / "reports").mkdir(parents=True)

    record = repo_root / "reports" / "case-a-final.json"
    record.write_text(
        json.dumps(
            {
                "case_id": "case-a",
                "mode": "skillclaw-inline",
                "model": "skillclaw-model",
                "score": 10,
                "max_score": 10,
                "checks": {
                    "cve": {"hit": True},
                    "file": {"hit": True},
                    "function": {"hit": True},
                    "evidence": {"hit": True},
                    "root_cause": {"hit": True},
                },
                "skill_injection": {"selected_skill_names": ["source-parser-state-machine-oob"]},
                "skill_relevance": {
                    "status": "matched_task_skill",
                    "relevant_skills": ["source-parser-state-machine-oob"],
                    "mismatched_skills": [],
                    "infra_skills": [],
                },
                "validation": {"status": "passed", "checks": []},
                "feedback": {"decision": "positive", "suggested_action": "keep_and_expand_cases"},
            }
        ),
        encoding="utf-8",
    )
    (repo_root / "benchmarks" / "cases" / "case-a.json").write_text(
        json.dumps(
            {
                "case_id": "case-a",
                "confirmation": {
                    "maturity": "behavior-backed",
                    "current_claim": "runtime marker path is confirmed",
                },
            }
        ),
        encoding="utf-8",
    )
    manifest = repo_root / "reports" / "runset_manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "name": "test-runset-confirmation-fallback",
                "records": [record.name],
                "outputs": {
                    "matrix_md": "result_matrix.md",
                    "matrix_csv": "matrix.csv",
                    "feedback_md": "feedback.md",
                    "gate_md": "gate.md",
                    "gate_json": "gate.json",
                    "bundle_json": "bundle.json",
                    "runset_md": "runset.md",
                },
            }
        ),
        encoding="utf-8",
    )

    refresh_reports(manifest)

    matrix_text = (repo_root / "reports" / "result_matrix.md").read_text(encoding="utf-8")
    assert "behavior-backed" in matrix_text
    matrix_csv = (repo_root / "reports" / "matrix.csv").read_text(encoding="utf-8")
    assert "runtime marker path is confirmed" in matrix_csv


def test_build_result_matrix_falls_back_for_legacy_skill_relevance(tmp_path):
    final_record = tmp_path / "legacy-final.json"
    final_record.write_text(
        json.dumps(
            {
                "case_id": "legacy-case",
                "mode": "skillclaw-inline",
                "score": 8,
                "max_score": 10,
                "checks": {"file": {"hit": True}},
                "skill_injection": {
                    "selected_skill_names": [
                        "source-parser-state-machine-oob",
                        "skillclaw-skill-discovery",
                    ],
                },
                "validation": {"status": "passed"},
            }
        ),
        encoding="utf-8",
    )

    rows = collect_rows([final_record])

    assert rows[0]["skill_relevance"] == "legacy_has_non_infra_skill"
    assert rows[0]["relevant_skills"] == "source-parser-state-machine-oob"


def test_build_result_matrix_preserves_confirmation_fields(tmp_path):
    final_record = tmp_path / "confirm-final.json"
    final_record.write_text(
        json.dumps(
            {
                "case_id": "confirm-case",
                "mode": "skillclaw-inline",
                "score": 10,
                "max_score": 10,
                "checks": {"file": {"hit": True}, "function": {"hit": True}},
                "confirmation_maturity": "intermediate-confirmed-path",
                "confirmation_current_claim": "current path is readMetadata -> memcpy",
                "validation": {"status": "passed"},
            }
        ),
        encoding="utf-8",
    )

    rows = collect_rows([final_record])

    assert rows[0]["confirmation_maturity"] == "intermediate-confirmed-path"
    assert rows[0]["confirmation_current_claim"] == "current path is readMetadata -> memcpy"


def test_summarize_research_claims_extracts_conservative_observations(tmp_path):
    records = []
    for name, mode, score, cve_hit in [
        ("skill-low", "skillclaw-inline-guarded-clean-budget035", 8, False),
        ("direct-low", "direct-deepseek-guarded-clean-budget035", 0, False),
        ("skill-high", "skillclaw-inline-guarded-clean-budget080", 8, False),
        ("direct-high", "direct-deepseek-guarded-clean-budget080", 10, True),
    ]:
        path = tmp_path / f"{name}-final.json"
        path.write_text(
            json.dumps(
                {
                    "case_id": "demo-case",
                    "mode": mode,
                    "model": "demo",
                    "score": score,
                    "max_score": 10,
                    "checks": {
                        "cve": {"hit": cve_hit},
                        "file": {"hit": score > 0},
                        "function": {"hit": score > 0},
                        "evidence": {"hit": score > 0},
                        "root_cause": {"hit": score > 0},
                    },
                "skill_injection": {
                    "selected_skill_names": ["source-parser-state-machine-oob"],
                }
                if mode.startswith("skillclaw")
                else None,
                "confirmation_maturity": "behavior-backed" if mode.startswith("skillclaw") else "",
            }
        ),
        encoding="utf-8",
        )
        records.append(path)

    claims = build_claims(collect_rows(records))
    out_md = tmp_path / "claims.md"
    write_claim_markdown(claims, out_md)
    text = out_md.read_text(encoding="utf-8")

    assert claims["aggregate"]["cases"] == 1
    assert claims["aggregate"]["skillclaw_cve_misses_with_localization"] == 2
    assert claims["cases"][0]["skillclaw_confirmation_maturity"] == "behavior-backed"
    assert "SkillClaw produced a stronger low-budget result" in text
    assert "direct LLM outperformed SkillClaw under the high-budget setting" in text
    assert "CVE identity failure" in text
    assert "SkillClaw confirmation" in text


def test_audit_run_layout_flags_root_level_run_files(tmp_path):
    run_dirs = tmp_path / "confirmations"
    run_dirs.mkdir()

    complete = run_dirs / "demo-run-1"
    complete.mkdir()
    (complete / "demo-run-1-final.json").write_text("{}", encoding="utf-8")
    (complete / "demo-run-1-validation.json").write_text("{}", encoding="utf-8")
    (complete / "demo-run-1-prompt.txt").write_text("prompt", encoding="utf-8")

    partial = run_dirs / "demo-run-2"
    partial.mkdir()
    (partial / "demo-run-2-prompt.txt").write_text("prompt", encoding="utf-8")

    (run_dirs / "legacy-run.prompt.txt").write_text("prompt", encoding="utf-8")
    (run_dirs / "legacy-run.claude.json").write_text("{}", encoding="utf-8")
    (run_dirs / "README.md").write_text("index", encoding="utf-8")

    report = audit_run_layout(run_dirs)

    assert report["directory_count"] == 2
    assert report["complete_run_directories"] == 1
    assert report["partial_run_directories"] == 1
    assert report["root_run_file_count"] == 2
    assert sorted(report["root_run_files"]) == ["legacy-run.claude.json", "legacy-run.prompt.txt"]
    assert "README.md" in report["other_files"]


def test_audit_run_layout_treats_manifest_backed_run_as_complete(tmp_path):
    run_dirs = tmp_path / "confirmations"
    run_dirs.mkdir()

    run_dir = run_dirs / "demo-run-1"
    run_dir.mkdir()
    (run_dir / "demo-run-1-final-enriched.json").write_text("{}", encoding="utf-8")
    (run_dir / "manifest.json").write_text("{}", encoding="utf-8")
    (run_dir / "run_index.json").write_text("{}", encoding="utf-8")

    report = audit_run_layout(run_dirs)

    assert report["directory_count"] == 1
    assert report["complete_run_directories"] == 1
    assert report["partial_run_directories"] == 0
    assert report["run_directories"][0]["has_manifest"] is True
    assert report["run_directories"][0]["has_run_index"] is True


def test_backfill_run_manifest_creates_manifest_and_directory_index(tmp_path):
    run_dir = tmp_path / "remote-run"
    run_dir.mkdir()
    final_record = run_dir / "demo-case-skillclaw-inline-20260710-000000-final-enriched.json"
    final_record.write_text(
        json.dumps(
            {
                "case_id": "demo-case",
                "mode": "skillclaw-inline",
                "model": "skillclaw-model",
                "timestamp": "2026-07-10T10:00:00+00:00",
                "score": 10,
                "max_score": 10,
                "validation": {"status": "passed"},
                "skill_injection": {"selected_skill_names": ["source-parser-state-machine-oob"]},
                "skill_relevance": {"status": "matched_task_skill"},
                "confirmation_maturity": "behavior-backed",
            }
        ),
        encoding="utf-8",
    )

    manifest_path = backfill_run_manifest(final_record)

    assert manifest_path.is_file()
    assert manifest_path.name == "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["run_id"] == "demo-case-skillclaw-inline-20260710-000000"
    assert manifest["validation_status"] == "passed"
    assert manifest["artifacts"]["final"] == str(final_record.resolve())
    index_path = run_dir / "run_index.json"
    assert index_path.is_file()
    index_rows = json.loads(index_path.read_text(encoding="utf-8"))
    assert index_rows[0]["run_id"] == manifest["run_id"]


def _write_skill(root, name, description, body="workflow"):
    skill_dir = root / name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: \"{description}\"\ncategory: general\n---\n\n{body}\n",
        encoding="utf-8",
    )


def test_inline_keyword_retrieval_downranks_skillclaw_meta_for_vuln_tasks(tmp_path):
    _write_skill(
        tmp_path,
        "skillclaw-proxy-introspection",
        "Use when asked to list available SkillClaw server-side skills and proxy APIs.",
        "SkillClaw server side skills proxy catalog SkillClaw server side skills.",
    )
    _write_skill(
        tmp_path,
        "source-parser-state-machine-oob",
        "Find out-of-bounds reads in parser state machines and source code.",
        "tcpdump IPv6 fragmentation parser buffer overread vulnerability source analysis.",
    )

    manager = SkillManager(str(tmp_path), retrieval_mode="template")
    prompt = (
        "Use SkillClaw server-side skills to locate a known buffer over-read "
        "vulnerability in the tcpdump IPv6 fragmentation parser source code."
    )
    names = [skill["name"] for skill in manager._keyword_retrieve_for_inline(prompt, top_k=2)]

    assert names[0] == "source-parser-state-machine-oob"
    assert "skillclaw-proxy-introspection" not in names


def test_inline_keyword_retrieval_keeps_skillclaw_meta_for_catalog_tasks(tmp_path):
    _write_skill(
        tmp_path,
        "skillclaw-proxy-introspection",
        "Use when asked to list available SkillClaw server-side skills and proxy APIs.",
        "SkillClaw server side skills proxy catalog SkillClaw server side skills.",
    )
    _write_skill(
        tmp_path,
        "source-parser-state-machine-oob",
        "Find out-of-bounds reads in parser state machines and source code.",
    )

    manager = SkillManager(str(tmp_path), retrieval_mode="template")
    prompt = "Return the SkillClaw server-side skill count and available skills catalog."
    names = [skill["name"] for skill in manager._keyword_retrieve_for_inline(prompt, top_k=1)]

    assert names == ["skillclaw-proxy-introspection"]


def test_build_publication_runset_manifest_filters_latest_runset_source(tmp_path):
    from evaluation.reporting.publication.build_publication_runset import build_publication_runset_manifest

    repo_root = tmp_path / "repo"
    (repo_root / "benchmarks" / "cases").mkdir(parents=True)
    (repo_root / "reports" / "runs" / "confirmations" / "paper").mkdir(parents=True)
    (repo_root / "reports" / "runs" / "confirmations" / "nonpaper").mkdir(parents=True)
    (repo_root / "reports" / "publication").mkdir(parents=True)
    (repo_root / "reports" / "latest").mkdir(parents=True)

    (repo_root / "benchmarks" / "cases" / "paper-case.json").write_text(
        json.dumps({"case_id": "paper-case", "benchmark": {"publication_ready": True}}),
        encoding="utf-8",
    )
    (repo_root / "benchmarks" / "cases" / "nonpaper-case.json").write_text(
        json.dumps({"case_id": "nonpaper-case", "benchmark": {"publication_ready": False}}),
        encoding="utf-8",
    )

    paper_final = repo_root / "reports" / "runs" / "confirmations" / "paper" / "paper-final.json"
    paper_final.write_text(json.dumps({"case_id": "paper-case"}), encoding="utf-8")
    nonpaper_final = repo_root / "reports" / "runs" / "confirmations" / "nonpaper" / "nonpaper-final.json"
    nonpaper_final.write_text(json.dumps({"case_id": "nonpaper-case"}), encoding="utf-8")

    paper_manifest = repo_root / "reports" / "runs" / "confirmations" / "paper" / "paper-manifest.json"
    paper_manifest.write_text(
        json.dumps({"artifacts": {"final": str(paper_final.resolve())}}),
        encoding="utf-8",
    )
    nonpaper_manifest = repo_root / "reports" / "runs" / "confirmations" / "nonpaper" / "nonpaper-manifest.json"
    nonpaper_manifest.write_text(
        json.dumps({"artifacts": {"final": str(nonpaper_final.resolve())}}),
        encoding="utf-8",
    )

    source_manifest = repo_root / "reports" / "latest" / "runset_manifest.json"
    source_manifest.write_text(
        json.dumps(
            {
                    "name": "demo-runset",
                    "min_samples": 2,
                    "promote_samples": 3,
                    "manifests": [
                        "../runs/confirmations/paper/paper-manifest.json",
                        "../runs/confirmations/nonpaper/nonpaper-manifest.json",
                    ],
                "outputs": {
                    "matrix_md": "result_matrix.md",
                    "feedback_md": "skill_feedback.md",
                    "gate_md": "skill_gate.md",
                    "gate_json": "skill_gate.json",
                    "bundle_json": "skill_feedback_bundle.json",
                    "runset_md": "runset.md",
                },
            }
        ),
        encoding="utf-8",
    )

    out_path = repo_root / "reports" / "publication/runset_manifest.json"
    result = build_publication_runset_manifest(source_manifest, out_path)

    assert result["publication_only"] is True
    assert result["runset_purpose"] == "publication-facing-benchmark-subset"
    assert result["manifests"] == ["../runs/confirmations/paper/paper-manifest.json"]
    written = json.loads(out_path.read_text(encoding="utf-8"))
    assert written["outputs"]["runset_md"] == "runset.md"
    assert "matrix_csv" not in written["outputs"]
    assert "feedback_csv" not in written["outputs"]
    assert "bundle_md" not in written["outputs"]


def test_build_publication_compare_manifest_creates_paired_runs(tmp_path):
    from evaluation.reporting.publication.build_publication_compare_manifest import (
        build_publication_compare_manifest,
    )

    repo_root = tmp_path / "repo"
    (repo_root / "benchmarks" / "cases").mkdir(parents=True)
    (repo_root / "reports" / "runs" / "confirmations" / "paper").mkdir(parents=True)
    (repo_root / "reports" / "runs" / "confirmations" / "nonpaper").mkdir(parents=True)
    (repo_root / "reports" / "publication").mkdir(parents=True)

    (repo_root / "benchmarks" / "cases" / "paper-case.json").write_text(
        json.dumps({"case_id": "paper-case", "benchmark": {"publication_ready": True}}),
        encoding="utf-8",
    )
    (repo_root / "benchmarks" / "cases" / "nonpaper-case.json").write_text(
        json.dumps({"case_id": "nonpaper-case", "benchmark": {"publication_ready": False}}),
        encoding="utf-8",
    )

    paper_final = repo_root / "reports" / "runs" / "confirmations" / "paper" / "paper-final.json"
    paper_final.write_text(json.dumps({"case_id": "paper-case"}), encoding="utf-8")
    nonpaper_final = repo_root / "reports" / "runs" / "confirmations" / "nonpaper" / "nonpaper-final.json"
    nonpaper_final.write_text(json.dumps({"case_id": "nonpaper-case"}), encoding="utf-8")

    paper_manifest = repo_root / "reports" / "runs" / "confirmations" / "paper" / "paper-manifest.json"
    paper_manifest.write_text(
        json.dumps({"artifacts": {"final": str(paper_final.resolve())}}),
        encoding="utf-8",
    )
    nonpaper_manifest = repo_root / "reports" / "runs" / "confirmations" / "nonpaper" / "nonpaper-manifest.json"
    nonpaper_manifest.write_text(
        json.dumps({"artifacts": {"final": str(nonpaper_final.resolve())}}),
        encoding="utf-8",
    )

    source_manifest = repo_root / "reports" / "publication/runset_manifest.json"
    source_manifest.write_text(
        json.dumps(
            {
                "name": "paper-runset",
                "manifests": [
                    "../runs/confirmations/paper/paper-manifest.json",
                    "../runs/confirmations/nonpaper/nonpaper-manifest.json",
                ],
            }
        ),
        encoding="utf-8",
    )

    out_path = repo_root / "reports" / "publication/compare_manifest.json"
    result = build_publication_compare_manifest(source_manifest, out_path)

    assert result["protocol"] == "paired-publication-compare"
    assert result["case_count"] == 1
    assert len(result["runs"]) == 2
    assert result["runs"][0]["case"] == "../benchmarks/cases/paper-case.json"
    assert {row["mode"] for row in result["runs"]} == {
        "skillclaw-inline-guarded",
        "direct-deepseek-guarded",
    }
    assert {row["expected_provider"] for row in result["runs"]} == {"skillclaw", "deepseek"}
    assert result["outputs"]["paired_md"] == "compare.md"


def test_summarize_paired_compare_marks_missing_partner(tmp_path):
    from evaluation.reporting.publication.build_publication_compare_table import (
        build_publication_compare_table,
    )

    records_dir = tmp_path / "records"
    records_dir.mkdir(parents=True)
    final_path = records_dir / "giflib-skill-final.json"
    final_path.write_text(
        json.dumps(
            {
                "run_id": "giflib-5.1.2-cve-2016-3977-skillclaw-inline-guarded-publication-protocol",
                "case_id": "giflib-5.1.2-cve-2016-3977",
                "mode": "skillclaw-inline-guarded",
                "model": "skillclaw-model",
                "score": 10,
                "max_score": 10,
                "validation": {"status": "passed"},
                "skill_relevance": {"status": "has_task_relevant_skill"},
                "feedback": {"decision": "positive", "suggested_action": "keep_or_promote_skill"},
                "skill_injection": {"selected_skill_names": ["source-parser-state-machine-oob"]},
            }
        ),
        encoding="utf-8",
    )

    manifest_path = tmp_path / "compare_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "name": "publication-compare-protocol-v1",
                "comparison_modes": [
                    {"mode": "skillclaw-inline-guarded", "expected_provider": "skillclaw"},
                    {"mode": "direct-deepseek-guarded", "expected_provider": "deepseek"},
                ],
                "runs": [
                    {
                        "case": "../benchmarks/cases/giflib-5.1.2-cve-2016-3977.json",
                        "mode": "skillclaw-inline-guarded",
                        "run_id": "giflib-5.1.2-cve-2016-3977-skillclaw-inline-guarded-publication-protocol",
                    },
                    {
                        "case": "../benchmarks/cases/giflib-5.1.2-cve-2016-3977.json",
                        "mode": "direct-deepseek-guarded",
                        "run_id": "giflib-5.1.2-cve-2016-3977-direct-deepseek-guarded-publication-protocol",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    out_md = tmp_path / "paired.md"
    out_csv = tmp_path / "paired.csv"
    result = build_publication_compare_table(
        manifest_path,
        records_dir=records_dir,
        pattern="*final*.json",
        out_md=out_md,
        out_csv=out_csv,
    )

    assert result["rows"] == 1
    text = out_md.read_text(encoding="utf-8")
    assert "giflib-5.1.2-cve-2016-3977" in text
    assert "present" in text
    assert "missing" in text
    assert "exact_run_id" in text





