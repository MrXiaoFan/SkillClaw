# Experiment Result Matrix

Generated: 2026-07-05 12:32:35
Records: 4

| case_id | mode | score_text | cve_hit | file_hit | function_hit | evidence_hit | root_cause_hit | validation | selected_skills | first_selected_skills | latest_selected_skills | injection_turns | injection_changed | skill_relevance | decision | action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| giflib-5.1.2-cve-2016-3977 | skillclaw-inline-guarded | 10/10 | Y | Y | Y | Y | Y | passed | source-parser-state-machine-oob, ida-headless-cwe120-sink-analysis, idalib-headless-batch-diagnosis | source-parser-state-machine-oob, ida-headless-cwe120-sink-analysis, idalib-headless-batch-diagnosis | source-parser-state-machine-oob, ida-headless-cwe120-sink-analysis, idalib-headless-batch-diagnosis | 10 | False | has_task_relevant_skill | positive | keep_or_promote_skill |
| libxml2-2.9.4-cve-2017-8872 | skillclaw-inline-guarded | 10/10 | Y | Y | Y | Y | Y | passed | source-parser-state-machine-oob, vuln-hunting, elf-cwe120-firmware-triage | source-parser-state-machine-oob, vuln-hunting, elf-cwe120-firmware-triage | source-parser-state-machine-oob, vuln-hunting, elf-cwe120-firmware-triage | 32 | False | has_task_relevant_skill | positive | keep_or_promote_skill |
| tcpdump-4.9.1-cve-2017-13031 | skillclaw-inline-guarded | 10/10 | Y | Y | Y | Y | Y | passed | source-parser-state-machine-oob, vuln-hunting, verify-rootfs-full-enumeration | source-parser-state-machine-oob, vuln-hunting, verify-rootfs-full-enumeration | source-parser-state-machine-oob, vuln-hunting, verify-rootfs-full-enumeration | 11 | False | has_task_relevant_skill | positive | keep_or_promote_skill |
| tcpdump-4.9.1-cve-2017-13031 | direct-deepseek-guarded | 10/10 | Y | Y | Y | Y | Y | passed |  |  |  | 0 | False | no_selected_skills | positive | use_as_baseline_positive |

## Notes

- `Y/N` columns report whether the answer matched the case ground truth for that dimension.
- `skill_relevance=only_infra_skills` means SkillClaw selected framework/self-inspection skills rather than task-specific vulnerability skills.
- `decision/action` are feedback signals for later skill evolution; they are not human final judgments.
