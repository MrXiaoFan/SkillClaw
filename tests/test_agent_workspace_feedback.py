import json

from evolve_server.core.config import EvolveServerConfig
from evolve_server.engines.agent_workspace import AgentWorkspace


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
                "cve_calibration_miss": 1,
                "validator_passed": 2,
                "artifact_generated": 1,
                "artifact_execution_passed": 1,
            },
            "revision_directives": ["separate localization from CVE identity"],
            "revision_templates": [
                {
                    "template_id": "cve_calibration_miss",
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

    feedback_json = workspace.root / "feedback" / "skill_feedback_bundle_latest.json"
    feedback_summary = workspace.root / "feedback" / "SUMMARY.md"
    feedback_playbook = workspace.root / "feedback" / "PLAYBOOK.md"
    evolve_agents = workspace.root / "EVOLVE_AGENTS.md"

    assert feedback_json.is_file()
    assert feedback_summary.is_file()
    assert feedback_playbook.is_file()
    assert json.loads(feedback_json.read_text(encoding="utf-8"))[0]["skill"] == "source-parser-state-machine-oob"
    assert "cve_calibration_miss" in feedback_summary.read_text(encoding="utf-8")
    assert "Artifact Exec" in feedback_summary.read_text(encoding="utf-8")
    playbook_text = feedback_playbook.read_text(encoding="utf-8")
    assert "## revise" in playbook_text
    assert "separate localization from CVE identity" in playbook_text
    assert "cve_calibration_miss" in playbook_text
    assert "feedback/skill_feedback_bundle_latest.json" in evolve_agents.read_text(encoding="utf-8")
    assert "feedback/PLAYBOOK.md" in evolve_agents.read_text(encoding="utf-8")


def test_agent_config_defaults_feedback_bundle_path_for_agent_engine():
    config = EvolveServerConfig(engine="agent")

    assert config.feedback_bundle_path.endswith("experiment_records\\skill_feedback_bundle_latest.json") or (
        config.feedback_bundle_path.endswith("experiment_records/skill_feedback_bundle_latest.json")
    )
