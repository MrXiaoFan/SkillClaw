# Paper Idea Draft - 2026-07-01

## Working Title Options

1. **Verifiable Skill Evolution for Vulnerability Localization and Confirmation**
2. **From Trajectory-Driven to Validator-Grounded Skill Evolution for Vulnerability Analysis Agents**
3. **Dimension-Aware Skill Evolution for Vulnerability Confirmation**

## Problem

Existing skill-evolution systems such as `SkillClaw` mainly improve shared
skills from conversation trajectories and session summaries. This works for
collecting experience, but it leaves a key gap for vulnerability-analysis
tasks: a model may appear successful in natural-language reasoning while still
failing on exact CVE attribution or reproducible vulnerability confirmation.

In our experiments, this gap appears clearly in `libxml2`: `SkillClaw` could
localize the right file/function/root cause, yet still overclaim neighboring
CVEs. This means that whole-task success or conversation-level summaries are
too coarse to drive reliable skill revision for vulnerability work.

## Main Idea

We extend `SkillClaw` into a **validator-grounded, dimension-aware, auditable
skill-evolution framework** for vulnerability tasks.

The core change is to replace purely trajectory-driven revision signals with
structured feedback built from:

- benchmark cases,
- external validators,
- skill-level evidence aggregation,
- revision gates,
- revision templates,
- and evidence-cited skill history.

Instead of asking only whether a run was "good" or "bad", we separately track:

- localization success,
- evidence quality,
- root-cause quality,
- exact CVE calibration,
- artifact generation,
- artifact execution,
- and dynamic confirmation status.

## Method

Our system adds four layers on top of baseline `SkillClaw`:

1. **Case-driven execution**
   - vulnerability cases define target software, ground truth, prompts,
     validators, expected artifacts, and confirmation procedures.

2. **Validator-grounded assessment**
   - multi-mode validators check final answers, source locations, commands,
     bundle scripts, ASan outputs, artifact existence, and artifact execution.

3. **Dimension-aware skill feedback**
   - run-level results are aggregated into skill-level evidence and converted
     into gate decisions such as `promote`, `keep`, `revise`, or `demote`.
   - failures such as `cve_calibration_miss` are promoted to first-class
     revision targets instead of being hidden by an overall score.

4. **Auditable skill revision**
   - revision bundles, templates, and playbooks are injected into the evolve
     workspace.
   - each skill revision records its evidence source, gate, directives, and
     revision scope in versioned history files.

## Current Findings

### Finding 1: skill-task alignment is a dominant variable

On open-ended vulnerability tasks, relevant skills can meaningfully improve
search-path convergence; irrelevant skills can create analytical drift.

### Finding 2: localization and exact CVE attribution are separable

On `libxml2-2.9.4-cve-2017-8872`, the baseline SkillClaw run correctly localized
`HTMLparser.c / htmlParseTryOrFinish` but failed exact-CVE calibration by
enumerating neighboring libxml2 CVEs. This justified a new failure type:
`cve_calibration_miss`.

### Finding 3: template-driven revision can improve the failed dimension

After introducing a revision template that explicitly separates localization
from exact CVE attribution, a later `libxml2` rerun reached a clean `10/10`
result with exact `CVE-2017-8872`, while preserving the correct
file/function/root-cause target.

### Finding 4: confirmation-oriented evaluation is feasible

On `giflib`, the extended framework successfully validated:

- generated trigger artifact,
- executable repro script / artifact execution,
- ASan-based dynamic confirmation.

This shows that the framework can evaluate vulnerability confirmation, not only
textual localization quality.

## Draft Contributions

1. **A validator-grounded skill-evolution extension for vulnerability tasks**
   that augments `SkillClaw` with case execution, validation, feedback gating,
   and revision bundles.

2. **A dimension-aware feedback model**
   that separates localization quality from exact CVE calibration and
   confirmation-oriented signals such as artifact generation/execution.

3. **An auditable revision workflow**
   where each skill change is tied to explicit evidence, templates, and versioned
   rationale instead of opaque prompt edits.

4. **Empirical evidence from historical CVE benchmarks**
   showing both:
   - a confirmation-success case (`giflib`), and
   - a targeted revision-success case (`libxml2`).

## Best Current Paper-Safe Claim

> For vulnerability-analysis tasks, conversation summaries alone are too coarse
> to guide reliable skill evolution. Validator-grounded, dimension-aware
> feedback can preserve correct localization behavior while improving failed
> dimensions such as exact-CVE calibration and vulnerability confirmation.

## What We Still Need Before Writing In Earnest

1. one more rerun with shared injection logging preserved end to end,
2. a compact experiment table spanning `tcpdump`, `libxml2`, and `giflib`,
3. a short method figure that shows:
   `run -> validate -> aggregate -> gate -> revise -> rerun`.
