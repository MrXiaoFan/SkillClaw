# Dynamic Validation MVP Plan

目标：一周内完成一个能支撑论文 idea 的最小闭环，而不是实现通用漏洞验证平台。

## Scope

本阶段只覆盖两个 case：

1. `libxml2-2.9.4-cve-2017-8872`
2. `tcpdump-4.9.1-cve-2017-13031`

本阶段只比较三种模式：

1. `direct-deepseek`
2. `skillclaw-inline-default`
3. `skillclaw-inline-named-skill`

## Deliverables

1. 每个 case 的 ground truth JSON。
2. 每次 agent 输出的 JSON 评分结果。
3. 每次 SkillClaw 会话的 server-side skill 注入审计记录。
4. 每个 case 的 source/binary/PoC/ASan 证据记录。
5. 一张对照表：case、mode、selected skills、hit file、hit function、hit CVE、score、failure reason。

## Minimal Acceptance Criteria

### Engineering

- `score_agent_output.py` can score an agent JSON answer against a case.
- `run_dynamic_case.py` can run source-level validators on the remote VM.
- `extract_skill_injection.py` can extract selected SkillClaw server-side skills for a session.
- The result record includes `selected_skill_names` and `skill_prompt_hash` whenever the mode is SkillClaw.
- `asan_command` can treat sanitizer/crash evidence as positive dynamic evidence instead of ordinary command failure.

### Research

- At least one positive or partially positive SkillClaw case is documented.
- At least one negative or regression case is documented.
- The conclusion distinguishes skill usefulness from retrieval/injection correctness.
- The evidence separates three questions: whether the skill was selected, whether the answer hit the ground truth, and whether external validation supports the hit.

## Non-Goals

- No general fuzzing platform.
- No automatic exploit generation.
- No large dashboard rewrite.
- No automatic publication gate integration into `evolve_server` this week.
- No claim that SkillClaw universally outperforms the base LLM.

## Paper Framing

The intended claim is:

> Textual skill evolution alone is not enough to prove vulnerability-localization improvement. SkillClaw needs auditable skill injection and case-level validation to determine when a skill helps, hurts, or is not selected.

The MVP evidence should support this narrower claim.
