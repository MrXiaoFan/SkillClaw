import json
import sys
from argparse import Namespace
from pathlib import Path

from experiment_scripts.check_experiment_env import check_case_environment, infer_claude_provider
from experiment_scripts.attach_skill_injection import attach_injection
from experiment_scripts.run_eval_case import extract_json_object, run_case
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
                "validation": {"status": "passed"},
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


def test_smoke_validate_framework_runs_repository_cases():
    results = smoke_cases(Path("experiment_cases"))

    statuses = {item["case_id"]: item["status"] for item in results}
    assert statuses["giflib-5.1.2-cve-2016-3977"] == "passed"
    assert statuses["libxml2-2.9.4-cve-2017-8872"] == "passed"
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
