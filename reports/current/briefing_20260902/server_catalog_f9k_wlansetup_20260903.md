# Server-catalog repeated run: F9K WlanSetup

## Results

| Run | Score | Selected skill | Trace | Function hit | Evidence hit |
| --- | ---: | --- | --- | --- | --- |
| r1 | 2.0/10 | `embedded-cgi-command-injection-triage` | `ok`, catalog=36 | no | no |
| r2 | 2.0/10 | `embedded-cgi-command-injection-triage` | `ok`, catalog=36 | no | no |
| r3 | 2.0/10 | `embedded-cgi-command-injection-triage` | `ok`, catalog=36 | no | no |

Mean score: `2.0/10`.

## Interpretation

The server-side selector repeatedly chose the command-injection skill for a distinct buffer-overflow
task whose expected function is `formWlanSetup` and whose expected evidence includes `strcpy`.
All three traces are valid and complete, so this is a selection-quality failure rather than a
delivery or recording failure.

Together with the WISP5G result, this provides a cross-case diagnostic: the current selector is
stable but over-selects a semantically nearby command-injection skill. It is not evidence that
server-catalog improves downstream analysis.

Artifacts:

- `runtime/imports/remote_vm/server-catalog-f9k-wlansetup-20260903-r1/`
- `runtime/imports/remote_vm/server-catalog-f9k-wlansetup-20260903-r2/`
- `runtime/imports/remote_vm/server-catalog-f9k-wlansetup-20260903-r3/`

## Selector guard iterations

Prompt-only v2 did not correct the first-turn selection; its observed `4.5/10` run was a partial-output fluctuation. The v3 family guard excluded the command-injection skill but selected three overlapping CWE-120 skills, with all runs at `2.0/10`.

The focused v4 guard selected only `elf-cwe120-firmware-triage`:

| Run | Score | Function hit | Evidence hit | CVE hit | Fallback |
| --- | ---: | --- | --- | --- | --- |
| r1 | 4.5/10 | yes | yes | no | yes |
| r2 | 2.0/10 | no | no | no | yes |
| r3 | 4.5/10 | yes | yes | no | yes |

Mean score: `3.67/10`.

This is a diagnostic improvement over v3, not a final effectiveness claim: trace recording is complete and the wrong command-injection skill is excluded, but CVE identity remains unresolved and repeat variance remains material. Future comparisons must report selection correctness separately from downstream answer quality.

Artifacts:

- `runtime/imports/remote_vm/server-catalog-v2-f9k-wlansetup-20260903/`
- `runtime/imports/remote_vm/server-catalog-v3-f9k-wlansetup-20260903/`
- `runtime/imports/remote_vm/server-catalog-v4-f9k-wlansetup-20260903/`
