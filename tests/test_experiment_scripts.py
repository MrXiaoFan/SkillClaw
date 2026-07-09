import json
import shutil
import subprocess
import sys
from argparse import Namespace
from datetime import datetime, timedelta
from pathlib import Path

from experiment_scripts.check_experiment_env import check_case_environment, infer_claude_provider
from experiment_scripts.compare_experiment_records import compare_records, render_markdown
from experiment_scripts.attach_skill_injection import attach_injection
from experiment_scripts.run_eval_case import extract_json_object, infer_session_id_from_injection, run_case
from experiment_scripts.run_dynamic_case import run_validators
from experiment_scripts.smoke_validate_framework import smoke_cases
from experiment_scripts.score_agent_output import score_output
from experiment_scripts.build_result_record import _select_injection, _select_injection_history, _select_validation
from experiment_scripts.build_skill_gate_report import build_gate_report, decide_gate
from experiment_scripts.build_skill_feedback_bundle import (
    build_feedback_bundles,
    write_json as write_bundle_json,
    write_markdown as write_bundle_markdown,
)
from experiment_scripts.print_case_prompt import FINAL_ANSWER_GUARD, get_case_prompt
from experiment_scripts.print_case_runbook import render_runbook
from experiment_scripts.refresh_curated_reports import refresh_reports
from experiment_scripts.run_case_batch import run_batch
from experiment_scripts.skill_bundle_runner import resolve_bundle_script, run_bundle_script
from experiment_scripts.summarize_research_claims import build_claims, write_markdown as write_claim_markdown
from experiment_scripts.summarize_results import collect_rows, write_csv, write_markdown
from experiment_scripts.summarize_skill_feedback import build_skill_feedback
from experiment_validation.core import assess_skill_relevance, build_feedback
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


def test_score_agent_output_hits_ground_truth():
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


def test_score_agent_output_extracts_claude_json_result_field():
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


def test_score_agent_output_ignores_unscoreable_claude_error_wrapper():
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


def test_run_dynamic_case_source_contains(tmp_path):
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


def test_run_dynamic_case_artifact_exists(tmp_path):
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
                "artifact_type": "file",
                "min_size_bytes": 16,
            }
        ],
    }

    result = run_validators(case, tmp_path, skip_commands=True)

    assert result["status"] == "passed"
    assert result["checks"][0]["status"] == "passed"
    assert result["checks"][0]["size_bytes"] == 32


def test_run_dynamic_case_artifact_exec(tmp_path):
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


def test_run_dynamic_case_artifact_exec_expect_crash(tmp_path):
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


def test_run_dynamic_case_command_validator(tmp_path):
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
        / "experiment_cases"
        / "pocs"
        / "tcpdump-4.9.1-cve-2017-13031"
        / "make_poc.py"
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
        / "experiment_cases"
        / "pocs"
        / "tcpdump-4.9.1-cve-2018-14469"
        / "make_poc.py"
    )
    output = tmp_path / "isakmp.pcap"

    subprocess.run([sys.executable, str(script), str(output)], check=True)

    blob = output.read_bytes()
    assert len(blob) >= 80
    assert blob[:4] == bytes.fromhex("d4c3b2a1")
    assert bytes.fromhex("0800") in blob
    assert bytes.fromhex("01f401f4") in blob


def test_build_result_record_selects_session_injection():
    rows = [
        {"session_id": "a", "selected_skill_names": ["old"]},
        {"session_id": "b", "selected_skill_names": ["new"]},
    ]

    result = _select_injection(rows, "b")

    assert result == rows[1]


def test_build_result_record_selects_session_injection_history():
    rows = [
        {"session_id": "a", "selected_skill_names": ["old"]},
        {"session_id": "b", "selected_skill_names": ["first"]},
        {"session_id": "b", "selected_skill_names": ["latest"]},
    ]

    result = _select_injection_history(rows, "b")

    assert result == rows[1:]


