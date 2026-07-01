---
version: v1
date: 2026-07-01
skill: source-parser-state-machine-oob
---

# v1 Evidence

## Feedback Artifacts Used

- `experiment_records/libxml2_source_parser_revision_bundle_20260701.json`
- `experiment_records/libxml2_source_parser_revision_bundle_20260701.md`
- current workspace `feedback/PLAYBOOK.md` semantics for `revise`

## Gate Decision

- `revise`

## Revision Template

- `cve_calibration_miss`

## Revision Directives Followed

1. Keep useful localization guidance.
2. Separate source localization from exact CVE identity.
3. Require advisory, patch, or version-range evidence before naming an exact CVE.
4. Add an uncertainty fallback instead of speculative CVE overclaiming.

## Scope Control

This revision intentionally does not weaken:

- parser-state variable tracing,
- guard-dominance reasoning,
- lookahead/`avail` localization workflow.

It only revises the exact CVE attribution behavior that previously led to
`cve_calibration_miss` in the filtered `libxml2` evidence pack.
