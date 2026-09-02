# F9K Held-Out Source-Selection Follow-up (2026-08-27)

## 1. Why we ran this follow-up

The first four strict held-out experiments showed a repeated pattern:

- the evolved candidate was not inert
- it sometimes improved function-level targeting on unseen F9K tasks
- but it never achieved correct root-cause recovery

That raised a concrete engineering question:

- is the candidate being weakened by mixed-quality source sessions?

To test that, we kept the same source case family and same held-out protocol,
but changed only the source-session set used to generate the candidate.

## 2. Source-selection variants

Source case for all variants:

- `f9k1122-webs-overflow-formCrossBandSwitch`
- CVE: `CVE-2026-5042`

Variants:

| Variant | Source sessions used | Result |
| --- | --- | --- |
| original candidate | `r1 + r2 + r3` | candidate generated |
| clean-only candidate | `r2` only | evolve returned `skip` |
| reduced candidate | `r1 + r2` | candidate generated |

Artifacts:

- clean-only attempt:
  - `runtime/heldout_experiments/f9k_crossband_cleanr2_to_wisp5g_20260827/`
- reduced candidate:
  - `runtime/heldout_experiments/f9k_crossband_r1r2_to_wisp5g_20260827/`

## 3. What happened

### 3.1 Clean-only source (`r2`) did not produce a candidate

Using only the best source run:

- `ablation-f9k1122-crossband-overflow-weak-skill-r2-20260820-221232`

the evolution pipeline returned:

- `skip`

This means the current generator does not simply reward "cleaner source". It
also appears to need enough cross-run context to decide that a concrete edit is
warranted.

### 3.2 Reduced source (`r1 + r2`) produced a different candidate

Using two source runs:

- `r1` with `function_identity_miss`
- `r2` without that flag

the pipeline generated a new candidate:

- tree hash: `9b8d87d0b2594bd68080ab4110b395e2895cb1b7bd1d8411c05a110435870141`

This candidate was different from the earlier three-session candidate:

- old candidate tree hash:
  `fc79f1b0dfbe39bf16210c83fcc57785ac1fdb5fac7ea658dc17e51b95d4246a`

### 3.3 Strict held-out on `WISP5G` was blocked by leakage audit

When the new `r1 + r2` candidate was checked against:

- `f9k1122-webs-overflow-formWISP5G`
- `CVE-2026-4566`

the leakage audit blocked the run because the candidate text explicitly
included:

- `formWISP5G`

This is useful evidence, not a failed side detail:

- the stricter held-out protocol is doing real work
- candidate wording can cross the line from reusable guidance into direct
  task-specific leakage

## 4. Runner bug found during rerun

While trying to compare the new candidate against the previously used
`WlanSetup` held-out case, we found a runner bug:

- `run_id` only depended on `case_id + condition + repeat`
- rerunning the same held-out case under a different experiment reused the same
  `session_id` and import paths

This caused invalid zero-score rows and partial confirmations in the first
rerun attempt.

Fix applied:

- `evaluation/runs/run_heldout_evolved_skill.py`
- `tests/test_heldout_evolved_skill_runner.py`

The fix adds an experiment namespace to held-out `run_id`, so repeated
experiments on the same case no longer collide.

Validation:

- `python -m py_compile evaluation/runs/run_heldout_evolved_skill.py`
- `pytest -q tests/test_heldout_evolved_skill_runner.py`
- result: `4 passed`

## 5. Clean rerun on `WlanSetup`

After fixing run-id namespacing, we reran the reduced-source candidate on:

- held-out case: `f9k1122-webs-overflow-formWlanSetup`
- held-out CVE: `CVE-2026-5608`

Output:

- `runtime/heldout_experiments/f9k_crossband_r1r2_to_wlansetup_rerun_20260827/`

## 6. Comparison on the same held-out task

### Original three-session candidate (`r1 + r2 + r3`)

Data:

- `runtime/heldout_experiments/f9k_crossband_to_wlansetup_20260826/heldout_results.json`

Aggregate:

| Condition | Mean score | Function hit | Evidence hit | `function_identity_miss` |
| --- | ---: | ---: | ---: | ---: |
| `no-skill` | 2.00 | 0/3 | 0/3 | 3/3 |
| `seed-skill` | 2.00 | 0/3 | 0/3 | 3/3 |
| `candidate-skill` | 3.67 | 2/3 | 2/3 | 3/3 |

### Reduced two-session candidate (`r1 + r2`)

Data:

- `runtime/heldout_experiments/f9k_crossband_r1r2_to_wlansetup_rerun_20260827/heldout_results.json`

Aggregate:

| Condition | Mean score | Function hit | Evidence hit | `function_identity_miss` |
| --- | ---: | ---: | ---: | ---: |
| `no-skill` | 3.67 | 2/3 | 2/3 | 3/3 |
| `seed-skill` | 3.67 | 2/3 | 2/3 | 3/3 |
| `candidate-skill` | 5.00 | 3/3 | 3/3 | 2/3 |

## 7. Interpretation

This follow-up gives us a sharper conclusion than the earlier four-run matrix.

What it supports:

- source-session selection matters
- a reduced source set can produce a stronger held-out candidate than a noisier
  three-session source set
- the candidate still beats both baseline conditions on the same held-out task

What it still does not support:

- root-cause correctness on unseen tasks
- publish-safe automatic evolution without stronger release criteria

Even the improved two-session candidate still had:

- `root_cause_hit = 0/3`

## 8. Current best takeaway

The current bottleneck is no longer simply "does evolution do anything".

We now have direct evidence that:

1. source selection changes candidate quality;
2. leakage control is necessary because candidate wording can overfit quickly;
3. better candidates can improve held-out function-level targeting;
4. root-cause transfer remains unsolved.
