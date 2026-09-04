# 03. Experiment Index and Key Results

This file tells a future writer which experiment files are main evidence and which are
supporting evidence.

The copied tables and markdown reports are the first-stop evidence. If a later writer
needs the raw per-run JSON, those original artifact paths can usually be recovered from
the copied CSV/JSON summaries here, especially `closed_loop_proof.csv`,
`core_benchmarks.csv`, and the frozen/clean rerun tables.

## A. Early source-code closed-loop proof

Purpose:

- show that the end-to-end engineering chain exists;
- not the strongest evidence for firmware-skill necessity.

Key files:

- [reports/current/briefing_20260805/closed_loop_proof.csv](../../../reports/current/briefing_20260805/closed_loop_proof.csv)
- [reports/current/briefing_20260805/core_benchmarks.csv](../../../reports/current/briefing_20260805/core_benchmarks.csv)

What they support:

- remote run records can be finalized, handed off, consumed, and queued for candidate
  generation/gate;
- the repository is not just a static prompt collection.

## B. Early firmware ablation on wireless/login

Purpose:

- early evidence that different skill conditions can change blind-analysis behavior.

Key files:

- [reports/current/briefing_20260805/firmware_skill_ablation_summary.md](../../../reports/current/briefing_20260805/firmware_skill_ablation_summary.md)
- [reports/current/briefing_20260805/firmware_ablation_summary.csv](../../../reports/current/briefing_20260805/firmware_ablation_summary.csv)
- [reports/current/briefing_20260805/firmware_ablation_runs.csv](../../../reports/current/briefing_20260805/firmware_ablation_runs.csv)

Representative result:

- `firmware2-wireless-cgi-cve-2026-2529`: `none 2.67`, `wrong 3.00`, `relevant 3.00`,
  `seed 4.00`
- `firmware2-login-cgi-cve-2026-2527`: `none 4.33`, `wrong 4.50`, `relevant 5.00`,
  `seed 5.00`

What they support:

- skill choice changes model behavior;
- early evidence, but not the cleanest necessity proof.

## C. F453 drift study

Purpose:

- show that the model can land on a dangerous path yet still drift to the wrong target
  function within the same firmware family.

Key files:

- [reports/current/briefing_20260815/f453_skill_ablation_20260815.md](../../../reports/current/briefing_20260815/f453_skill_ablation_20260815.md)
- [reports/current/briefing_20260815/f453_run_table_20260815.csv](../../../reports/current/briefing_20260815/f453_run_table_20260815.csv)

What they support:

- high score can still correspond to the wrong function;
- this is why later scoring/feedback needed to distinguish target-function identity
  misses.

## D. Clean rerun necessity study, phase A

Purpose:

- rerun under cleaner conditions after discovering earlier leakage/over-strong oracle
  prompts.

Key files:

- [reports/current/briefing_20260816/planA_clean_rerun_validation_20260820.md](../../../reports/current/briefing_20260816/planA_clean_rerun_validation_20260820.md)
- [reports/current/briefing_20260816/planA_clean_rerun_table_20260820.csv](../../../reports/current/briefing_20260816/planA_clean_rerun_table_20260820.csv)

Representative aggregate:

| condition | YES | DECOY | NO | mean score |
| --- | ---: | ---: | ---: | ---: |
| no-skill | 1/28 = 3.6% | 9 | 18 | 4.38 |
| weak-skill | 4/28 = 14.3% | 12 | 12 | 4.34 |
| oracle-skill | 10/28 = 35.7% | 1 | 17 | 6.32 |

What they support:

- earlier oracle-like results were too optimistic;
- even after cleanup, a stronger skill condition still materially changes outcomes.

## E. Frozen necessity study, main current evidence

Purpose:

- fixed multi-case firmware necessity experiment on a frozen protocol.

Key files:

- [reports/current/briefing_20260816/plan1_necessity_frozen_validation_20260820.md](../../../reports/current/briefing_20260816/plan1_necessity_frozen_validation_20260820.md)
- [reports/current/briefing_20260816/plan1_necessity_frozen_table_20260820.csv](../../../reports/current/briefing_20260816/plan1_necessity_frozen_table_20260820.csv)
- [reports/current/briefing_20260816/plan1_necessity_attribution_20260820.md](../../../reports/current/briefing_20260816/plan1_necessity_attribution_20260820.md)
- [reports/current/briefing_20260816/plan1_necessity_attribution_20260820.csv](../../../reports/current/briefing_20260816/plan1_necessity_attribution_20260820.csv)

