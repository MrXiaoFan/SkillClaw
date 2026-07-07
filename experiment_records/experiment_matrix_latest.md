# Experiment Result Matrix

Generated: 2026-07-07 17:17:41
Records: 5

| case_id | mode | score_text | cve_hit | file_hit | function_hit | evidence_hit | root_cause_hit | validation | selected_skills | first_selected_skills | latest_selected_skills | injection_turns | injection_changed | skill_relevance | decision | action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| giflib-5.1.2-cve-2016-3977 | skillclaw-inline-guarded | 10/10 | Y | Y | Y | Y | Y | passed | source-parser-state-machine-oob, ida-headless-cwe120-sink-analysis, idalib-headless-batch-diagnosis | source-parser-state-machine-oob, ida-headless-cwe120-sink-analysis, idalib-headless-batch-diagnosis | source-parser-state-machine-oob, ida-headless-cwe120-sink-analysis, idalib-headless-batch-diagnosis | 7 | False | no_task_relevant_skill | neutral | inspect_retrieval_before_promoting_skill |
| libarchive-3.8.0-cve-2025-60753 | skillclaw-inline-guarded | 10/10 | Y | Y | Y | Y | Y | passed | source-parser-state-machine-oob, idalib-headless-batch-diagnosis, ida-headless-cwe120-sink-analysis | source-parser-state-machine-oob, idalib-headless-batch-diagnosis, ida-headless-cwe120-sink-analysis | source-parser-state-machine-oob, idalib-headless-batch-diagnosis, ida-headless-cwe120-sink-analysis | 20 | False | no_task_relevant_skill | neutral | inspect_retrieval_before_promoting_skill |
| libxml2-2.9.4-cve-2017-8872 | skillclaw-inline-guarded | 10/10 | Y | Y | Y | Y | Y | passed | source-parser-state-machine-oob, vuln-hunting, elf-cwe120-firmware-triage | source-parser-state-machine-oob, vuln-hunting, elf-cwe120-firmware-triage | source-parser-state-machine-oob, vuln-hunting, elf-cwe120-firmware-triage | 32 | False | mixed_task_relevance | positive | keep_skill_but_prune_extraneous_selection |
| tcpdump-4.9.1-cve-2017-13031 | skillclaw-inline-guarded | 10/10 | Y | Y | Y | Y | Y | passed | source-parser-state-machine-oob, vuln-hunting, verify-rootfs-full-enumeration | source-parser-state-machine-oob, vuln-hunting, verify-rootfs-full-enumeration | source-parser-state-machine-oob, vuln-hunting, verify-rootfs-full-enumeration | 11 | False | mixed_task_relevance | positive | keep_skill_but_prune_extraneous_selection |
| tcpdump-4.9.1-cve-2018-14469 | skillclaw-inline-guarded | 10/10 | Y | Y | Y | Y | Y | passed | source-parser-state-machine-oob, vuln-hunting, verify-rootfs-full-enumeration | source-parser-state-machine-oob, vuln-hunting, verify-rootfs-full-enumeration | source-parser-state-machine-oob, vuln-hunting, verify-rootfs-full-enumeration | 18 | False | mixed_task_relevance | positive | keep_skill_but_prune_extraneous_selection |

## Notes

- `Y/N` columns report whether the answer matched the case ground truth for that dimension.
- `skill_relevance=only_infra_skills` means SkillClaw selected framework/self-inspection skills rather than task-specific vulnerability skills.
- `decision/action` are feedback signals for later skill evolution; they are not human final judgments.