def test_build_result_record_selects_latest_case_validation():
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
    assert any("CVE calibration" in reason for reason in decision["reasons"])


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
    assert "infrastructure" in decision["reasons"][0]


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
    assert "mismatched" in decision["reasons"][0]


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
            "suggested_action": "revise_cve_calibration_before_promotion",
            "quality_flags": ["cve_calibration_miss"],
        },
    }
    gate = {
        "source-parser-state-machine-oob": {
            "gate_decision": "revise",
            "suggestions": ["add advisory evidence requirement"],
            "reasons": ["localization evidence exists but exact CVE calibration is absent"],
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
    assert bundle["dimensions"]["cve_calibration_miss"] == 1
    assert bundle["dimensions"]["dynamic_or_bundle_validation_passed"] == 1
    assert bundle["dimensions"]["artifact_generated"] == 1
    assert bundle["dimensions"]["artifact_execution_passed"] == 1
    assert any("CVE identity" in item for item in bundle["revision_directives"])
    assert bundle["revision_templates"][0]["template_id"] == "cve_calibration_miss"
    assert "uncertain" in bundle["revision_templates"][0]["required_changes"][2].lower()

    json_path = tmp_path / "bundle.json"
    md_path = tmp_path / "bundle.md"
    write_bundle_json(bundles, json_path)
    write_bundle_markdown(bundles, md_path)
    assert "source-parser-state-machine-oob" in json_path.read_text(encoding="utf-8")
    assert "cve_miss" in md_path.read_text(encoding="utf-8")
    assert "cve_calibration_miss" in md_path.read_text(encoding="utf-8")


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
            "suggested_action": "revise_cve_calibration_before_promotion",
            "quality_flags": ["cve_calibration_miss"],
        },
    }
    gate = {
        "source-parser-state-machine-oob": {
            "gate_decision": "revise",
            "suggestions": ["add advisory evidence requirement"],
            "reasons": ["localization evidence exists but exact CVE calibration is absent"],
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


def test_print_case_prompt_selects_mode():
    case = {
        "case_id": "demo",
        "prompt": {
            "recommended_skillclaw": "use skillclaw",
            "recommended_direct": "direct baseline",
        },
    }

    assert get_case_prompt(case, "skillclaw-inline") == "use skillclaw"
    assert get_case_prompt(case, "direct-deepseek") == "direct baseline"


def test_compare_experiment_records_reports_key_deltas():
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
        "feedback": {"decision": "neutral", "quality_flags": ["cve_calibration_miss"]},
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
    assert result["delta"]["quality_flags_removed"] == ["cve_calibration_miss"]
    assert result["delta"]["selected_skills_added"] == ["vuln-hunting"]

    markdown = render_markdown(result)
    assert "Experiment Compare: libxml2-demo" in markdown
    assert "artifact exec change" in markdown


def test_print_case_prompt_guarded_mode_appends_execution_constraints():
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


def test_print_case_prompt_appends_confirmation_contract():
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


def test_print_case_runbook_includes_artifacts_repro_and_commands(tmp_path):
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

    text = render_runbook(
        case,
        case_path=case_path,
        root_override=None,
        output_dir="~/skillclaw-eval/runs/demo",
    )

    assert "# Runbook: gif-demo" in text
    assert "artifacts/poc.gif" in text
    assert "AddressSanitizer" in text
    assert "skillclaw-inline-guarded" in text
    assert "direct-deepseek-guarded" in text
    assert "run_eval_case.py" in text


def test_repository_case_prompts_are_not_mojibake():
    suspicious_fragments = ["涓", "銆", "乸", "乺", "锛", "鏄"]
    for case_path in Path("experiment_cases").glob("*.json"):
        if case_path.name == "schema.json":
            continue
        case = json.loads(case_path.read_text(encoding="utf-8-sig"))
        prompts = case.get("prompt", {})
        for key, prompt in prompts.items():
            assert not any(fragment in str(prompt) for fragment in suspicious_fragments), (
                case_path,
                key,
            )


def test_check_experiment_env_passes_with_root_override(tmp_path):
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


def test_check_experiment_env_reports_missing_ground_truth_file(tmp_path):
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


def test_check_experiment_env_infers_claude_provider(tmp_path):
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


def test_skill_bundle_runner_executes_script(tmp_path):
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


def test_run_dynamic_case_bundle_script_validator(tmp_path):
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
    assert feedback["suggested_action"] == "revise_cve_calibration_before_promotion"
    assert "cve_calibration_miss" in feedback["quality_flags"]


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


def test_run_eval_case_extracts_fenced_json():
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


def test_run_eval_case_with_existing_agent_output(tmp_path):
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
            final_records=str(tmp_path / "results" / "final_records.jsonl"),
        )
    )

    assert final["score"] == 10
    assert final["validation"]["status"] == "passed"
    assert (tmp_path / "results" / "demo-run-final.json").is_file()