Representative aggregate:

| condition | YES | DECOY | NO | mean score |
| --- | ---: | ---: | ---: | ---: |
| no-skill | 3/45 = 6.7% | 28 | 14 | 3.92 |
| weak-skill | 5/45 = 11.1% | 24 | 16 | 3.99 |
| oracle-skill | 21/45 = 46.7% | 2 | 22 | 6.20 |

What they support:

- the strongest current evidence that skill content can matter a lot in blind firmware
  localization;
- still not proof that the full system has already achieved autonomous skill
  self-improvement.

## F. Family-internal distinguishing experiments

Purpose:

- test whether a more discriminative family-specific skill can prevent drift to nearby
  wrong handlers.

Key files:

- F9K positive result:
  - [reports/current/briefing_20260816/f9k_distinguishing_validation_20260820.md](../../../reports/current/briefing_20260816/f9k_distinguishing_validation_20260820.md)
  - [reports/current/briefing_20260816/f9k_distinguishing_run_table_20260820.csv](../../../reports/current/briefing_20260816/f9k_distinguishing_run_table_20260820.csv)
- FH451 negative result:
  - [reports/current/briefing_20260816/fh451_distinguishing_validation_20260820.md](../../../reports/current/briefing_20260816/fh451_distinguishing_validation_20260820.md)
  - [reports/current/briefing_20260816/fh451_distinguishing_run_table_20260820.csv](../../../reports/current/briefing_20260816/fh451_distinguishing_run_table_20260820.csv)

Representative aggregate:

| family | generic oracle | distinguishing oracle | reading |
| --- | ---: | ---: | --- |
| F9K1122 | 2/10 = 20.0% | 10/15 = 66.7% | positive |
| FH451 | 6/15 = 40.0% | 4/15 = 26.7% | negative |

What they support:

- "more specific skill" is not universally better;
- skill benefit is family-dependent;
- this is directly useful for the paper's discussion section.

## G. Gate and publication evidence

Purpose:

- show that candidate generation, pending-job settlement, and validated publish logic
  are not hypothetical.

Key files:

- [reports/current/briefing_20260816/gate_settle_20260820.md](../../../reports/current/briefing_20260816/gate_settle_20260820.md)
- [reports/current/skill_gate.md](../../../reports/current/skill_gate.md)
- [reports/current/skill_gate.json](../../../reports/current/skill_gate.json)
- [reports/current/skill_feedback_bundle.md](../../../reports/current/skill_feedback_bundle.md)
- [reports/current/skill_feedback_bundle.json](../../../reports/current/skill_feedback_bundle.json)

What they support:

- the engineering path into gate and publish exists;
- they do not, by themselves, prove that published skills improve future blind runs.

## H. Current best use in the paper

Use as main evidence:

1. frozen necessity study;
2. F9K positive family-specific result;
3. FH451 negative family-specific result;
4. attribution study;
5. gate/publication discussion as a systems limitation and research challenge.

Use as supporting context:

1. source-code closed-loop proof;
2. wireless/login early firmware ablation;
3. F453 drift study.

## I. Server-catalog selection diagnostic (2026-09-03)

The server-side catalog path is operational and now records selector traces through the final
artifact. A controlled F9K WlanSetup diagnostic compared selector guard iterations:

- prompt-only v2: first-turn selection remained the nearby command-injection skill;
- v3 family guard: excluded that skill but over-selected three overlapping CWE-120 tools;
- focused v4 guard: selected only `elf-cwe120-firmware-triage`, with scores `4.5/2.0/4.5`
  (mean `3.67/10`), function/evidence hits in 2/3 runs, and CVE hits in 0/3 runs.

This is evidence of an auditable server-side selection improvement, not evidence of stable
end-to-end effectiveness. It should be used as a limitation/diagnostic result until the same
protocol is evaluated on a frozen multi-case set. The full records are indexed in
[the catalog diagnostics](../../../reports/current/briefing_20260902/README.md).
