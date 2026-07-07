# Curated Runset 2026-07-05

## Inputs

This curated set is built from four finalized records:

1. `experiment_records/remote_runs/giflib-confirmation-20260702a/giflib-5.1.2-cve-2016-3977-skillclaw-inline-guarded-20260702-083840-final-with-injection.json`
2. `experiment_records/remote_runs/tcpdump-confirmation-20260702a/tcpdump-4.9.1-cve-2017-13031-skillclaw-inline-guarded-20260702-093822-final-with-injection.json`
3. `experiment_records/remote_runs/tcpdump-confirmation-20260702b-direct/tcpdump-4.9.1-cve-2017-13031-direct-deepseek-guarded-20260702-094727-final.json`
4. `experiment_records/remote_runs/libxml2-logic-confirmation-20260705/libxml2-2.9.4-cve-2017-8872-skillclaw-inline-guarded-logic-confirmation-20260705-final-with-injection.json`

The `libxml2` record is a derived archive that preserves the original 2026-07-02 run output but replaces the validation block with the 2026-07-05 logic-confirmation result.

## Output files

- `experiment_records/experiment_matrix_20260705_curated.md`
- `experiment_records/experiment_matrix_20260705_curated.csv`
- `experiment_records/skill_feedback_20260705_curated.md`
- `experiment_records/skill_feedback_20260705_curated.csv`
- `experiment_records/skill_gate_report_20260705_curated.md`
- `experiment_records/skill_gate_report_20260705_curated.json`
- `experiment_records/skill_feedback_bundle_20260705_curated.md`
- `experiment_records/skill_feedback_bundle_20260705_curated.json`

## Main signals

1. `source-parser-state-machine-oob`
   - selected in all 3 SkillClaw runs
   - gate result: `promote`
   - current evidence: `3/3` localization + CVE + validator passed

2. `vuln-hunting`
   - selected in `tcpdump` and `libxml2`
   - gate result: `keep`
   - current evidence: useful, but still only `2` runs

3. Other selected skills
   - `elf-cwe120-firmware-triage`
   - `ida-headless-cwe120-sink-analysis`
   - `idalib-headless-batch-diagnosis`
   - `verify-rootfs-full-enumeration`
   - current gate result: `insufficient_evidence`

## Caution

This curated set is useful for engineering status and short-term skill triage, but it is still too small to support broad task-family claims. It should be treated as a checkpoint, not a final generalization set.
