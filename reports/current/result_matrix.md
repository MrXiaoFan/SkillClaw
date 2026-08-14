# 当前结果矩阵

生成时间：2026-08-06 15:17:52
记录数：6

| case_id | mode | score_text | cve_hit | file_hit | function_hit | evidence_hit | root_cause_hit | confirmation | confirmation_maturity | selected_skills | first_selected_skills | latest_selected_skills | injection_turns | injection_changed | skill_relevance | relevant_skills | mismatched_skills | infra_skills | decision | action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| exiv2-0.26-cve-2017-17725 | blind-skillclaw-inline-guarded | 6/10 | N | N | Y | Y | Y |  | intermediate-confirmed-path | source-parser-state-machine-oob, elf-cwe120-plt-analysis | source-parser-state-machine-oob, elf-cwe120-plt-analysis |  | 34 | False | mixed_task_relevance | source-parser-state-machine-oob | elf-cwe120-plt-analysis |  | neutral | revise_cve_identity_before_promotion |
| giflib-5.1.2-cve-2016-3977 | blind-skillclaw-inline-guarded | 8/10 | N | Y | Y | Y | Y |  | asan-backed | source-parser-state-machine-oob, elf-cwe120-plt-analysis |  |  | 8 | False | no_task_relevant_skill |  | source-parser-state-machine-oob, elf-cwe120-plt-analysis |  | neutral | inspect_retrieval_before_promoting_skill |
| libarchive-3.8.0-cve-2025-60753 | blind-skillclaw-inline-guarded | 10/10 | Y | Y | Y | Y | Y |  | behavior-backed | elf-cwe120-plt-analysis | elf-cwe120-plt-analysis |  | 7 | False | no_task_relevant_skill |  | elf-cwe120-plt-analysis |  | neutral | inspect_retrieval_before_promoting_skill |
| libxml2-2.9.4-cve-2017-8872 | blind-skillclaw-inline-guarded | 8/10 | N | Y | Y | Y | Y |  | logic-confirm | source-parser-state-machine-oob, elf-cwe120-plt-analysis | source-parser-state-machine-oob, elf-cwe120-plt-analysis |  | 8 | False | mixed_task_relevance | source-parser-state-machine-oob | elf-cwe120-plt-analysis |  | neutral | revise_cve_identity_before_promotion |
| tcpdump-4.9.1-cve-2018-14469 | blind-skillclaw-inline-guarded | 2/10 | N | N | N | N | Y |  | behavior-backed | source-parser-state-machine-oob, elf-cwe120-plt-analysis |  |  | 30 | False | mixed_task_relevance | source-parser-state-machine-oob | elf-cwe120-plt-analysis |  | negative | inspect_skill_mismatch_or_deprecate |
| tcpdump-4.9.1-cve-2017-13031 | blind-skillclaw-inline-guarded | 10/10 | Y | Y | Y | Y | Y |  | behavior-backed | source-parser-state-machine-oob, elf-cwe120-plt-analysis |  |  | 9 | False | mixed_task_relevance | source-parser-state-machine-oob | elf-cwe120-plt-analysis |  | positive | keep_skill_but_prune_extraneous_selection |

## 说明

- `Y/N` 列表示该维度是否命中案例真值。
- `confirmation` 表示动态确认链路最终给出的运行结果状态。
- `confirmation_maturity` 表示当前案例声称达到的确认层级，例如 `behavior-backed` 或 `intermediate-confirmed-path`。
- `confirmation_current_claim` 与 `confirmation_accepted_runtime_claim` 可能不同：前者是当前工程上诚实的总体表述，后者是当前接受的运行时确认路径。
- `skill_relevance=only_infra_skills` 表示 SkillClaw 选到的是框架/自检类技能，而不是任务相关漏洞分析技能。
- `relevant_skills / mismatched_skills / infra_skills` 用来直接观察一次 run 里哪些技能与任务相关、哪些明显跑偏、哪些只是框架自检类技能。
- `decision/action` 是后续技能演化的反馈信号，不等于人工最终结论。
