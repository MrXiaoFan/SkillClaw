# Paper Outline Draft - 2026-07-01

## 1. Introduction

### 1.1 Motivation

- shared skill libraries are attractive for agent systems
- but vulnerability-analysis tasks require stronger evidence than generic task
  completion
- conversation summaries can hide important failure modes such as:
  - correct localization + wrong CVE
  - plausible reasoning + no reproducible confirmation

### 1.2 Key Observation

- on `libxml2`, SkillClaw can localize correctly but still overclaim CVEs
- on `giflib`, confirmation artifacts and ASan signals provide much harder
  evidence than answer text alone

### 1.3 Main Thesis

skill evolution for vulnerability tasks should be:

- validator-grounded,
- dimension-aware,
- auditable.

## 2. Background and Limitation of Baseline SkillClaw

### 2.1 Baseline pipeline

- session trajectory
- summarizer
- evolver
- skill rewrite

### 2.2 Limitation

- little external validation
- weak distinction between localization and attribution
- weak audit trail for why a skill changed

## 3. System Design

### 3.1 Case-driven benchmark layer

- target
- prompt
- validators
- expected artifacts
- repro commands

### 3.2 Validator layer

- `content_match`
- `source_contains`
- `command`
- `bundle_script`
- `asan_command`
- `artifact_exists`
- `artifact_exec`

### 3.3 Feedback layer

- score aggregation
- skill-level statistics
- gates
- revision directives
- revision templates

### 3.4 Auditable evolve layer

- feedback bundle in workspace
- summary
- playbook
- `history/vN_evidence.md`

## 4. Dimension-Aware Feedback Model

Suggested dimensions:

- localization
- evidence
- root cause
- exact CVE calibration
- artifact generated
- artifact executed
- dynamic confirmation passed

Introduce:

- `cve_calibration_miss`

as a first-class failure mode.

## 5. Experiments

### 5.1 RQ1: Does skill-task alignment matter?

Use:
- `tcpdump`
- early `libxml2`

### 5.2 RQ2: Can validator-grounded revision improve the failed dimension?

Use:
- `libxml2`
- baseline vs revised vs template-driven rerun

### 5.3 RQ3: Can the framework support vulnerability confirmation?

Use:
- `giflib`
- artifact generation / execution / ASan confirmation

## 6. Main Results To Highlight

### 6.1 libxml2

- baseline SkillClaw: strong localization, wrong CVE overclaim
- revised run: `cve_calibration_miss` surfaced explicitly
- template-driven rerun: clean exact `CVE-2017-8872`

### 6.2 giflib

- confirmation pipeline works end to end
- artifact-aware evaluation is practical

## 7. Discussion

### 7.1 What this work is not

- not zero-day exploitation
- not model fine-tuning
- not a claim that SkillClaw always beats direct LLM use

### 7.2 What this work shows

- better feedback shape matters
- exact vulnerability confirmation needs stronger evidence than conversation
  success

## 8. Limitations

- still small benchmark set
- one local rerun currently uses sharing-disabled isolation
- shared-pool synchronized confirmation needs one more clean rerun

## 9. Conclusion

Move from:

- trajectory-driven skill evolution

to:

- validator-grounded, dimension-aware, auditable skill evolution for
  vulnerability localization and confirmation.
