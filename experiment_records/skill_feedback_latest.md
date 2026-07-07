# Skill Feedback Summary

This file aggregates final experiment records into skill-level feedback evidence.
It is not a global quality score; it only reflects the current benchmark cases.

| skill | selected_count | positive | neutral | negative | mean_score | validation_passed | validation_partial | validation_failed | artifact_generated | artifact_execution_passed | relevant_selected | mismatched_selected | infra_selected | file_hits | function_hits | cve_hits | actions | cases |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| source-parser-state-machine-oob | 5 | 3 | 2 | 0 | 1.0 | 5 | 0 | 0 | 4 | 4 | 3 | 2 | 0 | 5 | 5 | 5 | inspect_retrieval_before_promoting_skill:2, keep_skill_but_prune_extraneous_selection:3 | giflib-5.1.2-cve-2016-3977, libarchive-3.8.0-cve-2025-60753, libxml2-2.9.4-cve-2017-8872, tcpdump-4.9.1-cve-2017-13031, tcpdump-4.9.1-cve-2018-14469 |
| vuln-hunting | 3 | 0 | 3 | 0 | 1.0 | 3 | 0 | 0 | 2 | 2 | 0 | 3 | 0 | 3 | 3 | 3 | keep_skill_but_prune_extraneous_selection:3 | libxml2-2.9.4-cve-2017-8872, tcpdump-4.9.1-cve-2017-13031, tcpdump-4.9.1-cve-2018-14469 |
| ida-headless-cwe120-sink-analysis | 2 | 0 | 2 | 0 | 1.0 | 2 | 0 | 0 | 2 | 2 | 0 | 2 | 0 | 2 | 2 | 2 | inspect_retrieval_before_promoting_skill:2 | giflib-5.1.2-cve-2016-3977, libarchive-3.8.0-cve-2025-60753 |
| idalib-headless-batch-diagnosis | 2 | 0 | 2 | 0 | 1.0 | 2 | 0 | 0 | 2 | 2 | 0 | 2 | 0 | 2 | 2 | 2 | inspect_retrieval_before_promoting_skill:2 | giflib-5.1.2-cve-2016-3977, libarchive-3.8.0-cve-2025-60753 |
| verify-rootfs-full-enumeration | 2 | 0 | 2 | 0 | 1.0 | 2 | 0 | 0 | 2 | 2 | 0 | 2 | 0 | 2 | 2 | 2 | keep_skill_but_prune_extraneous_selection:2 | tcpdump-4.9.1-cve-2017-13031, tcpdump-4.9.1-cve-2018-14469 |
| elf-cwe120-firmware-triage | 1 | 0 | 1 | 0 | 1.0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 1 | 1 | keep_skill_but_prune_extraneous_selection:1 | libxml2-2.9.4-cve-2017-8872 |

## Interpretation

- `positive/neutral/negative` comes from the run-level feedback decision.
- `mismatched_selected` means the skill was selected in a successful run but was not task-aligned, so it does not receive positive credit.
- `mean_score` is the mean normalized localization score across selected runs.
- `artifact_generated` / `artifact_execution_passed` summarize confirmation-oriented artifact checks.
- A skill with few selections should be treated as anecdotal evidence, not a stable ranking.
