# Source-quality v2 check — F9K WlanSetup

## Purpose

This is an engineering check of the revised `elf-cwe120-firmware-triage` method. The skill was
forced server-side with `--server-force-skills` so selector variation could not be confused with
skill-content quality. It is not a catalog or paper sample.

## Results

| Run | Score | Function check | Predicted function hit | Evidence hit | Root-cause hit |
| --- | ---: | --- | --- | --- | --- |
| r1 | 4.5/10 | partial | no | yes | no |
| r2 | 2.0/10 | no | no | no | no |
| r3 | 2.0/10 | no | no | no | no |

All three runs injected only `elf-cwe120-firmware-triage` and used the `override` path. The
method revision therefore did not yet produce an exact handler identity or root-cause hit.

## Quality-gate decision

The source set remains blocked for held-out candidate generation: `predicted_function_hit=0/3`
and `root_cause_hit=0/3`. The partial evidence in r1 is not sufficient to bypass the gate.
No candidate was generated, published, or added to `skillspace/live`.

## Next engineering direction

Do not keep tuning this skill against WlanSetup. Use an independently selected source case with
clean exact-function and root-cause hits, or improve the analysis/evaluation instrumentation
before attempting another held-out transfer.
