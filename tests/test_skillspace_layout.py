from pathlib import Path

from skillclaw import runtime_state, skillspace
from skillclaw.config_store import resolve_sharing_local_root, resolve_skills_dir


def test_resolve_skills_dir_maps_legacy_repo_skills_to_live():
    legacy_dir = skillspace.default_layout().legacy_source_dir
    resolved = resolve_skills_dir(str(legacy_dir), claw_type="openclaw")
    assert Path(resolved) == skillspace.default_layout().live_dir


def test_resolve_sharing_local_root_maps_legacy_share_to_skillspace_share():
    legacy_root = skillspace.default_layout().legacy_share_dir
    resolved = resolve_sharing_local_root(str(legacy_root))
    assert Path(resolved) == skillspace.default_layout().share_dir


def test_skill_stats_path_uses_skillspace_state_for_live_dir():
    live_dir = skillspace.default_layout().live_dir
    expected = skillspace.default_layout().state_dir / "skill_stats.json"
    assert runtime_state.skill_stats_path(str(live_dir)) == expected


def test_git_managed_detection_skips_skillspace_live_dir():
    live_dir = skillspace.default_layout().live_dir
    assert runtime_state.is_git_managed_path(str(live_dir)) is False


def test_live_has_skills_detects_skill_directories(tmp_path):
    live_dir = tmp_path / "live"
    (live_dir / "demo-skill").mkdir(parents=True)
    (live_dir / "demo-skill" / "SKILL.md").write_text("# demo\n", encoding="utf-8")

    assert skillspace.live_has_skills(live_dir) is True


def test_live_has_skills_is_false_for_empty_or_non_skill_dirs(tmp_path):
    live_dir = tmp_path / "live"
    (live_dir / "notes").mkdir(parents=True)
    (live_dir / "notes" / "README.md").write_text("demo\n", encoding="utf-8")

    assert skillspace.live_has_skills(live_dir) is False
