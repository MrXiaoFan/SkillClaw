# Held-out Transfer Overview (2026-08-26)

This note compares the first four strict held-out evolved-skill experiments.

## 1. Purpose

We wanted to move beyond:

- ordinary blind-run scores
- oracle-skill ablations
- same-task rerun gate

and test a stronger question:

- can a candidate generated from source runs improve a different held-out blind
  task that did not participate in candidate generation?

## 2. Completed experiments

| Experiment | Source case | Held-out case | Candidate type | Outcome |
| --- | --- | --- | --- | --- |
| FH451 | `fh451-httpd-overflow-formQuickIndex` | `fh451-httpd-overflow-formWrlExtraSet` | sink-family correction candidate | negative transfer |
| F9K1122-A | `f9k1122-webs-overflow-formCrossBandSwitch` | `f9k1122-webs-overflow-formWlanSetup` | evidence-discipline candidate | partial improvement, still incorrect |
| F9K1122-B | `f9k1122-webs-overflow-formCrossBandSwitch` | `f9k1122-webs-overflow-formSetSystemSettings` | same candidate reused | neutral to slightly worse |
| F9K1122-C | `f9k1122-webs-overflow-formCrossBandSwitch` | `f9k1122-webs-overflow-formWISP5G` | same candidate reused | strongest function-level transfer, root cause still wrong |

## 3. Result comparison

| Experiment | no-skill mean | seed-skill mean | candidate-skill mean | Candidate function hit | Candidate evidence hit | Candidate root-cause hit |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| FH451 | 3.50 | 3.00 | 3.00 | 0/3 | 3/3 | 0/3 |
| F9K1122-A (`WlanSetup`) | 2.00 | 2.00 | 3.67 | 2/3 | 2/3 | 0/3 |
| F9K1122-B (`SetSystemSettings`) | 5.50 | 5.50 | 5.00 | 3/3 | 3/3 | 0/3 |
| F9K1122-C (`WISP5G`) | 2.83 | 2.83 | 4.50 | 3/3 | 3/3 | 0/3 |

## 4. What these four runs tell us

1. Strict held-out evaluation is now technically runnable:
   - source-session lineage
   - candidate freezing
   - leakage audit
   - remote blind execution
   - held-out result collection

2. Candidate skills are not inert:
   - the F9K1122 candidate changed downstream behavior on multiple unseen tasks
   - on `formWlanSetup` and `formWISP5G`, it improved handler-level targeting
     and evidence capture relative to both baselines

3. But the current evolution signal is still below the standard needed for a
   strong "future-task improvement" claim:
   - no experiment achieved `root_cause_hit`
   - even the best candidate still carried `function_identity_miss` on all
     `WISP5G` runs
   - `SetSystemSettings` shows that transfer is not uniformly positive even
     within the same firmware family

## 5. Current best research statement

The current evidence supports:

- evolved candidates can alter future blind analysis behavior
- some candidates can improve function-level targeting and evidence quality on
  unseen tasks from the same firmware family

The current evidence does not yet support:

- evolved candidates reliably improve target-function correctness on unseen
  tasks
- evolved candidates reliably improve root-cause correctness on unseen tasks
- the present pipeline can already publish broadly reusable skills without
  stronger source filtering, stronger held-out criteria, or a stricter release
  policy than the current same-task rerun gate

## 6. Follow-up priority

The next productive work is now more specific:

- improve source-session selection for candidate generation so the model is not
  learning from mixed-quality source runs
- separate "function-level transfer" from "root-cause-level transfer" as two
  different success criteria
- decide whether release policy should reject candidates that improve evidence
  but still fail root-cause identity on unseen tasks

## 7. Follow-up completed on 2026-08-27

A follow-up source-selection study was completed after this note:

- `reports/current/briefing_20260827/f9k_source_selection_heldout_20260827.md`

That follow-up added three useful pieces of evidence:

- a clean-only single-source candidate did not generate at all (`skip`)
- a reduced two-source candidate was valid on `WlanSetup` and improved over the
  earlier three-source candidate on the same held-out task
- strict leakage audit blocked the same two-source candidate on `WISP5G`
  because the generated skill text mentioned `formWISP5G` directly

So the current state is slightly stronger than this 2026-08-26 snapshot:

- source-session selection measurably changes candidate quality
- leakage control is not theoretical; it already blocks overfitted candidates
