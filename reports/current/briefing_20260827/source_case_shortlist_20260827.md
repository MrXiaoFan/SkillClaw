# Source Case Shortlist (2026-08-27)

This file is a planning aid for the next evolution experiments.

It summarizes existing `runtime/imports/remote_vm/*-final-enriched.json` runs
and keeps only cases that currently have:

- at least 3 runs with non-empty selected skills
- at least 3 runs with `function_hit = true`

The table is useful for choosing the next source-case family, but it is **not**
paper-ready evidence, because it mixes older historical runs with newer clean
ones.

## Current shortlist

See:

- `source_case_shortlist_20260827.csv`

Top candidates by current function-level signal:

1. `f453-httpd-cmdinject-formWriteFacMac`
2. `f456-httpd-cmdinject-formWriteFacMac`
3. `f1202-httpd-cmdinject-formWriteFacMac`
4. `f9k1122-webs-overflow-formWISP5G`
5. `f9k1122-webs-overflow-formCrossBandSwitch`

## Better pair shapes for strict transfer

The next strict transfer experiment should prefer:

- same firmware family
- same binary type
- same bug class
- different target function names

That makes these pair shapes better than same-function command-injection pairs:

- `FH451` overflow family:
  `formQuickIndex`, `formWrlExtraSet`, `fromAdvSetWan`, `fromSetCfm`,
  `WrlclientSet`
- `F9K1122` overflow family:
  `formCrossBandSwitch`, `formSetSystemSettings`, `formWISP5G`,
  `formWlanSetup`
- `F453` overflow family:
  `formWrlsafeset`, `fromRouteStatic`, `fromqossetting`

Less suitable for strict transfer:

- `f1202/f453/f456-httpd-cmdinject-formWriteFacMac`

Reason:

- they share the same target function name `formWriteFacMac`
- a candidate that learns or mentions that function would trigger a direct
  leakage concern on the held-out side

## How to use this shortlist

For the next source-to-transfer experiment, the better default is:

- start from a case family with high `function_hit` and high
  `root_cause_hit_runs`
- then rebuild a **clean-only** source set under the fixed VM blind path
- only after that, generate a new candidate and run transfer

## Important cautions

- `f9k1122-webs-overflow-formSetPassword` is still a known dataset copy defect
  and should not be used for publication claims.
- `firmware2-*` cases can look strong on `root_cause_hit` while still being
  weak on `function_hit`, so they are not the safest first choice for this
  transfer protocol.
- Cases collected before the `vm-li` default-path fix may contain mixed-quality
  remote history and should be re-run clean before they are treated as strict
  source evidence.
