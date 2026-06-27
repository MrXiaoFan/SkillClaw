---
name: skillclaw-retrieval-optimization
description: "Guides concrete optimization of SkillClaw's skill retrieval pipeline. Use when users ask about adaptive k values, retrieval budgets, deduplication thresholds, or prompt injection limits in SkillClaw. NOT for: generic KNN/K-means theory, vector database tuning, or non-retrieval SkillClaw internals."
category: general
---

Optimize SkillClaw's retrieval pipeline in `skill_manager.py`. When users mention "adaptive k", retrieval budgets, or deduplication thresholds, they refer to this codebase, not generic KNN/K-means theory.

Key integration points:
- **`retrieve()`**: Currently fetches a fixed number of skills.
- **`build_injection_prompt()`**: Enforces `max_chars=30_000` (~line 650). This budget is currently decoupled from `retrieve()`.

Implement these concrete modifications:

1. **Token-budget dynamic retrieval** (`retrieve_with_budget`):
   - Fetch candidates by similarity descending.
   - Greedily pack skill summaries until `max_chars` is exhausted. Stop when the next candidate would exceed the budget.

2. **Similarity-gap truncation**:
   - After ranking, compute score deltas between consecutive candidates.
   - If a gap exceeds a threshold (e.g., 0.15–0.20), drop all lower-ranked results. This adapts the effective k to query clarity.

3. **Deduplication-aware packing**:
   - Apply the 0.9 deduplication threshold during packing so redundant skills do not waste the `max_chars` budget.

Always cite concrete method names, file names, and parameter values from the SkillClaw codebase. Never answer with generic vector-retrieval or clustering theory.