def test_run_eval_case_can_preflight_before_existing_output(tmp_path):
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
            final_records=str(tmp_path / "results" / "final_records.jsonl"),
        )
    )

    assert final["preflight"]["status"] == "passed"
    assert final["preflight"]["claude"]["provider"] == "deepseek"
    assert (tmp_path / "results" / "demo-preflight-preflight.json").is_file()


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
        Path("experiment_cases")
        / "pocs"
        / "exiv2-0.26-cve-2017-17725"
        / "prepare_artifacts.sh"
    ).resolve()
    make_poc_script = (
        Path("experiment_cases")
        / "pocs"
        / "exiv2-0.26-cve-2017-17725"
        / "make_poc.py"
    ).resolve()

    poc_path = root / "artifacts" / "poc-cve-2017-17725.tiff"
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
    else:
        subprocess.run(
            [sys.executable, str(make_poc_script), str(poc_path)],
            cwd=root,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert poc_path.is_file()
        assert poc_path.stat().st_size >= 32
        wrapper_text = prepare_script.read_text(encoding="utf-8")
        assert "--smoke-only" in wrapper_text
        assert "WRAPPER_SMOKE_OK" in wrapper_text
        assert "--probe-only" in wrapper_text
        assert "WRAPPER_PROBE_OK" in wrapper_text
        assert "TARGET_EXECUTION_RC=" in wrapper_text


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
            final_records=str(tmp_path / "results" / "final_records.jsonl"),
        )
    )

    assert final["session_id"] == "target"
    assert final["session_id_source"] == "inferred_from_injection_log"
    assert final["skill_injection"]["selected_skill_names"] == ["source-parser-state-machine-oob"]


def test_smoke_validate_framework_runs_repository_cases():
    results = smoke_cases(Path("experiment_cases"))

    statuses = {item["case_id"]: item["status"] for item in results}
    assert statuses["giflib-5.1.2-cve-2016-3977"] == "passed"
    assert statuses["libxml2-2.9.4-cve-2017-8872"] == "passed"
    assert statuses["libarchive-3.8.0-cve-2025-60753"] == "passed"
    assert statuses["tcpdump-4.9.1-cve-2017-13031"] == "passed"


def test_summarize_results_writes_matrix(tmp_path):
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
    md_path = tmp_path / "matrix.md"
    csv_path = tmp_path / "matrix.csv"
    write_markdown(rows, md_path)
    write_csv(rows, csv_path)

    assert rows[0]["score_text"] == "8/10"
    assert rows[0]["file_hit"] == "Y"
    assert rows[0]["cve_hit"] == "N"
    assert "only_infra_skills" in md_path.read_text(encoding="utf-8")
    assert "inspect_retrieval_before_promoting_skill" in csv_path.read_text(encoding="utf-8")


def test_refresh_curated_reports_rebuilds_outputs_in_order(tmp_path):
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
                "feedback": {
                    "decision": "neutral",
                    "suggested_action": "keep_skill_but_prune_extraneous_selection",
                },
            }
        ),
        encoding="utf-8",
    )
    manifest = tmp_path / "curated.json"
    manifest.write_text(
        json.dumps(
            {
                "name": "test-runset",
                "min_samples": 1,
                "promote_samples": 2,
                "records": [record_a.name, record_b.name],
                "outputs": {
                    "matrix_md": "matrix.md",
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
    by_skill = {row["skill"]: row for row in gate}
    assert by_skill["source-parser-state-machine-oob"]["gate_decision"] == "keep"
    assert by_skill["vuln-hunting"]["gate_decision"] == "demote"


def test_summarize_results_falls_back_for_legacy_skill_relevance(tmp_path):
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
    assert "SkillClaw produced a stronger low-budget result" in text
    assert "direct LLM outperformed SkillClaw under the high-budget setting" in text
    assert "CVE-calibration failure" in text


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
