# 159-run Ablation Preservation Audit · 2026-09-03

## Decision

Keep `runtime/ablation/results/ablation_results.csv` for now.

This dataset is methodologically superseded because its oracle condition contains skill-answer
leakage, but it is not safely replaceable by another complete 159-run aggregate.

## Evidence

- Aggregate file: `runtime/ablation/results/ablation_results.csv`
- Size: 159 data rows, 51,881 bytes
- Later `ablation_results_plan11_frozen.csv` has 153 rows and is a cleaned replacement for the
  main claim, not an equivalent copy of the old experiment.
- Matching raw import directories were found for 148 of 159 run IDs.
- 11 old run IDs currently have no matching directory under `runtime/imports/remote_vm/`.

## Implication for cleanup

Do not delete the 159-run CSV until either:

1. its historical comparison is explicitly abandoned; or
2. the 148 available raw runs have been indexed and the missing 11 runs are confirmed
   unrecoverable, with the loss documented.

The dataset remains excluded from current paper claims and catalog experiments. It is retained
only to preserve the historical negative-control/methodology comparison.
