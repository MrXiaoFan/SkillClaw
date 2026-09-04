# F9K Skill Condition Diagnostic (2026-09-02)

## Purpose

This diagnostic separates three possible causes of the recent source failure:

- the current model cannot analyze the task;
- the fixed seed skill sends the model in the wrong direction;
- natural skill retrieval selects unrelated skills.

All runs used the same remote VM (`li@192.168.1.4`), the same F9K `formWISP5G`
case, the same SkillClaw proxy at `http://192.168.1.1:30000`, and the same
current model configuration. Evolve feedback and publishing were disabled.

## Results

| Condition | Runs | Scores | Function hit | Evidence hit | Root-cause hit | Selected skills |
|---|---:|---|---:|---:|---:|---|
| No skill | 3 | 4.5, 2.0, 2.0 | 1/3 | 1/3 | 0/3 | none |
| Fixed seed | 3 | 2.0, 2.0, 2.0 | 0/3 | 0/3 | 0/3 | `elf-cwe120-firmware-triage` |
| Natural retrieval | 3 | 2.0, 2.0, 2.0 | 0/3 | 0/3 | 0/3 | `tenda-httpd-goform-execommand-triage`, `elf-cwe120-static-scan`, `vuln-hunting` |

The natural-retrieval runs were all marked with `extraneous_skill_selection`.
They selected skills for Tenda command injection and generic ELF scanning,
although the target was an F9K `webs` overflow case.

## Interpretation

The proxy and remote execution path worked: every run passed preflight, used
the SkillClaw provider, and recorded 36 available skills. The fixed seed and
natural retrieval conditions both performed worse than the first no-skill run.
However, the no-skill condition was itself variable, so this is evidence of
skill-induced error and retrieval mis-selection, not a controlled proof that
skills always reduce performance.

The current configuration uses `deepseek-v4-flash`; historical evolution logs
contain failures for `deepseek-v4-pro` because that model was unavailable at
the time. These results must therefore not be mixed with earlier experiments
without recording the model configuration.

## Artifacts

Per-run enriched records are stored under:

- `runtime/imports/remote_vm/diagnostic-f9k-wisp5g-no-skill-20260902/`
- `runtime/imports/remote_vm/diagnostic-f9k-wisp5g-no-skill-r2-20260902/`
- `runtime/imports/remote_vm/diagnostic-f9k-wisp5g-no-skill-r3-20260902/`
- `runtime/imports/remote_vm/diagnostic-f9k-wisp5g-natural-r1-20260902/`
- `runtime/imports/remote_vm/diagnostic-f9k-wisp5g-natural-r2-20260902/`
- `runtime/imports/remote_vm/diagnostic-f9k-wisp5g-natural-r3-20260902/`
- `runtime/imports/remote_vm/source-f9k-wisp5g-weak-r1-20260902/`
- `runtime/imports/remote_vm/source-f9k-wisp5g-weak-r2-20260902/`
- `runtime/imports/remote_vm/source-f9k-wisp5g-weak-r3-20260902/`

No candidate was generated from this diagnostic set, because none of the
source records satisfied the target-function, evidence, and root-cause quality
requirements.

## Post-fix smoke runs

After the negative-trigger matching fix in `skillclaw/skill_manager.py`, the
running SkillClaw service was restarted and two additional remote runs were
performed:

| Condition | Score | Function hit | Evidence hit | Root-cause hit | Selected skills |
|---|---:|---:|---:|---:|---|
| No skill | 2.0 | 0/1 | 0/1 | 0/1 | none |
| Natural retrieval | 2.0 | 0/1 | 0/1 | 0/1 | `windows-dotnet-cmd-injection-triage` |

The fix removed the earlier Tenda/ELF selection in this prompt, but the
retrieval path still selected an unrelated command-injection skill. This is a
reduction of one false-selection pattern, not a complete solution to
cross-domain retrieval.

## Catalog smoke run

`smoke-f9k-wisp5g-catalog-20260902` was run after restarting SkillClaw with
`skills.injection_mode=catalog`. The final record lists all 36 eligible skill
names in `selected_skill_names`. That field records the catalog supplied to the
session; it does not prove that the model used all of those skills.

The conversation record for session
`276146da-765b-5ad8-bc36-d046ef5b3dc1` was checked separately. The model made
shell inspection calls, but no call read a specific skill file or otherwise
requested a skill body from the catalog. The run scored 2.0 with no target
function, evidence, or root-cause hit, and was marked with
`cve_identity_miss`, `function_identity_miss`, and
`extraneous_skill_selection`.

This smoke run therefore verifies catalog delivery, not catalog-assisted skill
use or catalog effectiveness. A valid catalog comparison needs an explicit
record of the skill the model selected and read, while keeping the case blind;
the current `selected_skill_names` field alone is insufficient for that claim.

## Catalog verification rerun

`catalog-verify-f9k-wisp5g-20260902-r2` completed through the real remote VM
path. SSH connected to `li@192.168.1.4`, the remote Claude process used the
SkillClaw provider, and the SkillClaw proxy used the configured catalog mode.
The run created a fresh blind workspace and completed normally.

The result was `score=2.0/10.0`: the binary/file was identified, but the target
CVE, target function `formWISP5G`, and target evidence were not identified. The
model instead reported `CVE-2019-169200`, `formAdvanceSetup`, and a generic
command-execution explanation.

The final record reports `injection_mode=catalog`, `available_skill_count=36`,
and a catalog prompt hash, while its skill relevance section says
`no_selected_skills`. The matching conversation trace contains shell commands
for binary inspection but no read of a catalog-listed `SKILL.md`. This confirms
that catalog delivery worked, but the model did not perform the required lazy
skill selection/load action. It is therefore a valid catalog-delivery and
failure-observation run, not evidence that catalog skill use is ineffective.

The first attempt with `--preflight` was rejected before analysis because the
remote preflight checked `127.0.0.1:30000`; the VM's Claude configuration
correctly points to the Windows host address `10.12.189.47:30000`. The rerun
omitted that unsuitable remote-localhost preflight and completed successfully.

Artifact directory:

- `runtime/imports/remote_vm/catalog-verify-f9k-wisp5g-20260902-r2/`

## Server-catalog implementation status

The code now supports a separate `server-catalog` mode. In this mode the
SkillClaw server sends a text-only catalog (skill names and descriptions) to
the configured upstream LLM, accepts only names that exist in the local skill
manager, limits the result to three skills, reads those skill bodies locally,
and injects the bodies into the remote Claude request. The remote client does
not need access to the SkillClaw skill path.

The old `catalog` mode is retained unchanged as the client-lazy-loading mode.
It remains the configured mode until an explicit restart with
`skills.injection_mode=server-catalog`; existing catalog and inline records are
therefore still interpretable under their original semantics.

The selector was locally verified with a mocked upstream response: an unknown
skill name was discarded and four returned names were limited to three valid
catalog entries. A remote `server-catalog` effectiveness run still requires a
service restart into that mode and must be recorded separately from the
catalog-delivery smoke run above.
