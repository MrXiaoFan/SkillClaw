import json

from evolve_server.__main__ import _build_config_from_args, build_parser
from evolve_server.core.config import EvolveServerConfig
from evolve_server.engines.agent_workspace import AgentWorkspace
from evolve_server.pipeline.execution import _build_feedback_context


def test_agent_workspace_writes_feedback_bundle_and_summary(tmp_path):
    workspace = AgentWorkspace(tmp_path / "workspace")
    feedback_bundle = [
        {
            "skill": "source-parser-state-machine-oob",
            "gate_decision": "revise",
            "summary": {"selected_runs": 4, "mean_score": 0.8},
            "dimensions": {
                "localization_success": 4,
                "cve_success": 0,
                "cve_identity_miss": 1,
                "validator_passed": 2,
                "artifact_generated": 1,
                "artifact_execution_passed": 1,
            },
            "revision_directives": ["separate localization from CVE identity"],
            "revision_templates": [
                {
                    "template_id": "cve_identity_miss",
                    "title": "Separate bug localization from exact CVE attribution",
                }
            ],
        }
    ]

    workspace.prepare(
        sessions=[],
        existing_skills={},
        manifest={},
        agents_md="# Guide\n",
        feedback_bundle=feedback_bundle,
    )

    feedback_json = workspace.root / "evolution" / "skill_feedback_bundle.json"
    feedback_summary = workspace.root / "evolution" / "SUMMARY.md"
    feedback_playbook = workspace.root / "evolution" / "PLAYBOOK.md"
    evolve_agents = workspace.root / "EVOLVE_AGENTS.md"

    assert feedback_json.is_file()
    assert feedback_summary.is_file()
    assert feedback_playbook.is_file()
    assert json.loads(feedback_json.read_text(encoding="utf-8"))[0]["skill"] == "source-parser-state-machine-oob"
    assert "cve_identity_miss" in feedback_summary.read_text(encoding="utf-8")
    assert "Artifact Exec" in feedback_summary.read_text(encoding="utf-8")
    playbook_text = feedback_playbook.read_text(encoding="utf-8")
    assert "## revise" in playbook_text
    assert "separate localization from CVE identity" in playbook_text
    assert "cve_identity_miss" in playbook_text
    assert "evolution/skill_feedback_bundle.json" in evolve_agents.read_text(encoding="utf-8")
    assert "evolution/PLAYBOOK.md" in evolve_agents.read_text(encoding="utf-8")


def test_agent_config_defaults_feedback_bundle_path_for_agent_engine():
    config = EvolveServerConfig(engine="agent")

    normalized = config.feedback_bundle_path.replace("\\", "/")
    assert normalized.endswith("reports/current/skill_feedback_bundle.json")


def test_config_defaults_feedback_bundle_path_for_workflow_engine():
    config = EvolveServerConfig(engine="workflow")

    normalized = config.feedback_bundle_path.replace("\\", "/")
    assert normalized.endswith("reports/current/skill_feedback_bundle.json")


def test_evolve_cli_accepts_runtime_feedback_bundle():
    args = build_parser().parse_args(
        [
            "--engine",
            "workflow",
            "--publish-mode",
            "validated",
            "--feedback-bundle",
            "runtime/evolve/skill_feedback_bundle.json",
        ]
    )

    config = _build_config_from_args(args)

    assert config.publish_mode == "validated"
    assert config.feedback_bundle_path == "runtime/evolve/skill_feedback_bundle.json"


def test_feedback_context_formats_gate_and_directives():
    text = _build_feedback_context(
        {
            "skill": "source-parser-state-machine-oob",
            "gate_decision": "revise",
            "gate_reasons": ["validator passed but exact CVE attribution is unstable"],
            "revision_directives": ["separate localization from exact CVE identity"],
            "summary": {
                "selected_runs": 2,
                "mean_score": 0.9,
                "relevant_selected": 1,
                "mismatched_selected": 1,
            },
            "dimensions": {
                "localization_success": 2,
                "cve_success": 1,
                "cve_identity_miss": 1,
                "validator_passed": 2,
                "validator_failed": 0,
            },
        }
    )

    assert "Validator-backed feedback for this skill" in text
    assert "Gate decision: revise" in text
    assert "separate localization from exact CVE identity" in text
    assert "cve_identity_miss=1" in text

