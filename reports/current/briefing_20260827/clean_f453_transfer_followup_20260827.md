# Clean F453 Transfer Follow-up (2026-08-27)

## 1. What was run

This round used a strict source-to-transfer setup inside the F453 `httpd`
family.

Source case:

- `benchmarks/cases/f453-httpd-overflow-formWrlsafeset.json`
- target CVE: `CVE-2026-3273`

Held-out cases:

- `benchmarks/cases/f453-httpd-overflow-fromRouteStatic.json`
- target CVE: `CVE-2026-3166`
- `benchmarks/cases/f453-httpd-overflow-fromqossetting.json`
- target CVE: `CVE-2026-3378`

Conditions per held-out case:

- `no-skill`
- `seed-skill`
- `candidate-skill`

Repeats per condition:

- `3`

## 2. Clean source set

We rebuilt the source set from three fresh remote VM runs with one forced seed
skill:

- forced seed skill: `elf-cwe120-firmware-triage`

Source finals:

- `runtime/imports/remote_vm/clean-f453-wrlsafeset-weak-r1-20260827/clean-f453-wrlsafeset-weak-r1-20260827-final-enriched.json`
- `runtime/imports/remote_vm/clean-f453-wrlsafeset-weak-r2-20260827/clean-f453-wrlsafeset-weak-r2-20260827-final-enriched.json`
- `runtime/imports/remote_vm/clean-f453-wrlsafeset-weak-r3-20260827/clean-f453-wrlsafeset-weak-r3-20260827-final-enriched.json`

Source summary:

| Run | Score | Main wrong target | Quality flags |
| --- | ---: | --- | --- |
| `r1` | `2.0` | `CVE-2018-5767` / `formexeCommand` | `cve_identity_miss`, `function_identity_miss` |
| `r2` | `6.0` | `CVE-2018-5767`, `CVE-2020-10987` / `formexeCommand` | `cve_identity_miss` |
| `r3` | `2.0` | `CVE-2018-5767` / `formexeCommand` | `cve_identity_miss`, `function_identity_miss` |

Important detail:

- this source set did **not** recover the true root cause
- it still passed the current source-quality guard because `r2` mentioned
  `sprintf`, which counted as a function hit under the present scoring logic

## 3. Candidate generation

Candidate artifact:

- `runtime/heldout_experiments/clean_f453_wrlsafeset_source_20260827/candidate_skill.json`

Frozen candidate metadata:

- target skill name: `elf-cwe120-firmware-triage`
- candidate content SHA-256:
  `896abc51082ea08b9a72217479b3b0db2226faaf285c1c56dfed76fc2cc29f02`
- candidate tree SHA-256:
  `31fe3f4887160c4fd2181463acc3e23f67265e3f22070e0d9a75e5293f9a5746`

What the candidate changed:

- it widened the original overflow triage skill into a mixed
  overflow-or-command-injection skill
- it added explicit command-execution markers such as
  `doSystemCmd`, `system`, `exeCommand`, and `/goform`
- it added a rule to avoid naming a CVE unless independent evidence exists

The result is not a neutral edit. It clearly pushes the model toward the Tenda
command-execution family learned from the bad source runs.

## 4. Leakage audit result

Both held-out runs passed the direct leakage audit:

- `runtime/heldout_experiments/clean_f453_wrlsafeset_to_routestatic_20260827/heldout_leakage_audit.json`
- `runtime/heldout_experiments/clean_f453_wrlsafeset_to_qossetting_20260827/heldout_leakage_audit.json`

Both files reported:

- `blocked = false`
- `matched_terms = []`

That means the candidate did not directly mention:

- `fromRouteStatic`
- `fromqossetting`
- `page`
- `qos`

So the transfer failure below is not caused by direct string leakage into the
held-out answers.

## 5. Transfer result: fromRouteStatic

Artifacts:

- `runtime/heldout_experiments/clean_f453_wrlsafeset_to_routestatic_20260827/heldout_results.csv`
- `runtime/heldout_experiments/clean_f453_wrlsafeset_to_routestatic_20260827/heldout_results.json`

Aggregate:

| Condition | Mean score | Function hit | Evidence hit | Root-cause hit | `function_identity_miss` |
| --- | ---: | ---: | ---: | ---: | ---: |
| `no-skill` | `3.667` | `2/3` | `2/3` | `0/3` | `3/3` |
| `seed-skill` | `3.667` | `2/3` | `2/3` | `0/3` | `3/3` |
| `candidate-skill` | `2.000` | `0/3` | `0/3` | `0/3` | `3/3` |

Dominant drift:

- `no-skill` and `seed-skill` sometimes landed on nearby but still wrong
  high-risk handlers
- `candidate-skill` drifted more consistently to
  `formexeCommand` / `doSystemCmd`
- candidate runs often removed the guessed CVE entirely, but still failed to
  recover the true overflow path

## 6. Transfer result: fromqossetting

Artifacts:

- `runtime/heldout_experiments/clean_f453_wrlsafeset_to_qossetting_20260827/heldout_results.csv`
- `runtime/heldout_experiments/clean_f453_wrlsafeset_to_qossetting_20260827/heldout_results.json`

Aggregate:

| Condition | Mean score | Function hit | Evidence hit | Root-cause hit | `function_identity_miss` |
| --- | ---: | ---: | ---: | ---: | ---: |
| `no-skill` | `2.833` | `1/3` | `1/3` | `0/3` | `3/3` |
| `seed-skill` | `2.000` | `0/3` | `0/3` | `0/3` | `3/3` |
| `candidate-skill` | `2.000` | `0/3` | `0/3` | `0/3` | `3/3` |

Dominant drift:

- `no-skill` sometimes wandered to other wireless handlers
- `seed-skill` and `candidate-skill` both collapsed to the same wrong
  `formexeCommand` / `doSystemCmd` family
- candidate runs again failed to produce any true root-cause recovery

## 7. Current conclusion

This round supports three points.

What is supported:

- the isolated source-to-transfer runner works on real remote VM runs
- the candidate can be frozen, hashed, and tested without touching the live
  publish path
- the current candidate is not inert; it changes downstream behavior on unseen
  cases

What is not supported:

- this candidate does not improve either held-out overflow case
- it performs worse than `no-skill` on both held-out cases
- it never recovers the true root cause in any of the six candidate-condition
  runs

In short:

- this is a real negative-transfer example
- the present source-quality guard is still too loose for this family

## 8. Why this round matters

The useful answer here is not "candidate failed once."

The stronger answer is:

- a candidate generated from weak source runs can be frozen cleanly
- it can pass the direct leakage audit
- and it can still hurt held-out performance in a repeatable way

That gives us a concrete engineering target for the next step:

- tighten source eligibility beyond simple function-token overlap
- require stronger root-cause or path-level signal before candidate generation

## 9. Source-quality guard tightened after this run

After this experiment, the held-out runner's source-quality gate was tightened
so that a source set is blocked by default when:

- all source runs have `function_identity_miss`, or
- no source run has `root_cause_hit`

Recheck artifact:

- `runtime/heldout_experiments/clean_f453_wrlsafeset_source_20260827_recheck/source_quality_audit.json`

The same three source records now fail candidate generation with:

- `no_source_run_has_root_cause_hit`

That means this F453 source set is now treated as historical evidence of
negative transfer, not as an eligible source set for future automatic
candidate generation.
