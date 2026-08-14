from __future__ import annotations

import inspect
import types

import pytest

from evolve_server.core.config import EvolveServerConfig
from evolve_server.engines.workflow import EvolveServer


@pytest.mark.anyio
async def test_notify_proxy_reload_posts_callback_with_auth(monkeypatch) -> None:
    server = EvolveServer.__new__(EvolveServer)
    server.config = EvolveServerConfig(
        skill_reload_mode="callback",
        proxy_reload_url="http://proxy.test/",
        proxy_reload_api_key="secret",
    )
    captured = {}

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            captured["timeout"] = kwargs.get("timeout")

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, headers):
            captured["url"] = url
            captured["headers"] = headers
            return types.SimpleNamespace(raise_for_status=lambda: None)

    fake_httpx = types.SimpleNamespace(AsyncClient=FakeAsyncClient)
    monkeypatch.setitem(__import__("sys").modules, "httpx", fake_httpx)

    await server._notify_proxy_reload()

    assert captured == {
        "timeout": 5.0,
        "url": "http://proxy.test/internal/reload-skills",
        "headers": {"Authorization": "Bearer secret"},
    }


@pytest.mark.anyio
async def test_notify_proxy_reload_retries_on_http_error(monkeypatch) -> None:
    server = EvolveServer.__new__(EvolveServer)
    server.config = EvolveServerConfig(
        skill_reload_mode="callback",
        proxy_reload_url="http://proxy.test",
        proxy_reload_api_key="secret",
    )
    attempts = {"count": 0}

    class FakeResponse:
        def raise_for_status(self):
            raise RuntimeError("401 Unauthorized")

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, headers):
            attempts["count"] += 1
            return FakeResponse()

    async def fake_sleep(_delay):
        return None

    fake_httpx = types.SimpleNamespace(AsyncClient=FakeAsyncClient)
    monkeypatch.setitem(__import__("sys").modules, "httpx", fake_httpx)
    monkeypatch.setattr("evolve_server.engines.workflow.asyncio.sleep", fake_sleep)

    await server._notify_proxy_reload()

    assert attempts == {"count": 3}


@pytest.mark.anyio
async def test_notify_proxy_reload_skips_non_callback_modes(monkeypatch) -> None:
    server = EvolveServer.__new__(EvolveServer)
    server.config = EvolveServerConfig(
        skill_reload_mode="poll",
        proxy_reload_url="http://proxy.test",
        proxy_reload_api_key="secret",
    )
    called = {"http": False}

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            called["http"] = True

    fake_httpx = types.SimpleNamespace(AsyncClient=FakeAsyncClient)
    monkeypatch.setitem(__import__("sys").modules, "httpx", fake_httpx)

    await server._notify_proxy_reload()

    assert called == {"http": False}


@pytest.mark.anyio
async def test_run_once_returns_processing_errors_for_failed_skill_group(monkeypatch) -> None:
    server = EvolveServer.__new__(EvolveServer)
    server.config = EvolveServerConfig(publish_mode="validated")
    server._bucket = object()
    server._prefix = "default/"
    server._nacos_skill_client = None
    server._llm = object()

    class FakeRegistry:
        def prune_unpublished_placeholders(self, _published):
            return None

        def save_to_oss(self, *_args, **_kwargs):
            return None

    server._id_registry = FakeRegistry()

    async def fake_call_storage(fn, *args, **kwargs):
        result = fn(*args, **kwargs)
        if inspect.isawaitable(result):
            return await result
        return result

    async def fake_load_validated_pairs():
        return (
            [
                {
                    "session_id": "sess-1",
                    "_skills_referenced": {"skill-a", "skill-b"},
                    "validator_feedback": [],
                }
            ],
            ["session-key"],
            ["feedback-key"],
            {
                "ready_pairs": 1,
                "active_sessions": 0,
                "closed_sessions_waiting_feedback": 0,
                "stale_closed_sessions_without_feedback": 0,
                "feedback_waiting_session": 0,
            },
        )

    async def fake_evolve_skill_group(skill_name, sessions, existing_skill_names, *, feedback_context=None):
        assert sessions
        assert "skill-a" in existing_skill_names
        assert feedback_context is None
        if skill_name == "skill-a":
            raise RuntimeError("boom from skill-a")
        return None

    async def fake_finalize_validation_jobs():
        return [], {"publish_mode": "validated", "jobs_scanned": 0, "pending": 0, "published": 0, "rejected": 0, "skipped": 0}

    async def fake_summarize_sessions_parallel(_llm, sessions):
        return ["summary" for _ in sessions]

    monkeypatch.setattr("evolve_server.engines.workflow.summarize_sessions_parallel", fake_summarize_sessions_parallel)
    server._call_storage = fake_call_storage
    server._load_remote_skills = lambda: {"skill-a": {"name": "skill-a"}, "skill-b": {"name": "skill-b"}}
    server._load_validated_pairs = fake_load_validated_pairs
    async def fake_run_session_judge(sessions):
        return {
            "enabled": True,
            "judged_sessions": len(sessions),
            "scored_sessions": 0,
            "mean_score": None,
            "min_score": None,
            "max_score": None,
        }

    server._evolve_skill_group = fake_evolve_skill_group
    server._handle_no_skill_sessions = lambda sessions, existing_skill_names: []
    server._finalize_validation_jobs = fake_finalize_validation_jobs
    server._append_history = lambda summary: None
    server._notify_proxy_reload = lambda: None
    server._uses_nacos_skill_registry = lambda: False
    server._paired_feedback_map = lambda sessions: {}
    server._run_session_judge = fake_run_session_judge
    server._collect_skill_verifier_summary = lambda records: {
        "enabled": False,
        "verified_skills": 0,
        "accepted": 0,
        "rejected": 0,
        "mean_score": None,
        "min_score": None,
        "max_score": None,
    }

    summary = await server.run_once()

    assert summary["sessions"] == 1
    assert summary["skill_groups"] == 2
    assert summary["had_processing_error"] is True
    assert summary["processing_errors"] == [
        {
            "stage": "skill_group",
            "skill_name": "skill-a",
            "error_type": "RuntimeError",
            "message": "boom from skill-a",
        }
    ]
