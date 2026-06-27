# source-parser-state-machine-oob Revision Note

Date: 2026-06-28

## Trigger

`experiment_records/skill_gate_report_latest.md` marked
`source-parser-state-machine-oob` as `revise`.

The skill had positive localization evidence in the current benchmark records:

- selected_count: 3
- positive: 3
- mean_score: 0.8
- file_hits: 3
- function_hits: 3

However, the gate also found:

- cve_hits: 0
- localization evidence exists, but exact CVE calibration is absent

## Change

`Skills/source-parser-state-machine-oob/SKILL.md` was revised to separate:

- source localization
- root-cause evidence
- exact CVE identity

The updated skill now requires a CVE calibration pass before claiming an exact
CVE. If no advisory, patch, version metadata, or user-provided case label
supports the CVE identity, the agent should report the finding as a localized
parser OOB candidate with uncertain CVE identity.

## Research Meaning

This is the first manual example of a validator-backed skill revision:

```text
case-level validation -> skill-level feedback -> gate decision -> skill revision
```

The revision does not claim that the skill is promoted. It addresses a measured
failure mode: good localization but weak CVE calibration.
