---
name: skillclaw-claude-env
description: "Introspect the SkillClaw proxy and manage Claude Code configuration in this lab environment. Use when you need to verify the LLM relay setup, list available models/skills, or enable/disable MCP servers and tool permissions. NOT for: general Claude Code usage outside the SkillClaw-mediated lab environment, or tasks that do not require reading or editing local JSON settings."
category: general
---

- Global Claude Code settings are stored in `~/.claude/settings.json`. This file contains the SkillClaw proxy endpoint under `env.ANTHROPIC_BASE_URL` (e.g., `http://10.12.189.47:30000`) and the API token under `env.ANTHROPIC_AUTH_TOKEN` (e.g., `sk-skillclaw-lab`).
- To probe the SkillClaw API, use `curl` with the header `Authorization: Bearer <token>` against the base URL:
  - `GET <base_url>/v1/models`
  - `GET <base_url>/v1/skills`
  - `GET <base_url>/openapi.json`
- Project-level overrides, MCP server lists, and permission exceptions are stored in `./.claude/settings.local.json` relative to the current working directory.
- To enable or disable MCP servers, edit the `enabledMcpjsonServers` array inside `./.claude/settings.local.json`.
- To modify tool permissions, edit the `permissions.allow` and `permissions.deny` arrays in the same project-level file.
- Always verify the current working directory before constructing absolute paths to project settings; use relative paths (`./.claude/...`) or resolve via `find`.
