# Strict Held-Out Transfer: F9K1122 `formCrossBandSwitch` -> `formWISP5G`

## 1. Experiment goal

This run tests whether an automatically evolved candidate skill can improve a
different blind firmware task that did not participate in candidate generation.

Source side:

- source case: `f9k1122-webs-overflow-formCrossBandSwitch`
- source CVE: `CVE-2026-5042`
- source binary: `vul_file/webs`

Held-out side:

- held-out case: `f9k1122-webs-overflow-formWISP5G`
- held-out CVE: `CVE-2026-4566`
- held-out binary: `vul_file/webs`

The candidate was reused from:

- `runtime/heldout_experiments/f9k_crossband_to_wlansetup_20260826/candidate_skill.json`

This means the held-out task remained outside:

- candidate generation
- replay gate
- source feedback construction

## 2. Conditions

We ran 9 remote blind runs on the VM:

- `no-skill`
- `seed-skill` using `elf-cwe120-firmware-triage`
- `candidate-skill` using the evolved candidate

Each condition was repeated 3 times.

## 3. Leakage audit

Leakage audit passed:

- file: `runtime/heldout_experiments/f9k_crossband_to_wisp5g_20260826/heldout_leakage_audit.json`
- result: `blocked=false`, `matched_terms=[]`

## 4. Aggregate result

| Condition | Mean score | Function hit | Evidence hit | Root-cause hit | `function_identity_miss` |
| --- | ---: | ---: | ---: | ---: | ---: |
| `no-skill` | 2.83 | 1/3 | 1/3 | 0/3 | 3/3 |
| `seed-skill` | 2.83 | 1/3 | 1/3 | 0/3 | 3/3 |
| `candidate-skill` | 4.50 | 3/3 | 3/3 | 0/3 | 3/3 |

Primary data:

- `runtime/heldout_experiments/f9k_crossband_to_wisp5g_20260826/heldout_results.json`
- `runtime/heldout_experiments/f9k_crossband_to_wisp5g_20260826/heldout_results.csv`

## 5. What changed

Compared with both `no-skill` and `seed-skill`, the evolved candidate produced
a clear behavior shift:

- all 3 candidate runs landed on the correct held-out vulnerable function
- all 3 candidate runs preserved evidence-level support
- baseline conditions only reached that level once each

So this is not a "no effect" candidate. It materially changes future blind
analysis on an unseen task from the same firmware family.

## 6. What did not improve

Despite the stronger handler-level focus, the candidate still did not recover
the correct vulnerability explanation:

- `root_cause_hit = 0/3`
- `function_identity_miss = 3/3`

In practice, the model was pulled closer to the correct handler region, but it
still explained the bug through neighboring wrong functions or wrong overflow
stories.

## 7. Current interpretation

This is the strongest positive transfer signal we have so far, but it is still
not enough for the stronger claim that:

- evolved skills already improve unseen tasks in a publish-safe way

What we can say from this run is narrower and more precise:

- the current evolution pipeline can produce a candidate that transfers across
  unseen tasks in the same firmware family
- the transfer currently improves function-level targeting and evidence
  gathering more reliably than root-cause correctness

## 8. Why this run matters

Together with the earlier F9K1122 results, this experiment suggests the
current candidate is learning something real about the `webs` handler family,
not merely memorizing the original source case.

But the missing step is still the same:

- the pipeline can move the model toward the right region
- it cannot yet stably convert that into correct root-cause identification
