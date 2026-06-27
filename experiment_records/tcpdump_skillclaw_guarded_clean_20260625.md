# tcpdump SkillClaw Guarded Clean Run - 2026-06-25

## Run Metadata

- Case: `tcpdump-4.9.1-cve-2017-13031`
- Mode: `Claude Code + SkillClaw key`
- Prompt mode: `skillclaw-inline-guarded-clean`
- Remote cwd: `/home/li/skillclaw-eval/tcpdump-4.9.1`
- Run id: `tcpdump-skillclaw-guarded-clean-20260625-152601`
- Claude session id: `9e7e45c8-6f15-49cb-9d0a-4d69c4e0770b`
- Local copied output: `experiment_records/remote_runs/tcpdump-skillclaw-guarded-clean-20260625-152601.claude.json`
- Local copied prompt: `experiment_records/remote_runs/tcpdump-skillclaw-guarded-clean-20260625-152601.prompt.txt`
- Score output: `experiment_records/tcpdump_skillclaw_guarded_scores_20260625.jsonl`

## Cleanup Before Run

Before this run, the previous result artifact in the target source root was moved away:

```text
/home/li/skillclaw-eval/tcpdump-4.9.1/frag6-oob-read.json
-> /home/li/skillclaw-eval/runs/archived_target_artifacts/tcpdump-4.9.1/frag6-oob-read-20260625-before-clean-run.json
```

This matters because an earlier guarded run read that old JSON artifact and produced a contaminated answer. The clean run prompt also explicitly prohibited reading previous experiment outputs, notes, result files, or JSON files.

## Skill Injection

SkillClaw selected and pinned the following server-side skills for the session:

```text
source-parser-state-machine-oob
elf-cwe120-firmware-triage
vuln-hunting
```

The server log showed `stable=pin` on the first turn and `stable=reuse` on later turns, confirming that the session-stable inline injection cache worked as intended. The earlier irrelevant `ssh-password-recon-workflow` was no longer injected after the SSH-noise routing fix.

## Agent Output

The run completed successfully:

```json
{
  "subtype": "success",
  "is_error": false,
  "num_turns": 9,
  "total_cost_usd": 0.271084
}
```

The final prediction was:

```json
{
  "predicted_cves": ["CVE-2017-13005"],
  "predicted_files": ["print-frag6.c"],
  "predicted_functions": ["frag6_print"],
  "confidence": "high"
}
```

The answer correctly identified the file, function, insufficient `ND_TCHECK` guard, `ip6f_offlg` check, and later `ip6f_ident` read. However, it mapped the finding to the wrong CVE. The expected CVE for this benchmark case is `CVE-2017-13031`.

## Score

The scorer returned:

```text
score = 8.0 / 10.0
```

Breakdown:

- CVE: miss. Expected `CVE-2017-13031`; predicted `CVE-2017-13005`.
- File: hit. `print-frag6.c`.
- Function: hit. `frag6_print`.
- Evidence: hit. `frag6_print`, `ND_TCHECK`, `ip6f_offlg`, `ip6f_ident`.
- Root cause: hit. Insufficient bounds checking before reading later fields of the IPv6 fragment header.

## Interpretation

This run is a useful positive engineering result but not a full research win. The retrieval and execution-control fixes improved the run from budget exhaustion to a concise, scoreable vulnerability-localization answer. The remaining failure is CVE-level calibration: the model understands the memory-safety bug but confuses tcpdump CVE identifiers in the same vulnerability family.

For the paper direction, this supports a more precise claim:

```text
Skill-guided execution can improve localization structure and evidence quality, but text-only skill injection does not reliably solve benchmark identity mapping or final-answer calibration.
```

The next experiment should rerun the same clean guarded prompt with direct DeepSeek, then compare:

- score,
- cost,
- turns,
- file/function/root-cause precision,
- CVE mapping accuracy,
- tool-use behavior.
