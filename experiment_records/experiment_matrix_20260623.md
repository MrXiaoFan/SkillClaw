# Experiment Result Matrix

Generated: 2026-06-23 21:25:31
Records: 4

| case_id | mode | score_text | cve_hit | file_hit | function_hit | evidence_hit | root_cause_hit | validation | selected_skills | skill_relevance | decision | action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| libxml2-2.9.4-cve-2017-8872 | direct-deepseek | 6/10 | Y | Y | N | N | Y | passed |  | no_selected_skills | neutral | collect_more_cases |
| libxml2-2.9.4-cve-2017-8872 | skillclaw-inline | 8/10 | N | Y | Y | Y | Y | passed | source-parser-state-machine-oob, skillclaw-proxy-introspection, skillclaw-skill-discovery | legacy_has_non_infra_skill | positive | keep_or_promote_skill |
| tcpdump-4.9.1-cve-2017-13031 | direct-deepseek | 8/10 | N | Y | Y | Y | Y | passed |  | no_selected_skills | positive | use_as_baseline_positive |
| tcpdump-4.9.1-cve-2017-13031 | skillclaw-inline | 8/10 | N | Y | Y | Y | Y | passed | skillclaw-proxy-introspection, skillclaw-claude-env, skillclaw-skill-discovery | only_infra_skills | neutral | inspect_retrieval_before_promoting_skill |

## Notes

- `Y/N` columns report whether the answer matched the case ground truth for that dimension.
- `skill_relevance=only_infra_skills` means SkillClaw selected framework/self-inspection skills rather than task-specific vulnerability skills.
- `decision/action` are feedback signals for later skill evolution; they are not human final judgments.
