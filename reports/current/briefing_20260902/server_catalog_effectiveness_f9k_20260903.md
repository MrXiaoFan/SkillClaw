# Server-catalog effectiveness rerun: F9K WISP5G

## Protocol

- Case: `f9k1122-webs-overflow-formWISP5G`
- Mode: `server-catalog`
- Repeats: 3 (`r1`–`r3`)
- Remote path: `li@192.168.1.4` via `vm-li`
- Available skills recorded by the proxy: 36
- Skill bodies were selected and loaded by the SkillClaw server; the remote
  client did not read a local `SKILL.md`.

## Results

| Run | Score | File hit | Function hit | Evidence hit | Root-cause hit | Server-selected skill |
|---|---:|---:|---:|---:|---:|---|
| r1 | 2.0/10 | yes | no | no | no | `embedded-cgi-command-injection-triage` |
| r2 | 2.0/10 | yes | no | no | no | `embedded-cgi-command-injection-triage` |
| r3 | 2.0/10 | yes | no | no | no | `embedded-cgi-command-injection-triage` |

The server-side catalog path is operational and reproducible: all three runs
record `injection_mode=server-catalog`, `available_skill_count=36`, and a
loaded skill body. It did not improve this blind case. The selected skill was
explicitly out of domain (command injection rather than the target buffer
overflow), and the model repeatedly missed CVE-2026-4566, `formWISP5G`, and
the expected `strcpy`/`webpage`/`reboot_msg` evidence.

## Interpretation

This is evidence that server-side selection and injection work end-to-end, not
evidence that catalog selection is effective. On this case, server selection
made a stable but incorrect choice, yielding the same 2.0/10 outcome as the
earlier no-skill and natural-retrieval smoke runs. No candidate was generated
or published from these runs.

## Artifacts

- `runtime/imports/remote_vm/server-catalog-f9k-wisp5g-20260903-r1/`
- `runtime/imports/remote_vm/server-catalog-f9k-wisp5g-20260903-r2/`
- `runtime/imports/remote_vm/server-catalog-f9k-wisp5g-20260903-r3/`
- `runtime/imports/remote_vm/server-catalog-f9k-wisp5g-20260903-r4/`
- `runtime/imports/remote_vm/server-catalog-f9k-wisp5g-20260903-r5/`
- `runtime/logs/remote_vm_commands.log`

## Follow-up runs after trace instrumentation

Runs `r4` and `r5` repeated the same F9K condition after the server trace and
finalizer changes. Both completed with score `2.0/10`. Their final artifacts
preserve `server_catalog_trace.status=ok`, `catalog_count=36`, and the raw
selected skill name. They confirm that the instrumentation is carried through
the export pipeline; they do not change the negative effectiveness conclusion.

## Focused v4 guard rerun

After adding the server-side family guard, WISP5G was rerun three times with the
same frozen case and no further selector changes:

| Run | Score | Selected skill | Function hit | Evidence hit | CVE hit |
|---|---:|---|---|---|---|
| v4-r1 | 2.0/10 | `elf-cwe120-firmware-triage` | no | no | no |
| v4-r2 | 2.0/10 | `elf-cwe120-firmware-triage` | no | no | no |
| v4-r3 | 2.0/10 | `elf-cwe120-firmware-triage` | no | no | no |

The guard corrected the skill family but did not improve downstream WISP5G analysis.
Together with the WlanSetup v4 result, this supports the bounded conclusion that
server-side family selection is operational and auditable, while end-to-end benefit
is case-dependent and not yet established.
