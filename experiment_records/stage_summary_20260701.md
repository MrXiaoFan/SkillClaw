# Stage Summary - 2026-07-01

## What We Have Now

The current repository is no longer just a modified `SkillClaw` proxy. It now
contains a working prototype for **validator-grounded skill evolution** with a
new emphasis on **vulnerability confirmation**.

## Engineering State

### 1. Experiment execution is structured

We can run benchmarked cases through:

- prompt generation,
- guarded agent execution,
- scoring,
- validator checks,
- final-record assembly,
- skill-level feedback aggregation.

### 2. Validation is multi-mode

The framework now supports:

- `content_match`
- `source_contains`
- `command`
- `bundle_script`
- `asan_command`
- `artifact_exists`
- `artifact_exec`

This means we can validate not only textual localization quality, but also
artifact generation and confirmation behavior.

### 3. Feedback reaches the evolver

We now generate:

- `skill_feedback_latest.*`
- `skill_gate_report_latest.*`
- `skill_feedback_bundle_latest.*`

and inject bundle, summary, and playbook artifacts into the evolve workspace.

### 4. Skill revision is auditable

Each skill revision can now carry:

- a version note,
- evidence note,
- gate decision,
- revision template reference,
- and an explicit explanation of what was changed and why.

## Experimental State

### giflib

`giflib` has already become a successful **confirmation pipeline** case:

- artifact generated,
- artifact executed,
- ASan confirmation passed.

This shows that the framework can move beyond pure localization and into
repro/confirmation.

### libxml2

`libxml2` is now the stronger **revision-study case**:

- baseline localized correctly but overclaimed many CVEs,
- revised run exposed `cve_calibration_miss`,
- template-driven rerun produced a clean `10/10` exact-CVE hit.

## Research State

The current strongest idea is:

> skill evolution for vulnerability tasks should not rely only on trajectory or
> conversation summaries; it should rely on validator-grounded, dimension-aware,
> auditable feedback.

The project now has evidence for all three parts:

- **validator-grounded**: external checks and confirmation pipeline exist,
- **dimension-aware**: localization and CVE calibration are explicitly split,
- **auditable**: revision history and evidence notes are recorded.

## What Is Still Missing

The main gap is not framework capability anymore; it is **synchronized evidence
quality**:

1. one more rerun that preserves shared injection logging end to end,
2. a cleaner paper-ready comparison table across cases,
3. a concise narrative that links giflib confirmation and libxml2 revision into
   one coherent paper contribution.
