# 当前 Runset

清单名：`skillclaw-remote-blind-regression-v1`
用途：`engineering-remote-blind-regression`
是否仅论文子集：`False`
记录数：4

## 适用性说明

这份 runset 只收录当前用于工程回归的远端 blind 运行结果。它的目标是检查 SkillClaw 注入、远端执行、validator 确认和技能反馈闭环是否真实打通，而不是直接充当论文最终基准。

## 收录记录

| case_id | mode | score | validation | confirmation | benchmark_maturity | benchmark_tier | publication_ready | source_type | source_path | selected_skills | skill_relevance | record |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| giflib-5.1.2-cve-2016-3977 | blind-skillclaw-inline-guarded | 10/10 | passed | asan-backed | current | publication-ready | True | record | `runtime/imports/remote_vm/giflib-5.1.2-cve-2016-3977-blind-skillclaw-inline-guarded-20260728-151445/giflib-5.1.2-cve-2016-3977-blind-skillclaw-inline-guarded-20260728-151445-final-final-enriched.json` | source-parser-state-machine-oob, vuln-hunting, verify-rootfs-full-enumeration | no_task_relevant_skill | `runtime/imports/remote_vm/giflib-5.1.2-cve-2016-3977-blind-skillclaw-inline-guarded-20260728-151445/giflib-5.1.2-cve-2016-3977-blind-skillclaw-inline-guarded-20260728-151445-final-final-enriched.json` |
| libxml2-2.9.4-cve-2017-8872 | blind-skillclaw-inline-guarded | 10/10 | passed | logic-confirm | confirmed | current-confirmation | False | record | `runtime/imports/remote_vm/libxml2-2.9.4-cve-2017-8872-blind-skillclaw-inline-guarded-20260728-154511/libxml2-2.9.4-cve-2017-8872-blind-skillclaw-inline-guarded-20260728-154511-final-final-enriched.json` | source-parser-state-machine-oob, cwe120-analysis-verification, elf-plt-reloc-sink-scan | mixed_task_relevance | `runtime/imports/remote_vm/libxml2-2.9.4-cve-2017-8872-blind-skillclaw-inline-guarded-20260728-154511/libxml2-2.9.4-cve-2017-8872-blind-skillclaw-inline-guarded-20260728-154511-final-final-enriched.json` |
| tcpdump-4.9.1-cve-2018-14469 | blind-skillclaw-inline-guarded | 10/10 | passed | behavior-backed | confirmed | current-confirmation | False | record | `runtime/imports/remote_vm/tcpdump-4.9.1-cve-2018-14469-blind-skillclaw-inline-guarded-20260728-160446/tcpdump-4.9.1-cve-2018-14469-blind-skillclaw-inline-guarded-20260728-160446-final-final-enriched.json` | source-parser-state-machine-oob, elf-plt-reloc-sink-scan, elf-cwe120-plt-analysis | mixed_task_relevance | `runtime/imports/remote_vm/tcpdump-4.9.1-cve-2018-14469-blind-skillclaw-inline-guarded-20260728-160446/tcpdump-4.9.1-cve-2018-14469-blind-skillclaw-inline-guarded-20260728-160446-final-final-enriched.json` |
| tcpdump-4.9.1-cve-2017-13031 | blind-skillclaw-inline-guarded | 5/10 | passed | behavior-backed | confirmed | current-confirmation | False | record | `runtime/imports/remote_vm/tcpdump-4.9.1-cve-2017-13031-blind-skillclaw-inline-guarded-20260728-161929/tcpdump-4.9.1-cve-2017-13031-blind-skillclaw-inline-guarded-20260728-161929-final-final-enriched.json` | source-parser-state-machine-oob, cwe120-analysis-verification, elf-plt-reloc-sink-scan | mixed_task_relevance | `runtime/imports/remote_vm/tcpdump-4.9.1-cve-2017-13031-blind-skillclaw-inline-guarded-20260728-161929/tcpdump-4.9.1-cve-2017-13031-blind-skillclaw-inline-guarded-20260728-161929-final-final-enriched.json` |

