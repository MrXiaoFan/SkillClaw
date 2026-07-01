## libxml2 Revision Rerun Plan - 2026-07-01

### Objective

Run the next `libxml2` experiment as a **template-driven revision rerun** for
`source-parser-state-machine-oob`, rather than as a generic SkillClaw replay.

### Target Skill

- `source-parser-state-machine-oob`

### Target Case

- `libxml2-2.9.4-cve-2017-8872`

### Revision Input Pack

- JSON:
  `experiment_records/libxml2_source_parser_revision_bundle_20260701.json`
- Markdown:
  `experiment_records/libxml2_source_parser_revision_bundle_20260701.md`

### Why This Pack

The filtered bundle removes unrelated positive `giflib` confirmation evidence
and isolates the `libxml2` parser-state-machine signal:

- selected runs: `2`
- mean score: `0.8`
- localization success: `2`
- cve success: `0`
- cve calibration miss: `1`
- validator passed: `2`

This makes it a cleaner revision input than the global `latest` bundle.

### Revision Focus

The rerun should preserve:

- parser-state variable tracing,
- guard-dominance reasoning,
- lookahead/`avail` source localization.

The rerun should revise only:

- exact CVE attribution behavior,
- uncertainty handling when localization is strong but advisory-level evidence
  is missing.

### Expected Improvement

The next revised run does **not** need to beat the direct baseline on every
dimension. The minimum acceptable improvement is:

1. no regression in file/function/root-cause localization,
2. reduced CVE overclaiming,
3. explicit `candidate/uncertain` behavior when exact CVE evidence is missing.

### Comparison Targets

Use these prior records for before/after comparison:

- `experiment_records/libxml2-skillclaw-final-with-injection-20260623.json`
- `experiment_records/libxml2-skillclaw-revised-final-20260628.json`

### Next Operational Step

Feed the filtered revision pack into the next evolve/revision run for
`source-parser-state-machine-oob`, then rerun the `libxml2` case and compare:

- `localization_success`
- `cve_calibration_miss`
- `predicted_cves`
- `feedback.decision`
- validator status
