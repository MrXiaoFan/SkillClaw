# giflib confirmation rerun (2026-07-02)

## Goal

Validate the new local post-processing path:

- remote `run_eval_case.py` produces the raw final record
- local `finalize_experiment_record.py` attaches injection audit automatically
- optional before/after compare is generated in one step

## Run

- Case: `giflib-5.1.2-cve-2016-3977`
- Mode: `skillclaw-inline-guarded`
- Remote output dir: `~/skillclaw-eval/runs/giflib-confirmation-20260702a`

## Result

- score: `10/10`
- validation: `passed`
- artifact exec: `passed`
- ASan: `passed`
- finalized session linkage:
  - `session_id = 6cd995b4-0232-4006-8fce-18e7fda53e05`
  - `session_id_source = inferred_from_injection_log`

## Selected skills

- `source-parser-state-machine-oob`
- `ida-headless-cwe120-sink-analysis`
- `idalib-headless-batch-diagnosis`

## Engineering significance

This rerun confirms that the new finalize helper can recover injection audit
from the local SkillClaw log and emit a ready-to-compare finalized record
without manual session-id lookup.
