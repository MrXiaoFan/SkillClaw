from __future__ import annotations

from evolve_server.core.skill_registry import SkillIDRegistry


def test_prune_unpublished_placeholders_removes_only_empty_unpublished_entries() -> None:
    registry = SkillIDRegistry()
    registry._map = {
        "published-skill": {
            "skill_id": "111111111111",
            "version": 2,
            "content_sha": "abc",
            "history": [{"version": 1}],
        },
        "placeholder-skill": {
            "skill_id": "222222222222",
            "version": 0,
            "content_sha": "",
            "history": [],
        },
        "historical-unpublished-skill": {
            "skill_id": "333333333333",
            "version": 1,
            "content_sha": "",
            "history": [{"version": 1}],
        },
    }

    removed = registry.prune_unpublished_placeholders({"published-skill"})

    assert removed == ["placeholder-skill"]
    assert "placeholder-skill" not in registry._map
    assert "published-skill" in registry._map
    assert "historical-unpublished-skill" in registry._map
