# Strict Held-Out Transfer: F9K1122 `formCrossBandSwitch` -> `formSetSystemSettings`

## 1. Experiment goal

This run reuses the evolved candidate from source case
`f9k1122-webs-overflow-formCrossBandSwitch` and applies it to a different blind
task:

- held-out case: `f9k1122-webs-overflow-formSetSystemSettings`
- held-out CVE: `CVE-2026-5044`
- binary: `vul_file/webs`

The purpose is to check whether the candidate improves a future task that did
not participate in candidate generation.

## 2. Conditions

We compared:

- `no-skill`
- `seed-skill` using `elf-cwe120-firmware-triage`
- `candidate-skill` using the evolved candidate

Each condition was repeated 3 times on the remote VM.

## 3. Leakage audit

Leakage audit passed:

- `runtime/heldout_experiments/f9k_crossband_to_setsystemsettings_20260826/heldout_leakage_audit.json`

No blocked terms were reported.

## 4. Aggregate result

| Condition | Mean score | Function hit | Evidence hit | Root-cause hit | `function_identity_miss` |
| --- | ---: | ---: | ---: | ---: | ---: |
| `no-skill` | 5.50 | 3/3 | 3/3 | 0/3 | 1/3 |
| `seed-skill` | 5.50 | 3/3 | 3/3 | 0/3 | 1/3 |
| `candidate-skill` | 5.00 | 3/3 | 3/3 | 0/3 | 2/3 |

Primary data:

- `runtime/heldout_experiments/f9k_crossband_to_setsystemsettings_20260826/heldout_results.json`
- `runtime/heldout_experiments/f9k_crossband_to_setsystemsettings_20260826/heldout_results.csv`

## 5. Interpretation

This case is different from `WlanSetup` and `WISP5G`:

- all three conditions already landed on the correct handler region
- the candidate did not add evidence that was missing from baseline
- the candidate was slightly worse on average score

So this run should not be treated as positive transfer.

The better reading is:

- this held-out task is already relatively easy at the function level
- the candidate does not help convert that function-level success into correct
  root-cause reasoning
- in one more repeat than baseline, the candidate drifted into
  `function_identity_miss`

## 6. Why this run matters

This experiment prevents us from over-claiming based only on the more positive
`WlanSetup` and `WISP5G` outcomes.

It shows that even inside the same firmware family and same `webs` binary:

- transfer is not uniformly positive
- an evolved candidate can improve some unseen tasks and fail to help others

That is an important constraint on any later "publish to live skill library"
policy.
