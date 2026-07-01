# giflib Confirmation Follow-up - 2026-07-01

## Scope

This note captures the follow-up `skillclaw-inline-guarded` rerun after we
updated the confirmation contract to require wrapper reproduction scripts to
preserve the crashing target's exit status.

Primary records:

- original local follow-up final:
  `experiment_records/remote_runs/giflib-confirmation-20260701c/giflib-5.1.2-cve-2016-3977-skillclaw-inline-guarded-20260701-201932-final.json`
- postprocessed final with injection audit:
  `experiment_records/remote_runs/giflib-confirmation-20260701c/giflib-5.1.2-cve-2016-3977-skillclaw-inline-guarded-20260701-201932-final-with-injection.json`

## Why A Follow-up Was Needed

The previous confirmation run already triggered the expected ASan crash, but
the generated wrapper script printed the target exit code and then returned
success itself. That made `artifact_exec` look weaker than the underlying crash
path actually was.

We fixed this by strengthening the prompt contract so that any generated
wrapper script must preserve the crashing target's exit status.

## Result

| Dimension | Result |
| --- | --- |
| Score | `10/10` |
| Validation status | `passed` |
| Artifact exists | `passed` |
| Artifact exec | `passed` |
| Artifact exec return code | `134` |
| ASan validation | `passed` |

The confirmation chain is now cleaner:

1. the agent still localizes the correct file/function/root cause,
2. the generated artifact still triggers the bug,
3. the wrapper script now propagates the crash correctly,
4. `artifact_exec` and `asan_command` both pass without interpretation gaps.

## Recovered Injection Audit

The local SkillClaw log retained the corresponding session and selected skills.
Recovered values:

- `session_id`: `445d3d13-a9ab-4690-acae-e2bde9c89b4d`
- `selected_skills`:
  - `source-parser-state-machine-oob`
  - `ida-headless-cwe120-sink-analysis`
  - `idalib-headless-batch-diagnosis`

## Engineering Takeaway

This follow-up confirms a practical point about the confirmation pipeline:

- validator failures can come from the generated helper artifact itself, not
  from the underlying target reproduction path,
- and small prompt-contract changes can make artifact execution evidence much
  cleaner without changing the underlying vulnerability result.
