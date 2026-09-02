# Clean F9K Transfer Follow-up (2026-08-27)

## 1. What was run

This round used a stricter source-to-transfer setup for the F9K `webs` family.

Source case:

- `benchmarks/cases/f9k1122-webs-overflow-formCrossBandSwitch.json`
- target CVE: `CVE-2026-5042`

Held-out cases:

- `benchmarks/cases/f9k1122-webs-overflow-formWlanSetup.json`
- `benchmarks/cases/f9k1122-webs-overflow-formWISP5G.json`

Conditions per held-out case:

- `no-skill`
- `seed-skill`
- `candidate-skill`

Repeats per condition:

- `3`

## 2. Clean source set

We first rebuilt the source set with three new remote runs that used the VM path
profile explicitly, so the blind workspace lived under:

- `/home/li/skillclaw-eval/blind_workspaces/workspace-c5b3c271f2f0`

instead of the earlier mistaken repo-nested path.

Source finals:

- `runtime/imports/remote_vm/clean-f9k-crossband-weak-r1-20260827/clean-f9k-crossband-weak-r1-20260827-final-enriched.json`
- `runtime/imports/remote_vm/clean-f9k-crossband-weak-r2-20260827/clean-f9k-crossband-weak-r2-20260827-final-enriched.json`
- `runtime/imports/remote_vm/clean-f9k-crossband-weak-r3-20260827/clean-f9k-crossband-weak-r3-20260827-final-enriched.json`

All three source runs:

- selected the same forced seed skill: `elf-cwe120-firmware-triage`
- stayed on the same clean blind workspace path
- ended with `function_identity_miss`

Their main wrong targets were:

- `CVE-2016-1555` / `mp_handler`
- `CVE-2014-7868` / `formSetWanMacAddr`
- `CVE-2018-5767` / `formWanPingBlocking`

## 3. Candidate generation

Candidate artifact:

- `runtime/heldout_experiments/clean_f9k_crossband_source_20260827/candidate_skill.json`

Frozen candidate metadata:

- target skill name: `elf-cwe120-firmware-triage`
- candidate content SHA-256:
  `455e67196bcbb397abc6afa76e81f0c200dc0baa9ae81f486dfe0626f9e14ab6`
- candidate tree SHA-256:
  `34d5585b4b00d649bde2adf53288bb199c3cdf56ecbc410c931add95cdcc9e54`

Important observation:

- the generated candidate added embedded-web command-injection triage rules
- it also introduced concrete handler examples such as
  `formSetSystemSettings`
- because of that, `formSetSystemSettings` is not suitable as a held-out case
  for this candidate

## 4. Leakage audit result

Both transfer runs passed the direct leakage audit:

- `runtime/heldout_experiments/clean_f9k_crossband_to_wlansetup_20260827/heldout_leakage_audit.json`
- `runtime/heldout_experiments/clean_f9k_crossband_to_wisp5g_20260827/heldout_leakage_audit.json`

Both files reported:

- `blocked = false`
- `matched_terms = []`

That means the candidate did not directly mention:

- `formWlanSetup`
- `formWISP5G`

## 5. Transfer result: WlanSetup

Artifacts:

- `runtime/heldout_experiments/clean_f9k_crossband_to_wlansetup_20260827/heldout_results.csv`
- `runtime/heldout_experiments/clean_f9k_crossband_to_wlansetup_20260827/heldout_results.json`

Aggregate:

| Condition | Mean score | Function hit | Evidence hit | Root-cause hit | `function_identity_miss` |
| --- | ---: | ---: | ---: | ---: | ---: |
| `no-skill` | 3.667 | 2/3 | 2/3 | 0/3 | 3/3 |
| `seed-skill` | 3.667 | 2/3 | 2/3 | 0/3 | 3/3 |
| `candidate-skill` | 2.000 | 0/3 | 0/3 | 0/3 | 3/3 |

Dominant drift:

- `candidate-skill` drifted repeatedly to `/goform/mp`-style command injection
- typical wrong outputs mentioned `CVE-2016-1555`, `formMp`, `netNameScan`,
  or `websGetVar -> system`

Interpretation:

- on `formWlanSetup`, this candidate is worse than both baselines
- it carries the source-side command-injection bias into a buffer-overflow task

## 6. Transfer result: WISP5G

Artifacts:

- `runtime/heldout_experiments/clean_f9k_crossband_to_wisp5g_20260827/heldout_results.csv`
- `runtime/heldout_experiments/clean_f9k_crossband_to_wisp5g_20260827/heldout_results.json`

Aggregate:

| Condition | Mean score | Function hit | Evidence hit | Root-cause hit | `function_identity_miss` |
| --- | ---: | ---: | ---: | ---: | ---: |
| `no-skill` | 2.833 | 1/3 | 1/3 | 0/3 | 3/3 |
| `seed-skill` | 2.833 | 1/3 | 1/3 | 0/3 | 3/3 |
| `candidate-skill` | 2.833 | 1/3 | 1/3 | 0/3 | 3/3 |

Dominant drift:

- `candidate-skill` again favored wrong command-injection-style handlers such as
  `formMp`, `formNetbios`, and `/goform/mp`

Interpretation:

- on `formWISP5G`, the candidate does not improve over either baseline
- the candidate is not inert, but its added guidance is not transferring to the
  true target function

## 7. Current conclusion

This round gives a clearer answer than the earlier mixed-path experiments.

What is supported:

- the clean remote blind path fix worked
- the current pipeline can generate a frozen candidate from selected source runs
- the current held-out runner can test `no-skill`, `seed-skill`, and
  `candidate-skill` under the same remote setup
- the current candidate can change downstream analysis behavior on unseen cases

What is not supported:

- this candidate does not improve transfer on the two clean F9K held-out cases
- it does not recover the true root cause on either held-out case
- it still produces `function_identity_miss` in every held-out run

In short:

- the experiment path is now real and reproducible
- the current candidate is a negative transfer example, not a success case

## 8. Source-quality guard added after this run

Because the three clean source runs all ended with `function_identity_miss`, we
added a source-quality audit to candidate generation:

- code: `evaluation/runs/run_heldout_evolved_skill.py`
- test: `tests/test_heldout_evolved_skill_runner.py`

New default behavior:

- if all source runs have `function_identity_miss`, candidate generation is
  blocked
- if no source run has `root_cause_hit`, candidate generation is also blocked
- the block can still be overridden explicitly with
  `--allow-source-quality-risk`

Verification artifact:

- `runtime/heldout_experiments/clean_f9k_crossband_source_20260827_blockcheck/source_quality_audit.json`

That audit recorded:

- `source_run_count = 3`
- `function_identity_miss_count = 3`
- `root_cause_hit_count = 0`
- `blocked = true`

So this source set would no longer be accepted by default for future evolution.

## 9. Useful next step

The next sensible move is not to widen the candidate again, but to change what
kind of source set is allowed to produce a candidate. Right now, three source
runs with the same weak seed skill were enough to teach the pipeline a strong
command-injection bias even though the source task was a buffer-overflow case.
