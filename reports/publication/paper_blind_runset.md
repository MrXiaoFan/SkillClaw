# 当前 Runset

清单名：`skillclaw-paper-blind-runset-v1`
用途：`paper-blind-remote-validation-evolution`
是否仅论文子集：`True`
记录数：3

## 适用性说明

该 runset 只收录 2026 年 8 月 1 日通过远端 VM、blind prompt、SkillClaw 注入与 validator 确认链路完成的三组代表性运行，用于论文中的闭环可行性与失败模式分析。

## 收录记录

| case_id | mode | score | validation | confirmation | benchmark_maturity | benchmark_tier | publication_ready | source_type | source_path | selected_skills | skill_relevance | record |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| giflib-5.1.2-cve-2016-3977 | blind-skillclaw-inline-guarded | 8/10 | passed | asan-backed | current | publication-ready | True | record | `runtime/imports/remote_vm/giflib-paper-20260801a/giflib-paper-20260801a-final-enriched.json` | source-parser-state-machine-oob, elf-cwe120-plt-analysis | no_task_relevant_skill | `runtime/imports/remote_vm/giflib-paper-20260801a/giflib-paper-20260801a-final-enriched.json` |
| libxml2-2.9.4-cve-2017-8872 | blind-skillclaw-inline-guarded | 8/10 | passed | logic-confirm | confirmed | current-confirmation | False | record | `runtime/imports/remote_vm/libxml2-paper-20260801a/libxml2-paper-20260801a-final-enriched.json` | source-parser-state-machine-oob, elf-cwe120-plt-analysis | mixed_task_relevance | `runtime/imports/remote_vm/libxml2-paper-20260801a/libxml2-paper-20260801a-final-enriched.json` |
| tcpdump-4.9.1-cve-2018-14469 | blind-skillclaw-inline-guarded | 2/10 | passed | behavior-backed | confirmed | current-confirmation | False | record | `runtime/imports/remote_vm/tcpdump-paper-20260801a/tcpdump-paper-20260801a-final-enriched.json` | source-parser-state-machine-oob, elf-cwe120-plt-analysis | mixed_task_relevance | `runtime/imports/remote_vm/tcpdump-paper-20260801a/tcpdump-paper-20260801a-final-enriched.json` |

