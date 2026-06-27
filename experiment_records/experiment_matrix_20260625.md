# Experiment Result Matrix

Generated: 2026-06-25 19:01:48
Records: 7

| case_id | mode | score_text | cve_hit | file_hit | function_hit | evidence_hit | root_cause_hit | validation | selected_skills | first_selected_skills | latest_selected_skills | injection_turns | injection_changed | skill_relevance | decision | action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| libxml2-2.9.4-cve-2017-8872 | direct-deepseek-guarded-clean-budget035 | 0/10 | N | N | N | N | N |  |  |  |  | 0 | False | no_selected_skills | neutral | baseline_no_skill_feedback |
| libxml2-2.9.4-cve-2017-8872 | direct-deepseek-guarded-clean-budget080 | 10/10 | Y | Y | Y | Y | Y |  |  |  |  | 0 | False | no_selected_skills | positive | use_as_baseline_positive |
| libxml2-2.9.4-cve-2017-8872 | skillclaw-inline-guarded-clean-budget035 | 0/10 | N | N | N | N | N |  |  |  |  | 0 | False | no_selected_skills | neutral | baseline_no_skill_feedback |
| libxml2-2.9.4-cve-2017-8872 | skillclaw-inline-guarded-clean-budget080 | 8/10 | N | Y | Y | Y | Y |  | source-parser-state-machine-oob, elf-cwe120-firmware-triage, vuln-hunting | source-parser-state-machine-oob, elf-cwe120-firmware-triage, vuln-hunting | source-parser-state-machine-oob, elf-cwe120-firmware-triage, vuln-hunting | 8 | False | has_task_relevant_skill | positive | keep_or_promote_skill |
| tcpdump-4.9.1-cve-2017-13031 | direct-deepseek-guarded-clean-budget035 | 0/10 | N | N | N | N | N |  |  |  |  | 0 | False | no_selected_skills | neutral | baseline_no_skill_feedback |
| tcpdump-4.9.1-cve-2017-13031 | direct-deepseek-guarded-clean-budget080 | 8/10 | N | Y | Y | Y | Y |  |  |  |  | 0 | False | no_selected_skills | positive | use_as_baseline_positive |
| tcpdump-4.9.1-cve-2017-13031 | skillclaw-inline-guarded-clean-budget035 | 8/10 | N | Y | Y | Y | Y |  | source-parser-state-machine-oob, elf-cwe120-firmware-triage, vuln-hunting | source-parser-state-machine-oob, elf-cwe120-firmware-triage, vuln-hunting | source-parser-state-machine-oob, elf-cwe120-firmware-triage, vuln-hunting | 6 | False | has_task_relevant_skill | positive | keep_or_promote_skill |

## Notes

- `Y/N` columns report whether the answer matched the case ground truth for that dimension.
- `skill_relevance=only_infra_skills` means SkillClaw selected framework/self-inspection skills rather than task-specific vulnerability skills.
- `decision/action` are feedback signals for later skill evolution; they are not human final judgments.
