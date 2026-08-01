from __future__ import annotations

import pytest

from skillclaw.config import SkillClawConfig
from skillclaw.launcher import SkillClawLauncher


class _FakeConfigStore:
    def __init__(self, cfg: SkillClawConfig):
        self._cfg = cfg

    def to_skillclaw_config(self) -> SkillClawConfig:
        return self._cfg


class _FakeSkillManager:
    def __init__(self, *args, **kwargs):
        self._count = {"total": 1, "by_category": {"general": 1}}

    def get_skill_count(self):
        return self._count


class _FakeServer:
    def __init__(self, *args, **kwargs):
        self._stopped = False

    def start(self):
        return None

    def wait_until_ready(self, timeout_s: float = 30.0):
        return True

    def stop(self):
        self._stopped = True


@pytest.mark.anyio
async def test_launcher_preserves_existing_live_skills(monkeypatch, tmp_path):
    cfg = SkillClawConfig(
        use_skills=True,
        skills_dir=str(tmp_path / "skillspace" / "live"),
        sharing_enabled=False,
        use_prm=False,
        validation_enabled=False,
    )
    launcher = SkillClawLauncher(_FakeConfigStore(cfg))
    launcher._stop_event.set()

    seeded = {"called": False}

    monkeypatch.setattr("skillclaw.skillspace.is_skillspace_live_dir", lambda _path: True)
    monkeypatch.setattr("skillclaw.skillspace.live_has_skills", lambda _path=None: True)
    monkeypatch.setattr(
        "skillclaw.skillspace.seed_live_from_source",
        lambda *args, **kwargs: seeded.__setitem__("called", True),
    )
    monkeypatch.setattr("skillclaw.skill_manager.SkillManager", _FakeSkillManager)
    monkeypatch.setattr("skillclaw.api_server.SkillClawAPIServer", _FakeServer)
    monkeypatch.setattr("skillclaw.claw_adapter.configure_claw", lambda _cfg: None)

    await launcher._run(cfg)

    assert seeded["called"] is False


@pytest.mark.anyio
async def test_launcher_seeds_live_skills_when_live_is_empty(monkeypatch, tmp_path):
    cfg = SkillClawConfig(
        use_skills=True,
        skills_dir=str(tmp_path / "skillspace" / "live"),
        sharing_enabled=False,
        use_prm=False,
        validation_enabled=False,
    )
    launcher = SkillClawLauncher(_FakeConfigStore(cfg))
    launcher._stop_event.set()

    seeded = {"called": False}

    monkeypatch.setattr("skillclaw.skillspace.is_skillspace_live_dir", lambda _path: True)
    monkeypatch.setattr("skillclaw.skillspace.live_has_skills", lambda _path=None: False)
    monkeypatch.setattr(
        "skillclaw.skillspace.seed_live_from_source",
        lambda *args, **kwargs: seeded.__setitem__("called", True),
    )
    monkeypatch.setattr("skillclaw.skill_manager.SkillManager", _FakeSkillManager)
    monkeypatch.setattr("skillclaw.api_server.SkillClawAPIServer", _FakeServer)
    monkeypatch.setattr("skillclaw.claw_adapter.configure_claw", lambda _cfg: None)

    await launcher._run(cfg)

    assert seeded["called"] is True
