# Skill Feedback Summary

This file aggregates final experiment records into skill-level feedback evidence.
It is not a global quality score; it only reflects the current benchmark cases.

| skill | selected_count | positive | neutral | negative | mean_score | validation_passed | validation_partial | validation_failed | file_hits | function_hits | cve_hits | actions | cases |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| source-parser-state-machine-oob | 3 | 3 | 0 | 0 | 0.8 | 1 | 0 | 0 | 3 | 3 | 0 | keep_or_promote_skill:3 | libxml2-2.9.4-cve-2017-8872, tcpdump-4.9.1-cve-2017-13031 |
| elf-cwe120-firmware-triage | 3 | 2 | 1 | 0 | 0.7 | 1 | 0 | 0 | 3 | 2 | 0 | inspect_retrieval_before_promoting_skill:1, keep_or_promote_skill:2 | libxml2-2.9.4-cve-2017-8872, tcpdump-4.9.1-cve-2017-13031 |
| vuln-hunting | 2 | 2 | 0 | 0 | 0.8 | 0 | 0 | 0 | 2 | 2 | 0 | keep_or_promote_skill:2 | libxml2-2.9.4-cve-2017-8872, tcpdump-4.9.1-cve-2017-13031 |
| skillclaw-skill-discovery | 3 | 1 | 2 | 0 | 0.7 | 3 | 0 | 0 | 3 | 2 | 0 | inspect_retrieval_before_promoting_skill:2, keep_or_promote_skill:1 | libxml2-2.9.4-cve-2017-8872, tcpdump-4.9.1-cve-2017-13031 |
| skillclaw-proxy-introspection | 2 | 1 | 1 | 0 | 0.8 | 2 | 0 | 0 | 2 | 2 | 0 | inspect_retrieval_before_promoting_skill:1, keep_or_promote_skill:1 | libxml2-2.9.4-cve-2017-8872, tcpdump-4.9.1-cve-2017-13031 |
| skillclaw-claude-env | 1 | 0 | 1 | 0 | 0.8 | 1 | 0 | 0 | 1 | 1 | 0 | inspect_retrieval_before_promoting_skill:1 | tcpdump-4.9.1-cve-2017-13031 |
| ssh-password-recon-workflow | 1 | 0 | 1 | 0 | 0.5 | 1 | 0 | 0 | 1 | 0 | 0 | inspect_retrieval_before_promoting_skill:1 | tcpdump-4.9.1-cve-2017-13031 |

## Interpretation

- `positive/neutral/negative` comes from the run-level feedback decision.
- `mean_score` is the mean normalized localization score across selected runs.
- A skill with few selections should be treated as anecdotal evidence, not a stable ranking.
