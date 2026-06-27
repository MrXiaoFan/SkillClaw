# tcpdump SkillClaw Post-Fix Run - Budget-Truncated Sample - 2026-06-25

## Run Metadata

- Case: `tcpdump-4.9.1-cve-2017-13031`
- Mode: `Claude Code + SkillClaw key`
- Remote cwd: `/home/li/skillclaw-eval/tcpdump-4.9.1`
- Run id: `tcpdump-skillclaw-postfix-20260625-150813`
- Claude session id: `a2bcd0e4-dba9-4230-a511-e6085f868d37`
- Local copied output: `experiment_records/remote_runs/tcpdump-skillclaw-postfix-20260625-150813.claude.json`
- Budget: `$0.45`

## Prompt

The run used the tcpdump case prompt:

```text
Do not use WebSearch. The current working directory is tcpdump-4.9.1 and the target program is ./tcpdump. Use SkillClaw server-side skills to locate a known buffer over-read vulnerability related to the IPv6 fragmentation header parser. Do not invoke Claude Code local Skill(...). Analyze source code and build artifacts. Finish with a single JSON object containing predicted_cves, predicted_files, predicted_functions, root_cause, evidence, and confidence.
```

## Observed Skill Injection

The first post-fix run showed partial routing improvement:

```text
source-parser-state-machine-oob, elf-cwe120-firmware-triage, ssh-password-recon-workflow
```

The session-stable cache correctly reused that set across later turns, but `ssh-password-recon-workflow` was still irrelevant. This exposed a second retrieval-noise issue: real Claude Code requests can contain SSH/remote-operation text that should not be interpreted as the target task.

After adding an SSH-noise filter and restarting SkillClaw, a smoke probe with explicit SSH transport noise selected:

```text
source-parser-state-machine-oob, elf-cwe120-firmware-triage, vuln-hunting
```

## Outcome

The formal run did not produce a final JSON answer:

```json
{
  "subtype": "error_max_budget_usd",
  "is_error": true,
  "num_turns": 18,
  "stop_reason": "tool_use",
  "total_cost_usd": 0.45573499999999995
}
```

This record should not be scored as a successful or failed localization answer because there is no final prediction object. It should be treated as an execution-control failure sample.

## Interpretation

This run is still useful for engineering analysis:

1. Session-stable inline injection works: later turns reused the initially pinned skills.
2. Initial retrieval still matters: a wrong third skill wastes prompt budget and can steer tool use.
3. Claude Code may continue tool use until budget exhaustion even after it has enough evidence, so the evaluation runner needs stronger stop/final-answer enforcement.

## Follow-Up

1. Keep the SSH-noise routing fix.
2. Add a runner-level final-answer guard or prompt wrapper that forces early JSON output after key evidence is found.
3. Rerun tcpdump only after the guard is in place, otherwise more budget may be spent without a final scoreable answer.

## Guard Implementation

Added guarded prompt modes in `experiment_scripts/print_case_prompt.py`:

- `skillclaw-inline-guarded`
- `direct-deepseek-guarded`

These modes reuse the same case prompt as their unguarded counterparts, then append execution constraints:

- no task-list tools,
- at most 8 tool calls,
- stop once file/function/root-cause/evidence are found,
- output a single JSON object even when uncertain.

Regression test:

```text
python -m pytest tests/test_experiment_scripts.py tests/test_inline_skill_session_cache.py
27 passed
```
