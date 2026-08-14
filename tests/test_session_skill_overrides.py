from __future__ import annotations

from pathlib import Path

from skillclaw.api_server import SkillClawAPIServer
from skillclaw.config import SkillClawConfig


class _FakeSkillManager:
    def __init__(self) -> None:
        self.generation = 7
        self.recorded: list[list[str]] = []
        self._skills = [
            {
                "name": "source-parser-state-machine-oob",
                "description": "parser skill",
                "content": "# Parser skill",
                "category": "general",
            },
            {
                "name": "elf-cwe120-plt-analysis",
                "description": "elf skill",
                "content": "# ELF skill",
                "category": "general",
            },
        ]

    def refresh_if_changed(self) -> None:
        return None

    def get_all_skills(self) -> list[dict]:
        return list(self._skills)

    def format_inline_skills_for_prompt(self, skills: list[dict], max_chars: int = 30_000) -> str:
        return " | ".join(str(skill.get("name") or "") for skill in skills)[:max_chars]

    def build_inline_injection_prompt(self, task_description: str, max_chars: int = 30_000, top_k: int = 3):
        selected = self._skills[: max(1, top_k)]
        return self.format_inline_skills_for_prompt(selected, max_chars=max_chars), [
            str(skill.get("name") or "") for skill in selected
        ]

    def record_injection(self, skill_names: list[str]) -> None:
        self.recorded.append(list(skill_names))


def _build_server(tmp_path: Path) -> tuple[SkillClawAPIServer, _FakeSkillManager]:
    skill_manager = _FakeSkillManager()
    cfg = SkillClawConfig(
        record_enabled=False,
        record_dir=str(tmp_path / "records"),
        skill_injection_mode="inline",
    )
    server = SkillClawAPIServer(cfg, skill_manager=skill_manager)
    return server, skill_manager


def test_session_override_disable_skips_injection(tmp_path):
    server, skill_manager = _build_server(tmp_path)
    server._set_session_skill_override("sid-disable", {"disable_skills": True, "note": "ablation"})

    messages, skill_names, meta = server._inject_skills(
        [{"role": "user", "content": "analyze parser bug"}],
        session_id="sid-disable",
    )

    assert messages == [{"role": "user", "content": "analyze parser bug"}]
    assert skill_names == []
    assert meta["override_mode"] == "disable"
    assert meta["enabled"] is False
    assert skill_manager.recorded == []


def test_session_override_force_names_uses_requested_live_skills(tmp_path):
    server, skill_manager = _build_server(tmp_path)
    server._set_session_skill_override(
        "sid-force",
        {
            "forced_skill_names": [
                "source-parser-state-machine-oob",
                "missing-skill",
            ],
            "note": "force-one",
        },
    )

    messages, skill_names, meta = server._inject_skills(
        [{"role": "user", "content": "analyze parser bug"}],
        session_id="sid-force",
    )

    assert messages[0]["role"] == "system"
    assert "source-parser-state-machine-oob" in str(messages[0]["content"] or "")
    assert skill_names == ["source-parser-state-machine-oob"]
    assert meta["override_mode"] == "force_names"
    assert meta["override_requested_skill_names"] == [
        "source-parser-state-machine-oob",
        "missing-skill",
    ]
    assert meta["override_unmatched_skill_names"] == ["missing-skill"]
    assert skill_manager.recorded[-1] == ["source-parser-state-machine-oob"]


def test_session_override_inline_skills_supports_candidate_payload(tmp_path):
    server, skill_manager = _build_server(tmp_path)
    server._set_session_skill_override(
        "sid-inline",
        {
            "inline_skills": [
                {
                    "name": "candidate-skill",
                    "description": "candidate desc",
                    "content": "# Candidate body",
                    "category": "general",
                }
            ],
            "note": "candidate-check",
        },
    )

    messages, skill_names, meta = server._inject_skills(
        [{"role": "user", "content": "analyze parser bug"}],
        session_id="sid-inline",
    )

    assert messages[0]["role"] == "system"
    assert "candidate-skill" in str(messages[0]["content"] or "")
    assert skill_names == ["candidate-skill"]
    assert meta["override_mode"] == "inline_skills"
    assert meta["selected_skill_names"] == ["candidate-skill"]
    assert skill_manager.recorded[-1] == ["candidate-skill"]
