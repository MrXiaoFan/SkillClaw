from skillclaw.api_server import SkillClawAPIServer
from skillclaw.config import SkillClawConfig


class FakeInlineSkillManager:
    generation = 0

    def __init__(self):
        self.calls = []
        self.injected = []
        self.skills = [
            {
                "name": "source-parser-state-machine-oob",
                "description": "Find out-of-bounds reads in parser state machines.",
                "content": "parser state machine OOB workflow",
            },
            {
                "name": "vuln-hunting",
                "description": "General vulnerability hunting workflow.",
                "content": "vulnerability hunting workflow",
            },
            {
                "name": "ssh-password-recon-workflow",
                "description": "SSH password reconnaissance workflow.",
                "content": "ssh reconnaissance workflow",
            },
            {
                "name": "skillclaw-skill-discovery",
                "description": "Explain SkillClaw server-side skill catalog.",
                "content": "SkillClaw catalog introspection",
            },
        ]

    def refresh_if_changed(self):
        return False

    def get_all_skills(self):
        return list(self.skills)

    def format_inline_skills_for_prompt(self, skills, max_chars=30000):
        names = ",".join(str(skill.get("name", "")) for skill in skills)
        return f"<available_server_skills>{names}</available_server_skills>"[:max_chars]

    def build_inline_injection_prompt(self, task_description, *, max_chars, top_k):
        self.calls.append(task_description)
        text = task_description.lower()
        if "count" in text or "catalog" in text:
            names = ["skillclaw-skill-discovery"]
        elif "ssh" in text:
            names = ["ssh-password-recon-workflow", "skillclaw-skill-discovery"]
        else:
            names = ["source-parser-state-machine-oob", "vuln-hunting"]
        selected = [skill for skill in self.skills if skill["name"] in names][:top_k]
        return self.format_inline_skills_for_prompt(selected, max_chars=max_chars), [
            skill["name"] for skill in selected
        ]

    def record_injection(self, names):
        self.injected.append(list(names))


def _inline_server(tmp_path, manager):
    return SkillClawAPIServer(
        SkillClawConfig(
            skill_injection_mode="inline",
            skill_top_k=3,
            record_enabled=False,
            record_dir=str(tmp_path),
            claw_type="nanoclaw",
        ),
        skill_manager=manager,
    )


def test_inline_skill_selection_is_pinned_within_session(tmp_path):
    manager = FakeInlineSkillManager()
    server = _inline_server(tmp_path, manager)

    _, first_names, first_meta = server._inject_skills(
        [{"role": "user", "content": "Analyze tcpdump parser state machine OOB vulnerability."}],
        session_id="session-a",
    )
    _, second_names, second_meta = server._inject_skills(
        [{"role": "user", "content": "Tool result now mentions ssh and unrelated recon text."}],
        session_id="session-a",
    )

    assert first_names == ["source-parser-state-machine-oob", "vuln-hunting"]
    assert second_names == first_names
    assert first_meta["stable_action"] == "pin"
    assert second_meta["stable_action"] == "reuse"
    assert len(manager.calls) == 1


def test_inline_skill_meta_tasks_do_not_pin_session(tmp_path):
    manager = FakeInlineSkillManager()
    server = _inline_server(tmp_path, manager)

    _, first_names, first_meta = server._inject_skills(
        [{"role": "user", "content": "Return the SkillClaw skill catalog count."}],
        session_id="session-b",
    )
    _, second_names, second_meta = server._inject_skills(
        [{"role": "user", "content": "Analyze tcpdump parser state machine OOB vulnerability."}],
        session_id="session-b",
    )

    assert first_names == ["skillclaw-skill-discovery"]
    assert second_names == ["source-parser-state-machine-oob", "vuln-hunting"]
    assert first_meta["stable_action"] == "none"
    assert second_meta["stable_action"] == "pin"
    assert len(manager.calls) == 2
