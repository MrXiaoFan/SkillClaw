# libxml2 Paper-Ready Result Table - 2026-07-01

## Recommended Reading Of The Result

This table is intended for paper drafting and slide reuse. It separates two
claims:

1. whether `SkillClaw` localization stayed stable across revisions,
2. whether the template-driven revision improved exact-CVE calibration.

## Main Comparison

| System / Run | Score | Exact CVE Hit | File Hit | Function Hit | Validation | Key Observation |
| --- | --- | --- | --- | --- | --- | --- |
| Direct baseline (`2026-06-25`) | `10/10` | yes | yes | yes | passed | strong upper baseline on this case |
| SkillClaw baseline (`2026-06-23`) | `8/10` | no | yes | yes | passed | localized correctly but overclaimed many neighboring CVEs |
| SkillClaw revised (`2026-06-28`) | `8/10` | no | yes | yes | passed | still localized correctly; `cve_calibration_miss` became explicit |
| SkillClaw template-driven rerun (`2026-07-01`) | `10/10` | yes | yes | yes | passed | first clean exact-CVE hit after targeted CVE-calibration revision |

## SkillClaw Trajectory Only

| SkillClaw Stage | Localization | Evidence | Root Cause | Exact CVE Attribution | Notes |
| --- | --- | --- | --- | --- | --- |
| `2026-06-23` baseline | strong | strong | strong | weak | multi-CVE hedge list; noisy extra files/functions |
| `2026-06-28` revised | strong | strong | strong | weak-but-exposed | failure was reclassified as `cve_calibration_miss` |
| `2026-07-01` template rerun | strong | strong | strong | strong | exact `CVE-2017-8872`, clean file/function set |

## Paper-Safe Claim

The strongest paper-safe statement supported by current evidence is:

> On `libxml2-2.9.4-cve-2017-8872`, validator-guided template revision improved
> SkillClaw's exact-CVE attribution behavior without degrading the already
> correct localization target (`HTMLparser.c / htmlParseTryOrFinish`).

## Important Caveat

The `2026-07-01` rerun was executed after temporarily disabling local sharing
reload/pull, because the shared pool was overwriting the revised local skill.
So this table supports a **local template-driven revision success** claim first.

It does **not yet** prove that the shared multi-user injection pipeline would
log the same result end to end without an additional synchronized rerun.
