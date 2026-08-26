# 当前 Runset

清单名：`skillclaw-remote-blind-regression-v2`
用途：`engineering-remote-blind-regression-six-case`
是否仅论文子集：`False`
记录数：6

## 适用性说明

这份 runset 只收录当前用于工程回归的远端 blind 运行结果。它的目标是检查 SkillClaw 注入、远端执行、validator 确认和技能反馈闭环是否真实打通，而不是直接充当论文最终基准。

## 收录记录

| case_id | mode | score | confirmation | confirmation_maturity | benchmark_maturity | benchmark_tier | publication_ready | source_type | source_path | selected_skills | skill_relevance | record |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| giflib-5.1.2-cve-2016-3977 | blind-skillclaw-inline-guarded | 8/10 |  | asan-backed | current | publication-ready | True | record | `runtime/imports/remote_vm/giflib-paper-20260801a/giflib-paper-20260801a-final-enriched.json` | source-parser-state-machine-oob, elf-cwe120-plt-analysis | no_task_relevant_skill | `runtime/imports/remote_vm/giflib-paper-20260801a/giflib-paper-20260801a-final-enriched.json` |
| libxml2-2.9.4-cve-2017-8872 | blind-skillclaw-inline-guarded | 8/10 |  | logic-confirm | confirmed | current-confirmation | False | record | `runtime/imports/remote_vm/libxml2-paper-20260801a/libxml2-paper-20260801a-final-enriched.json` | source-parser-state-machine-oob, elf-cwe120-plt-analysis | mixed_task_relevance | `runtime/imports/remote_vm/libxml2-paper-20260801a/libxml2-paper-20260801a-final-enriched.json` |
| tcpdump-4.9.1-cve-2018-14469 | blind-skillclaw-inline-guarded | 2/10 |  | behavior-backed | confirmed | current-confirmation | False | record | `runtime/imports/remote_vm/tcpdump-paper-20260801a/tcpdump-paper-20260801a-final-enriched.json` | source-parser-state-machine-oob, elf-cwe120-plt-analysis | mixed_task_relevance | `runtime/imports/remote_vm/tcpdump-paper-20260801a/tcpdump-paper-20260801a-final-enriched.json` |
| libarchive-3.8.0-cve-2025-60753 | blind-skillclaw-inline-guarded | 10/10 |  | behavior-backed | confirmed | current-confirmation | True | record | `runtime/imports/remote_vm/libarchive-paper-20260802a/libarchive-paper-20260802a-final-enriched.json` | elf-cwe120-plt-analysis | no_task_relevant_skill | `runtime/imports/remote_vm/libarchive-paper-20260802a/libarchive-paper-20260802a-final-enriched.json` |
| tcpdump-4.9.1-cve-2017-13031 | blind-skillclaw-inline-guarded | 10/10 |  | behavior-backed | confirmed | current-confirmation | False | record | `runtime/imports/remote_vm/tcpdump13031-paper-20260802a/tcpdump13031-paper-20260802a-final-enriched.json` | source-parser-state-machine-oob, elf-cwe120-plt-analysis | mixed_task_relevance | `runtime/imports/remote_vm/tcpdump13031-paper-20260802a/tcpdump13031-paper-20260802a-final-enriched.json` |
| exiv2-0.26-cve-2017-17725 | blind-skillclaw-inline-guarded | 6/10 |  | intermediate-confirmed-path | confirmed | candidate | False | record | `runtime/imports/remote_vm/exiv2-paper-20260802a/exiv2-paper-20260802a-final-enriched.json` | source-parser-state-machine-oob, elf-cwe120-plt-analysis | mixed_task_relevance | `runtime/imports/remote_vm/exiv2-paper-20260802a/exiv2-paper-20260802a-final-enriched.json` |

