# libxml2 Revision Compare - 2026-07-01

## Scope

This note compares three `SkillClaw` runs for
`libxml2-2.9.4-cve-2017-8872`:

1. baseline `2026-06-23`
2. revised-but-still-misaligned `2026-06-28`
3. template-driven rerun `2026-07-01`

## Summary Table

| Run | Score | Exact CVE | File | Function | Validation | Feedback | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `2026-06-23` baseline | `8/10` | no | `HTMLparser.c` plus noisy extras | `htmlParseTryOrFinish` plus noisy extras | passed | positive | strong localization but multi-CVE overclaiming |
| `2026-06-28` revised | `8/10` | no | `HTMLparser.c` plus extras | `htmlParseTryOrFinish` plus extras | passed | neutral | `cve_calibration_miss` explicitly surfaced |
| `2026-07-01` template-driven rerun | `10/10` | yes (`CVE-2017-8872`) | `HTMLparser.c` only | `htmlParseTryOrFinish` only | passed | positive | first clean exact-CVE hit with focused evidence |

## What Improved

- The `2026-07-01` rerun preserved the same core localization target:
  `HTMLparser.c / htmlParseTryOrFinish`.
- The output no longer enumerated neighboring libxml2 CVEs.
- The predicted file/function set became much cleaner: only the ground-truth
  target remained.
- The exact target CVE `CVE-2017-8872` was recovered together with matching
  root-cause and evidence terms.

## Important Caveat

This rerun was executed after temporarily disabling local SkillClaw sharing
reload/pull so that the revised `source-parser-state-machine-oob` prompt would
not be overwritten by the shared pool. Because of that local isolation,
`skill_injection` and `selected_skills` were not recovered in the final record.

So the strongest supported claim is:

- the revised local `source-parser-state-machine-oob` formulation is compatible
  with a clean `libxml2` exact-CVE result,

not yet:

- that the shared multi-user injection pipeline independently logged this same
  rerun end to end.

## Why This Still Matters

Even with the logging caveat, this run is a useful proof point for the current
research hypothesis:

- `cve_calibration_miss` can be isolated as a revision target,
- the revision can preserve localization quality,
- and the revised skill wording can improve exact-CVE attribution behavior on a
  historical parser OOB benchmark.
