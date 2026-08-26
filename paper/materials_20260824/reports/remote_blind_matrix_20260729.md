# 当前结果矩阵

生成时间：2026-07-29 10:01:49
记录数：5

| case_id | mode | score_text | cve_hit | file_hit | function_hit | evidence_hit | root_cause_hit | validation | confirmation_maturity | selected_skills | first_selected_skills | latest_selected_skills | injection_turns | injection_changed | skill_relevance | relevant_skills | mismatched_skills | infra_skills | decision | action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| exiv2-0.26-cve-2017-17725 | blind-skillclaw-inline-guarded | 10/10 | Y | Y | Y | Y | Y | failed | intermediate-confirmed-path | source-parser-state-machine-oob, elf-plt-reloc-sink-scan, elf-cwe120-plt-analysis | source-parser-state-machine-oob, elf-plt-reloc-sink-scan, elf-cwe120-plt-analysis | source-parser-state-machine-oob, elf-plt-reloc-sink-scan, elf-cwe120-plt-analysis | 6 | False | mixed_task_relevance | source-parser-state-machine-oob | elf-plt-reloc-sink-scan, elf-cwe120-plt-analysis |  | negative | require_dynamic_evidence_before_publish |
| giflib-5.1.2-cve-2016-3977 | blind-skillclaw-inline-guarded | 10/10 | Y | Y | Y | Y | Y | passed | asan-backed | source-parser-state-machine-oob, verify-rootfs-full-enumeration, vuln-hunting | source-parser-state-machine-oob, verify-rootfs-full-enumeration, vuln-hunting | source-parser-state-machine-oob, verify-rootfs-full-enumeration, vuln-hunting | 7 | False | no_task_relevant_skill |  | source-parser-state-machine-oob, verify-rootfs-full-enumeration, vuln-hunting |  | neutral | inspect_retrieval_before_promoting_skill |
| libxml2-2.9.4-cve-2017-8872 | blind-skillclaw-inline-guarded | 10/10 | Y | Y | Y | Y | Y | passed | logic-confirm | source-parser-state-machine-oob, elf-plt-reloc-sink-scan, cwe120-analysis-verification | source-parser-state-machine-oob, elf-plt-reloc-sink-scan, cwe120-analysis-verification | source-parser-state-machine-oob, elf-plt-reloc-sink-scan, cwe120-analysis-verification | 6 | False | mixed_task_relevance | source-parser-state-machine-oob | elf-plt-reloc-sink-scan, cwe120-analysis-verification |  | positive | keep_skill_but_prune_extraneous_selection |
| tcpdump-4.9.1-cve-2017-13031 | blind-skillclaw-inline-guarded | 10/10 | Y | Y | Y | Y | Y | passed | behavior-backed | source-parser-state-machine-oob, elf-plt-reloc-sink-scan, elf-cwe120-plt-analysis | source-parser-state-machine-oob, elf-plt-reloc-sink-scan, elf-cwe120-plt-analysis | source-parser-state-machine-oob, elf-plt-reloc-sink-scan, elf-cwe120-plt-analysis | 7 | False | mixed_task_relevance | source-parser-state-machine-oob | elf-plt-reloc-sink-scan, elf-cwe120-plt-analysis |  | positive | keep_skill_but_prune_extraneous_selection |
| tcpdump-4.9.1-cve-2018-14469 | blind-skillclaw-inline-guarded | 10/10 | Y | Y | Y | Y | Y | passed | behavior-backed | source-parser-state-machine-oob, elf-plt-reloc-sink-scan, elf-cwe120-plt-analysis | source-parser-state-machine-oob, elf-plt-reloc-sink-scan, elf-cwe120-plt-analysis | source-parser-state-machine-oob, elf-plt-reloc-sink-scan, elf-cwe120-plt-analysis | 19 | False | mixed_task_relevance | source-parser-state-machine-oob | elf-plt-reloc-sink-scan, elf-cwe120-plt-analysis |  | positive | keep_skill_but_prune_extraneous_selection |

## 说明

- `Y/N` 列表示该维度是否命中案例真值。
- `confirmation_maturity` 表示当前案例声称达到的确认层级，例如 `behavior-backed` 或 `intermediate-confirmed-path`。
- `confirmation_current_claim` 与 `confirmation_accepted_runtime_claim` 可能不同：前者是当前工程上诚实的总体表述，后者是当前接受的运行时确认路径。
- `skill_relevance=only_infra_skills` 表示 SkillClaw 选到的是框架/自检类技能，而不是任务相关漏洞分析技能。
- `relevant_skills / mismatched_skills / infra_skills` 用来直接观察一次 run 里哪些技能与任务相关、哪些明显跑偏、哪些只是框架自检类技能。
- `decision/action` 是后续技能演化的反馈信号，不等于人工最终结论。
