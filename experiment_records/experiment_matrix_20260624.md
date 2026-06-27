# Experiment Result Matrix

Generated: 2026-06-24 11:51:28
Records: 5

| case_id | mode | score_text | cve_hit | file_hit | function_hit | evidence_hit | root_cause_hit | validation | selected_skills | first_selected_skills | latest_selected_skills | injection_turns | injection_changed | skill_relevance | decision | action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| libxml2-2.9.4-cve-2017-8872 | direct-deepseek | 6/10 | Y | Y | N | N | Y | passed |  |  |  | 0 | False | no_selected_skills | neutral | collect_more_cases |
| libxml2-2.9.4-cve-2017-8872 | skillclaw-inline | 8/10 | N | Y | Y | Y | Y | passed | source-parser-state-machine-oob, skillclaw-proxy-introspection, skillclaw-skill-discovery | source-parser-state-machine-oob, skillclaw-proxy-introspection, skillclaw-skill-discovery | source-parser-state-machine-oob, skillclaw-proxy-introspection, skillclaw-skill-discovery | 1 | False | legacy_has_non_infra_skill | positive | keep_or_promote_skill |
| tcpdump-4.9.1-cve-2017-13031 | direct-deepseek | 8/10 | N | Y | Y | Y | Y | passed |  |  |  | 0 | False | no_selected_skills | positive | use_as_baseline_positive |
| tcpdump-4.9.1-cve-2017-13031 | skillclaw-inline | 8/10 | N | Y | Y | Y | Y | passed | skillclaw-proxy-introspection, skillclaw-claude-env, skillclaw-skill-discovery | skillclaw-proxy-introspection, skillclaw-claude-env, skillclaw-skill-discovery | skillclaw-proxy-introspection, skillclaw-claude-env, skillclaw-skill-discovery | 1 | False | only_infra_skills | neutral | inspect_retrieval_before_promoting_skill |
| tcpdump-4.9.1-cve-2017-13031 | skillclaw-inline-rerun | 5/10 | N | Y | N | Y | Y | passed | elf-cwe120-firmware-triage, ssh-password-recon-workflow, skillclaw-skill-discovery | source-parser-state-machine-oob, elf-cwe120-firmware-triage, vuln-hunting | elf-cwe120-firmware-triage, ssh-password-recon-workflow, skillclaw-skill-discovery | 13 | True | no_task_relevant_skill | neutral | inspect_retrieval_before_promoting_skill |

## Notes

- `Y/N` columns report whether the answer matched the case ground truth for that dimension.
- `skill_relevance=only_infra_skills` means SkillClaw selected framework/self-inspection skills rather than task-specific vulnerability skills.
- `decision/action` are feedback signals for later skill evolution; they are not human final judgments.
