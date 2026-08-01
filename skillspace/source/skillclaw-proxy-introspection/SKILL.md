---
name: skillclaw-proxy-introspection
description: "Use when asked to list available skills, probe SkillClaw proxy APIs, or explain how skills are loaded. SkillClaw exposes only standard LLM endpoints and injects skills via the session system prompt; there is no queryable skill registry. NOT for: tasks involving target device exploitation or firmware analysis."
category: general
---

SkillClaw Proxy exposes only standard OpenAI-compatible LLM endpoints. Do not waste time probing for skill-management APIs.

Known proxy endpoints (example base URL `http://<host>:30000`):
- `GET /healthz` – health check
- `GET /openapi.json` – proxy OpenAPI specification
- `GET /v1/models` – returns `skillclaw-model`
- `POST /v1/chat/completions` – standard chat completions
- `POST /v1/responses` – responses endpoint

There are NO skill or tool registry endpoints. Paths such as `/v1/skills`, `/api/skills`, `/v1/tools`, `/v1/functions`, `/v1/agents`, and `/v1/plugins` return 404.

Skill injection model:
- Skills are injected into the session via the system prompt context (visible as `injected=[...]` or in system reminders), not through any HTTP API.
- When a user asks you to list all available skills or tools, enumerate ONLY the skills explicitly visible in the current session context.
- Do not attempt to query a server-side registry via curl or hallucinate skills beyond those shown in context.
- If you need details about a specific skill, use the `Skill` tool to read it by name.

Local router artifacts (if analyzing the host):
- Configuration and logs may reside under `~/.claude-code-router/` (e.g., `config.json`, `logs/`).
- The proxy typically routes requests to upstream LLM backends; it does not itself host skill orchestration logic.
