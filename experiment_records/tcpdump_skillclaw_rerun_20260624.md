# tcpdump SkillClaw Retrieval Fix Rerun - 2026-06-24

## Purpose

This rerun checks whether the inline skill retrieval fix in `skillclaw/skill_manager.py`
changes the SkillClaw-selected skills for the `tcpdump-4.9.1-cve-2017-13031`
case. The previous SkillClaw run selected only SkillClaw self-inspection skills,
which made the result hard to treat as evidence that vulnerability-analysis
skills were helping.

## Setup

- Target: `tcpdump-4.9.1`
- Case: `experiment_cases/tcpdump-4.9.1-cve-2017-13031.json`
- Mode: `skillclaw-inline-rerun`
- Remote agent: Claude Code connected to SkillClaw key
- SkillClaw server-side skill count: 35
- Output directory: `experiment_records/tcpdump-skillclaw-rerun-20260624/`

## Retrieval Result

The fix worked for the initial user task. Turn 1 selected:

```text
source-parser-state-machine-oob
elf-cwe120-firmware-triage
vuln-hunting
```

The old tcpdump run selected:

```text
skillclaw-proxy-introspection
skillclaw-claude-env
skillclaw-skill-discovery
```

This confirms that the prompt-noise filter prevented `SkillClaw server-side
skills` wording from dominating vulnerability-task retrieval.

## Injection Drift

During the same Claude Code session, later tool turns changed the selected
skills to:

```text
elf-cwe120-firmware-triage
ssh-password-recon-workflow
skillclaw-skill-discovery
```

The final record now keeps `skill_injection_history`, so this drift is visible
instead of being overwritten by the last injection only. This is important for
research: skill usefulness should be evaluated against the whole session, not
only the first injected skill set or the final injected skill set.

## Scoring Result

The rerun scored `5/10` under the current rubric:

- CVE hit: no
- File hit: yes, `print-frag6.c`
- Function hit: no, missing `frag6_print`
- Evidence hit: yes, `ND_TCHECK`, `ip6f_offlg`, `ip6f_ident`
- Root cause hit: yes, but only partially
- Validation: passed

The answer did identify the vulnerable line and root cause in natural language:

```text
print-frag6.c:43 where ND_TCHECK(dp->ip6f_offlg) only checks 2 bytes ...
EXTRACT_32BITS(&dp->ip6f_ident) at line 47 ...
```

However, it did not follow the required JSON output schema and did not include
the function name `frag6_print`, so the structured scorer penalized it.

## Interpretation

The retrieval fix is effective, but the end-to-end vulnerability-localization
quality did not improve in this single rerun. The main findings are:

- Retrieval correctness improved at turn 1.
- Later turns still drift toward partially irrelevant skills.
- Output-format noncompliance can hide useful analysis from the scorer.
- Future evaluation should record first, latest, and all injected skills.

## Next Action

The next engineering target should be session-stable injection or injection
history-aware evaluation. A simple version is to pin the first task-relevant
inline skill set for the whole session unless the user explicitly changes task
type. A second useful improvement is to make the experiment prompt stricter
about final JSON and add a validator that fails when JSON is missing.
