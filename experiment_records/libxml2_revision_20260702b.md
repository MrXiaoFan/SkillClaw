# libxml2 revision rerun (2026-07-02)

## Goal

Verify that the new local post-processing flow also works for the revision-study
case:

- remote `run_eval_case.py` produces a raw final record
- local `finalize_experiment_record.py` recovers the matching SkillClaw
  injection audit
- compare output is emitted in the same step

## Run

- Case: `libxml2-2.9.4-cve-2017-8872`
- Mode: `skillclaw-inline-guarded`
- Remote output dir: `~/skillclaw-eval/runs/libxml2-revision-20260702b`

## Result

- score: `10/10`
- validation: `passed`
- finalized session linkage:
  - `session_id = d5384b3c-9ca4-44f4-b098-dcc838c2c32c`
  - `session_id_source = inferred_from_injection_log`

## Engineering significance

This rerun shows that the new finalize helper is not limited to the `giflib`
confirmation path. It also works for the `libxml2` revision-study path and
produces a ready-to-compare finalized record without manual session-id lookup.
