---
name: skillclaw-skill-discovery
description: "Use when a user asks to list, discover, or obtain available skills in a SkillClaw session. Clarifies that 'skill' refers to the dynamically injected Skill tool catalog, not game, voice-assistant, or career skills. NOT for: detailed usage instructions of a specific skill or for skill acquisition outside the SkillClaw framework."
category: general
---

In SkillClaw, when a user asks to '获取skill', 'list skills', 'what skills are available', or similar, they are asking about the injected Skill tool catalog—not game, voice-assistant, or career skills.
1. Check the system context for any enumerated skill inventory. If present, list each skill with its name and function.
2. If no inventory is provided, state that SkillClaw provides dynamically injected domain-specific skills (e.g., update-config, keybindings-help, simplify, loop, schedule, claude-api, elf-cwe120-firmware-triage, cisco-wsma-enumeration) and ask the user to describe their task for recommendations.
3. Never answer with generic skill-acquisition advice (gaming, Alexa, Coursera, etc.) unless the user explicitly references those domains.
