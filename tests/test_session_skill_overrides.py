from __future__ import annotations

from unittest.mock import patch
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
            {
                "name": "skillclaw-proxy-introspection",
                "description": "proxy skill",
                "content": "# Proxy skill",
                "category": "general",
            },
            {
                "name": "vuln-hunting",
                "description": "vulnerability hunting skill",
                "content": "# Hunting skill",
                "category": "general",
            },
        ]

    def refresh_if_changed(self) -> None:
        return None

    def get_all_skills(self) -> list[dict]:
        return list(self._skills)

    def format_inline_skills_for_prompt(
        self,
        skills: list[dict],
        max_chars: int = 30_000,
        include_catalog: bool = True,
    ) -> str:
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


def test_server_catalog_selects_only_known_names_and_caps_at_three(tmp_path):
    server, _skill_manager = _build_server(tmp_path)
    server.config.skill_injection_mode = "server-catalog"

    with patch(
        "skillclaw.api_server.run_llm",
        return_value='{"selected_skill_names":["elf-cwe120-plt-analysis","missing","source-parser-state-machine-oob","extra"]}',
    ) as run_llm:
        selected = __import__("asyncio").run(server._select_server_catalog("inspect the parser binary"))

    assert selected == ["elf-cwe120-plt-analysis", "source-parser-state-machine-oob"]
    assert run_llm.call_args.kwargs["compress"] is False


def test_server_catalog_family_guard_falls_back_from_cgi_to_cwe120(tmp_path):
    server, skill_manager = _build_server(tmp_path)
    skill_manager._skills.extend(
        [
            {
                "name": "embedded-cgi-command-injection-triage",
                "description": "Use for embedded CGI. NOT for: buffer-overflow analysis.",
                "content": "# CGI",
                "category": "general",
            },
            {
                "name": "elf-cwe120-firmware-triage",
                "description": "Use for firmware CWE-120 buffer-overflow analysis.",
                "content": "# CWE-120",
                "category": "general",
            },
        ]
    )

    with patch(
        "skillclaw.api_server.run_llm",
        return_value='{"selected_skill_names":["embedded-cgi-command-injection-triage"]}',
    ):
        selected, trace = __import__("asyncio").run(
            server._select_server_catalog("analyze a stack-based buffer overflow in strcpy", return_trace=True)
        )

    assert selected[0] == "elf-cwe120-firmware-triage"
    assert "embedded-cgi-command-injection-triage" not in selected
    assert trace["excluded_selected_skill_names"] == ["embedded-cgi-command-injection-triage"]
    assert trace["fallback_applied"] is True


def test_server_catalog_rejects_non_list_selection(tmp_path):
    server, _skill_manager = _build_server(tmp_path)

    with patch("skillclaw.api_server.run_llm", return_value='{"selected_skill_names":"not-a-list"}'):
        selected = __import__("asyncio").run(server._select_server_catalog("inspect the parser binary"))

    assert selected == []


def test_server_catalog_injects_selected_bodies_without_full_catalog(tmp_path):
    server, skill_manager = _build_server(tmp_path)
    server.config.skill_injection_mode = "server-catalog"

    messages, skill_names, meta = server._inject_skills(
        [{"role": "user", "content": "inspect the parser binary"}],
        session_id="sid-catalog",
        selected_skill_names=["source-parser-state-machine-oob"],
    )

    assert skill_names == ["source-parser-state-machine-oob"]
    assert "source-parser-state-machine-oob" in messages[0]["content"]
    assert meta["selection_source"] == "server-llm"
    assert meta["selected_skill_names"] == skill_names
    assert skill_manager.recorded[-1] == skill_names


def test_server_catalog_does_not_reuse_inline_session_cache(tmp_path):
    server, skill_manager = _build_server(tmp_path)
    server.config.skill_injection_mode = "server-catalog"
    server._session_inline_skill_cache["sid-catalog-cache"] = {
        "generation": skill_manager.generation,
        "selected_skill_names": ["source-parser-state-machine-oob"],
    }

    messages, skill_names, meta = server._inject_skills(
        [{"role": "user", "content": "inspect the parser binary"}],
        session_id="sid-catalog-cache",
        selected_skill_names=["elf-cwe120-plt-analysis"],
        server_catalog_trace={"status": "ok", "catalog_count": 4},
    )

    assert skill_names == ["elf-cwe120-plt-analysis"]
    assert "elf-cwe120-plt-analysis" in messages[0]["content"]
    assert meta["stable_action"] == "server-select"
    assert meta["stable_session"] is False


def test_server_catalog_trace_records_filtering_and_truncation(tmp_path):
    server, _skill_manager = _build_server(tmp_path)

    with patch(
        "skillclaw.api_server.run_llm",
        return_value=(
            '{"selected_skill_names":['
            '"elf-cwe120-plt-analysis",'
            '"missing",'
            '"source-parser-state-machine-oob",'
            '"skillclaw-proxy-introspection",'
            '"vuln-hunting"'
            ']}'
        ),
    ):
        selected, trace = __import__("asyncio").run(
            server._select_server_catalog("inspect the parser binary", return_trace=True)
        )

    assert selected == [
        "elf-cwe120-plt-analysis",
        "source-parser-state-machine-oob",
        "skillclaw-proxy-introspection",
    ]
    assert trace["status"] == "ok"
    assert trace["unknown_selected_skill_names"] == ["missing"]
    assert trace["truncated"] is True


def test_server_catalog_trace_records_invalid_response(tmp_path):
    server, _skill_manager = _build_server(tmp_path)

    with patch("skillclaw.api_server.run_llm", return_value='{"selected_skill_names":"bad"}'):
        selected, trace = __import__("asyncio").run(
            server._select_server_catalog("inspect the parser binary", return_trace=True)
        )

    assert selected == []
    assert trace["status"] == "invalid_selection_type"
