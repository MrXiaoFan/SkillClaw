import base64
import struct
from unittest.mock import patch

import httpx
import pytest

from skillclaw.api_server import SkillClawAPIServer
from skillclaw.config import SkillClawConfig


@pytest.fixture
def anthropic_server(tmp_path):
    return SkillClawAPIServer(
        SkillClawConfig(
            proxy_api_key="skillclaw",
            record_enabled=False,
            record_dir=str(tmp_path),
            claw_type="nanoclaw",
        )
    )


@pytest.mark.asyncio
async def test_anthropic_count_tokens_endpoint_returns_local_estimate(anthropic_server):
    client = httpx.AsyncClient(transport=httpx.ASGITransport(app=anthropic_server.app), base_url="http://test")
    try:
        response = await client.post(
            "/v1/messages/count_tokens",
            headers={"x-api-key": "skillclaw"},
            json={
                "model": "claude-code-test",
                "messages": [{"role": "user", "content": [{"type": "text", "text": "hello"}]}],
                "tools": [{"name": "Read", "description": "read", "input_schema": {"type": "object"}}],
            },
        )
    finally:
        await client.aclose()

    assert response.status_code == 200
    assert response.json()["input_tokens"] > 0


@pytest.mark.asyncio
async def test_anthropic_count_tokens_accounts_for_image_content(anthropic_server):
    png_header = (
        b"\x89PNG\r\n\x1a\n"
        + struct.pack(">I", 13)
        + b"IHDR"
        + struct.pack(">II", 2000, 2000)
        + b"\x08\x02\x00\x00\x00"
    )
    image_data = base64.b64encode(png_header).decode("ascii")
    client = httpx.AsyncClient(transport=httpx.ASGITransport(app=anthropic_server.app), base_url="http://test")
    try:
        response = await client.post(
            "/v1/messages/count_tokens",
            headers={"x-api-key": "skillclaw"},
            json={
                "model": "claude-code-test",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "look"},
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": image_data,
                                },
                            },
                        ],
                    }
                ],
            },
        )
    finally:
        await client.aclose()

    assert response.status_code == 200
    assert response.json()["input_tokens"] >= 5000


@pytest.mark.asyncio
async def test_anthropic_messages_uses_claude_code_session_header(anthropic_server):
    seen = {}

    async def fake_handle_request(body, session_id, turn_type, session_done):
        seen["body"] = body
        seen["session_id"] = session_id
        seen["turn_type"] = turn_type
        seen["session_done"] = session_done
        return {
            "response": {
                "id": "chatcmpl_1",
                "choices": [{"message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1},
            }
        }

    anthropic_server._handle_request = fake_handle_request
    client = httpx.AsyncClient(transport=httpx.ASGITransport(app=anthropic_server.app), base_url="http://test")
    try:
        response = await client.post(
            "/v1/messages",
            headers={"x-api-key": "skillclaw", "x-claude-code-session-id": "claude-session-1"},
            json={
                "model": "claude-code-test",
                "messages": [{"role": "user", "content": "hi"}],
            },
        )
    finally:
        await client.aclose()

    assert response.status_code == 200
    assert response.json()["content"] == [{"type": "text", "text": "ok"}]
    assert seen["session_id"] == "claude-session-1"
    identity = anthropic_server._session_segments["claude-session-1"]
    assert identity["client_session_id"] == "claude-session-1"
    assert identity["session_id_source"] == "x-claude-code-session-id"
    assert identity["session_segment_id"]


@pytest.mark.asyncio
async def test_anthropic_messages_preserves_registered_custom_tool_name(anthropic_server):
    async def fake_handle_request(body, session_id, turn_type, session_done):
        return {
            "response": {
                "id": "chatcmpl_1",
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "",
                            "tool_calls": [
                                {
                                    "id": "call_read",
                                    "type": "function",
                                    "function": {
                                        "name": "read",
                                        "arguments": '{"path":"/tmp/demo.py","mode":"raw"}',
                                    },
                                }
                            ],
                        },
                        "finish_reason": "tool_calls",
                    }
                ],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1},
            }
        }

    anthropic_server._handle_request = fake_handle_request
    client = httpx.AsyncClient(transport=httpx.ASGITransport(app=anthropic_server.app), base_url="http://test")
    try:
        response = await client.post(
            "/v1/messages",
            headers={"x-api-key": "skillclaw"},
            json={
                "model": "claude-code-test",
                "messages": [{"role": "user", "content": "use custom read"}],
                "tools": [
                    {
                        "name": "read",
                        "description": "custom read tool",
                        "input_schema": {"type": "object"},
                    }
                ],
            },
        )
    finally:
        await client.aclose()

    assert response.status_code == 200
    assert response.json()["content"] == [
        {
            "type": "tool_use",
            "id": "call_read",
            "name": "read",
            "input": {"path": "/tmp/demo.py", "mode": "raw"},
        }
    ]


@pytest.mark.asyncio
async def test_forward_to_deepseek_chat_normalizes_multimodal_messages_to_text_only(tmp_path):
    server = SkillClawAPIServer(
        SkillClawConfig(
            proxy_api_key="skillclaw",
            record_enabled=False,
            record_dir=str(tmp_path),
            claw_type="nanoclaw",
            llm_provider="openai",
            llm_api_base="https://api.deepseek.com",
            llm_api_key="test-key",
            llm_model_id="deepseek-v4-pro",
        )
    )
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "id": "chatcmpl_1",
                "choices": [{"message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1},
            }

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, json, headers):
            captured["url"] = url
            captured["json"] = json
            captured["headers"] = headers
            return FakeResponse()

    body = {
        "model": "skillclaw-model",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "inspect this target"},
                    {"type": "image_url", "image_url": {"url": "data:image/gif;base64,AAAA"}},
                ],
            }
        ],
    }

    with patch("httpx.AsyncClient", FakeAsyncClient):
        result = await server._forward_to_llm_openai(body)

    assert result["choices"][0]["message"]["content"] == "ok"
    assert captured["url"] == "https://api.deepseek.com/chat/completions"
    assert captured["json"]["messages"] == [
        {
            "role": "user",
            "content": (
                "inspect this target\n"
                "[non-text input omitted: image_url; use shell/file tools in the workspace to inspect target files directly]"
            ),
        }
    ]
