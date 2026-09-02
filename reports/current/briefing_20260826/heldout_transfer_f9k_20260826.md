# F9K1122 Held-out Transfer Experiment (2026-08-26)

## 1. Experiment goal

This experiment asks whether a candidate skill generated from one F9K1122
overflow case can improve a different F9K1122 overflow case that did not
participate in candidate generation.

Unlike the earlier FH451 run, this family is attractive because the historical
weak-skill runs show a more structured failure pattern: several cases are
repeatedly dragged toward the wrong `formWISP5G` / nearby-family explanation.

## 2. Source / held-out setup

Source case:

- `benchmarks/cases/f9k1122-webs-overflow-formCrossBandSwitch.json`
- project: `F9K1122`
- CVE: `CVE-2026-5042`
- target binary: `vul_file/webs`
- target functions: `formCrossBandSwitch`, `strcpy`

Held-out case:

- `benchmarks/cases/f9k1122-webs-overflow-formWlanSetup.json`
- project: `F9K1122`
- CVE: `CVE-2026-5608`
- target binary: `vul_file/webs`
- target functions: `formWlanSetup`, `strcpy`

Why this pair was chosen:

- same firmware family
- same `webs` binary
- same bug class (`buffer_overflow`)
- different vulnerable functions
- both families have enough recent traceable runs for strict source lineage

## 3. Candidate generation

The candidate was built from three real weak-skill source runs:

- `runtime/imports/remote_vm/ablation-f9k1122-crossband-overflow-weak-skill-r1-20260820-221209/...-final.json`
- `runtime/imports/remote_vm/ablation-f9k1122-crossband-overflow-weak-skill-r2-20260820-221232/...-final.json`
- `runtime/imports/remote_vm/ablation-f9k1122-crossband-overflow-weak-skill-r3-20260820-221247/...-final.json`

Manifest and candidate:

- `runtime/heldout_experiments/f9k_crossband_to_wlansetup_20260826/candidate_manifest.json`
- `runtime/heldout_experiments/f9k_crossband_to_wlansetup_20260826/candidate_skill.json`

Source-run profile:

- all three source runs used `elf-cwe120-firmware-triage`
- source scores: `4.5`, `6.0`, `2.0`
- two of three source runs had `function_identity_miss`
- the visible failure pattern was repeated wrong-family / weak-evidence output,
  often drifting around nearby handler families instead of proving exact target
  identity

Candidate content direction:

- unlike the FH451 candidate, this one did not harden a specific wrong handler
  family
- instead it added:
  - mandatory evidence-confirmation checklist
  - stricter CVE-identity rule
  - explicit warning against premature conclusions

In short, this candidate is more about analysis discipline than sink-family
memorization.

## 4. Held-out protocol

Three conditions, each repeated three times:

- `no-skill`
- `seed-skill` (`elf-cwe120-firmware-triage`)
- `candidate-skill`

Total runs: `9`

Execution path:

- runner:
  - `evaluation/runs/run_heldout_evolved_skill.py`
- remote host:
  - `li@192.168.1.4`
- result directory:
  - `runtime/heldout_experiments/f9k_crossband_to_wlansetup_20260826/`
- leakage audit:
  - `runtime/heldout_experiments/f9k_crossband_to_wlansetup_20260826/heldout_leakage_audit.json`

Audit result:

- `blocked = false`
- `matched_terms = []`

## 5. Main results

Per-run files:

- `runtime/heldout_experiments/f9k_crossband_to_wlansetup_20260826/heldout_results.json`
- `runtime/heldout_experiments/f9k_crossband_to_wlansetup_20260826/heldout_results.csv`

Aggregate summary:

| Condition | Runs | Mean score | function_identity_miss | evidence_hit |
| --- | ---: | ---: | ---: | ---: |
| no-skill | 3 | 2.0 | 3/3 | 0/3 |
| seed-skill | 3 | 2.0 | 3/3 | 0/3 |
| candidate-skill | 3 | 3.67 | 3/3 | 2/3 |

Per-run scores:

| Condition | r1 | r2 | r3 |
| --- | ---: | ---: | ---: |
| no-skill | 2.0 | 2.0 | 2.0 |
| seed-skill | 2.0 | 2.0 | 2.0 |
| candidate-skill | 4.5 | 4.5 | 2.0 |

Representative wrong targets:

| Condition | Typical drift |
| --- | --- |
| no-skill | `formSetupTools`, `formexeCommand`, `formSetSystemSettings` |
| seed-skill | `BS_ping_ip`, `formSetSystemSettings`, `system`, `goform` |
| candidate-skill | `formBBSWlSetting`, `netNameScan`, `formMP` |

## 6. Interpretation

This second held-out experiment is more encouraging than FH451, but still not
enough to claim successful transfer.

What improved:

- candidate-skill raised mean score from `2.0` to `3.67`
- candidate-skill improved `evidence_hit` from `0/3` to `2/3`
- candidate-skill stopped some of the cruder weak-skill failures and pushed the
  model toward richer binary-level evidence

What did not improve enough:

- all 3 runs still ended in `function_identity_miss`
- `cve_hit = 0/3`
- `root_cause_hit = 0/3`
- the candidate changed the shape of the wrong answer, but did not recover the
  true held-out vulnerable function

Plain-language conclusion:

- this candidate is not useless
- it appears to improve evidence quality and suppress the weakest failure modes
- but it still does not cross the line from "better reasoning" to "correct
  vulnerable-function identification"

## 7. Comparison to the first FH451 held-out result

The first FH451 experiment and this F9K1122 experiment fail in different ways:

- FH451 candidate:
  - reinforced or redirected drift into wrong Tenda command-execution families
  - no measurable held-out gain
- F9K1122 candidate:
  - improved evidence quality on 2 of 3 runs
  - still failed to reach the correct handler identity

This suggests the current evolution pipeline is not purely random noise:

- some candidates can change analysis behavior in a useful direction
- but the present gate / feedback recipe still does not guarantee handler-level
  transfer success on unseen cases

## 8. Practical takeaway

After two strict held-out experiments, the strongest current statement is:

- the engineering pipeline for strict held-out evolved-skill evaluation now
  works
- the current candidate-generation mechanism can influence future blind runs
- but we do not yet have evidence that evolved candidates reliably improve
  target-function correctness on unseen tasks
