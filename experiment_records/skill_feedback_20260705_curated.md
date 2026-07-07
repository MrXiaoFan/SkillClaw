# Skill Feedback Summary

This file aggregates final experiment records into skill-level feedback evidence.
It is not a global quality score; it only reflects the current benchmark cases.

| skill | selected_count | positive | neutral | negative | mean_score | validation_passed | validation_partial | validation_failed | artifact_generated | artifact_execution_passed | file_hits | function_hits | cve_hits | actions | cases |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| source-parser-state-machine-oob | 3 | 3 | 0 | 0 | 1.0 | 3 | 0 | 0 | 2 | 2 | 3 | 3 | 3 | keep_or_promote_skill:3 | giflib-5.1.2-cve-2016-3977, libxml2-2.9.4-cve-2017-8872, tcpdump-4.9.1-cve-2017-13031 |
| vuln-hunting | 2 | 2 | 0 | 0 | 1.0 | 2 | 0 | 0 | 1 | 1 | 2 | 2 | 2 | keep_or_promote_skill:2 | libxml2-2.9.4-cve-2017-8872, tcpdump-4.9.1-cve-2017-13031 |
| ida-headless-cwe120-sink-analysis | 1 | 1 | 0 | 0 | 1.0 | 1 | 0 | 0 | 1 | 1 | 1 | 1 | 1 | keep_or_promote_skill:1 | giflib-5.1.2-cve-2016-3977 |
| idalib-headless-batch-diagnosis | 1 | 1 | 0 | 0 | 1.0 | 1 | 0 | 0 | 1 | 1 | 1 | 1 | 1 | keep_or_promote_skill:1 | giflib-5.1.2-cve-2016-3977 |
| elf-cwe120-firmware-triage | 1 | 1 | 0 | 0 | 1.0 | 1 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | keep_or_promote_skill:1 | libxml2-2.9.4-cve-2017-8872 |
| verify-rootfs-full-enumeration | 1 | 1 | 0 | 0 | 1.0 | 1 | 0 | 0 | 1 | 1 | 1 | 1 | 1 | keep_or_promote_skill:1 | tcpdump-4.9.1-cve-2017-13031 |

## Interpretation

- `positive/neutral/negative` comes from the run-level feedback decision.
- `mean_score` is the mean normalized localization score across selected runs.
- `artifact_generated` / `artifact_execution_passed` summarize confirmation-oriented artifact checks.
- A skill with few selections should be treated as anecdotal evidence, not a stable ranking.
