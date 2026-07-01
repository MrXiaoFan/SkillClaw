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
| `2026-07-01` template-driven rerun | `10/10` | yes (`CVE-2017-8872`) | `HTMLparser.c` only | `htmlParseTryOrFinish` only | passed | positive | first clean exact-CVE hit with focused evidence; injection audit recovered |

## What Improved

- The `2026-07-01` rerun preserved the same core localization target:
  `HTMLparser.c / htmlParseTryOrFinish`.
- The output no longer enumerated neighboring libxml2 CVEs.
- The predicted file/function set became much cleaner: only the ground-truth
  target remained.
- The exact target CVE `CVE-2017-8872` was recovered together with matching
  root-cause and evidence terms.

## Injection Audit Recovery

The initial `2026-07-01` final record was missing attached `skill_injection`
metadata, but the local SkillClaw service had in fact logged the rerun in
`records/conversations.jsonl`. We later recovered the audit trail and attached
it to a postprocessed final record for the same run.

Recovered session evidence:

- `session_id`: `3e940773-4651-4198-ab3a-95236c180fe9`
- `selected_skills`:
  - `source-parser-state-machine-oob`
  - `vuln-hunting`
  - `elf-cwe120-firmware-triage`
- `injection_mode`: `inline`
- `available_skill_count`: `35`

This means the strongest supported claim is now:

- the revised local `source-parser-state-machine-oob` formulation produced a
  clean exact-CVE result, and
- the same rerun can be tied back to a concrete SkillClaw injection record with
  relevant selected skills.

## Why This Still Matters

This run is now a stronger proof point for the current research hypothesis:

- `cve_calibration_miss` can be isolated as a revision target,
- the revision can preserve localization quality,
- and the revised skill wording can improve exact-CVE attribution behavior on a
  historical parser OOB benchmark.
