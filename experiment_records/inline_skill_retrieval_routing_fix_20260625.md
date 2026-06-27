# Inline Skill Retrieval Routing Fix - 2026-06-25

## Problem

The first session-stable inline experiment showed that stable injection fixed turn-to-turn skill drift, but the first pinned skill set could still be wrong. In one formal tcpdump run, SkillClaw pinned `ida-headless-cwe120-sink-analysis`, `elf-cwe120-firmware-triage`, and `skillclaw-proxy-introspection` for a source-level IPv6 fragmentation parser over-read task. This made the SkillClaw group spend budget under mismatched guidance.

## Change

Updated `skillclaw/skill_manager.py` keyword routing for inline injection:

1. Treat `SkillClaw`, `server-side`, `API proxy`, and similar words as plumbing language, not task semantics.
2. Exclude `skillclaw-*` self-inspection skills from vulnerability-analysis tasks, even when the prompt mentions the SkillClaw proxy.
3. Detect source-level parser boundary tasks using terms such as `parser`, `fragmentation`, `tcpdump`, `source`, `oob`, `overread`, `bounds`, and `guard`.
4. Boost `source-parser-state-machine-oob` for source parser boundary tasks.
5. Exclude IDA/idalib skills from source parser tasks unless the user explicitly asks for IDA, Hex-Rays, headless, or decompiler analysis.
6. Exclude `ssh-password-recon-workflow` from vulnerability tasks unless the request has clear SSH intent, such as SSH plus password/login/paramiko/reconnaissance terms. This prevents remote-execution plumbing from becoming task guidance.

## Regression Tests

Added tests in `tests/test_experiment_scripts.py`:

1. `test_inline_retrieval_prefers_source_parser_skill_for_tcpdump_prompt`
2. `test_inline_retrieval_keeps_skillclaw_meta_for_catalog_task`
3. `test_inline_retrieval_ignores_incidental_ssh_noise_in_vulnerability_task`

Verified:

```text
python -m pytest tests/test_experiment_scripts.py tests/test_inline_skill_session_cache.py
25 passed
```

## Service Smoke Test

After restarting SkillClaw, a minimal `/v1/messages` probe with the tcpdump prompt produced:

```text
[SkillManager] inlining 3 skill(s) stable=pin:
source-parser-state-machine-oob, vuln-hunting, vuln-hunting-claw
```

This confirms the updated routing is active in the running proxy.

After a real Claude Code run still selected `ssh-password-recon-workflow` from SSH/runtime noise, the SSH-noise filter was added and smoke-tested with a prompt that explicitly mentioned remote SSH transport. The running proxy then selected:

```text
[SkillManager] inlining 3 skill(s) stable=pin:
source-parser-state-machine-oob, elf-cwe120-firmware-triage, vuln-hunting
```

## Remaining Risk

This fix improves initial skill routing, but it does not by itself prove that the selected skill improves vulnerability localization. The next experiment should rerun the tcpdump SkillClaw group under the corrected routing and compare it with the earlier direct DeepSeek and SkillClaw records using the same scoring rubric.
