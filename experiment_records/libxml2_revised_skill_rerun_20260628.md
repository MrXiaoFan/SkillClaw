# libxml2 Revised Skill Rerun - 2026-06-28

## Purpose

This rerun checks whether the revised `source-parser-state-machine-oob` skill improves the libxml2 CVE-calibration problem observed in earlier experiments. The target remains `libxml2-2.9.4-cve-2017-8872`, and the remote VM uses Claude Code through the SkillClaw proxy.

## Setup

The host SkillClaw service was healthy and exposed 35 server-side skills. The remote VM passed preflight checks for the libxml2 source tree, `.libs/xmllint`, Claude Code SkillClaw configuration, and `/v1/skills` visibility.

The run used:

- case: `experiment_cases/libxml2-2.9.4-cve-2017-8872.json`
- mode: `skillclaw-inline`
- run id: `libxml2-skillclaw-revised-20260628`
- selected skills: `source-parser-state-machine-oob`, `elf-cwe120-firmware-triage`, `elf-cwe120-plt-analysis`
- session: `4185693c-2de4-488f-a2c0-7cc78f92a615`

Raw remote artifacts are archived under `experiment_records/remote_runs/libxml2-20260628/`. The injection-attached final record is `experiment_records/libxml2-skillclaw-revised-final-20260628.json`.

## Result

The run scored `8/10`. It correctly localized the source file `HTMLparser.c`, the function `htmlParseTryOrFinish`, and the key evidence around `in->cur[2]`, `in->cur[3]`, and `avail`. The bundle-script validator also passed, confirming the expected source-level pattern.

The run still missed the exact CVE identity. It predicted nearby libxml2 CVEs such as `CVE-2017-9047` and `CVE-2017-9048`, but not the expected `CVE-2017-8872`.

## Feedback Adjustment

This rerun exposed a weakness in the earlier feedback rule: a high score with validator pass was marked positive even when the exact CVE was missed. The feedback layer now adds `quality_flags`, and this run is marked:

- decision: `neutral`
- suggested action: `revise_cve_calibration_before_promotion`
- quality flag: `cve_calibration_miss`

This keeps the useful localization evidence while preventing the skill from being promoted as a fully successful vulnerability-identification skill.

## Research Implication

The current SkillClaw skill improves structured source localization, but text-only skill guidance is still insufficient for exact CVE calibration. The next research step should treat CVE identity as a separate evidence dimension, requiring advisory, patch, or version-range support instead of accepting source localization alone.
