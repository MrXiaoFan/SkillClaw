---
name: skillclaw-internal-mechanics-inspection
description: "Use when users ask about SkillClaw's internal behavior, retrieval logic, embedding mechanics, or proxy injection details. Directs the agent to read the local source code rather than providing theoretical or literature-based answers. NOT for: general software engineering questions unrelated to SkillClaw, or tasks that do not inquire about the framework's own implementation."
category: general
---

When asked about SkillClaw's internal mechanics—such as top-k retrieval granularity, embedding computation, skill injection, or proxy behavior—examine the local source code instead of theorizing.

1. Locate `skill_manager.py` in the current working directory and inspect the relevant methods (e.g., `_embedding_retrieve`, `_skill_to_text`, `retrieve_skills`).
2. Verify the retrieval unit: determine whether the code returns whole skill documents/dicts or individual steps/chunks.
3. Inspect embedding construction for truncation or slicing logic (e.g., content limited to the first N characters before vectorization), which can make later parts of long skills invisible to retrieval.
4. If the question involves proxy or injection behavior, inspect the proxy source files present in the runtime environment.
5. Cite specific file names, method names, and code snippets to support the answer.

Do not answer based on general agent-framework literature or speculation.
