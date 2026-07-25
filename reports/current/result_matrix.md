# 当前结果矩阵

生成时间：2026-07-25 15:16:57
记录数：5

| case_id | mode | score_text | cve_hit | file_hit | function_hit | evidence_hit | root_cause_hit | validation | confirmation_maturity | selected_skills | first_selected_skills | latest_selected_skills | injection_turns | injection_changed | skill_relevance | decision | action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| giflib-5.1.2-cve-2016-3977 | skillclaw-inline-guarded | 10/10 | Y | Y | Y | Y | Y | passed | asan-backed | source-parser-state-machine-oob, ida-headless-cwe120-sink-analysis, idalib-headless-batch-diagnosis | source-parser-state-machine-oob, ida-headless-cwe120-sink-analysis, idalib-headless-batch-diagnosis | source-parser-state-machine-oob, ida-headless-cwe120-sink-analysis, idalib-headless-batch-diagnosis | 7 | False | no_task_relevant_skill | neutral | inspect_retrieval_before_promoting_skill |
| libarchive-3.8.0-cve-2025-60753 | skillclaw-inline-guarded | 10/10 | Y | Y | Y | Y | Y | passed | behavior-backed | source-parser-state-machine-oob, idalib-headless-batch-diagnosis, ida-headless-cwe120-sink-analysis | source-parser-state-machine-oob, idalib-headless-batch-diagnosis, ida-headless-cwe120-sink-analysis | source-parser-state-machine-oob, idalib-headless-batch-diagnosis, ida-headless-cwe120-sink-analysis | 20 | False | no_task_relevant_skill | neutral | inspect_retrieval_before_promoting_skill |
| libxml2-2.9.4-cve-2017-8872 | skillclaw-inline-guarded | 10/10 | Y | Y | Y | Y | Y | passed | logic-confirm | source-parser-state-machine-oob, vuln-hunting, elf-cwe120-firmware-triage | source-parser-state-machine-oob, vuln-hunting, elf-cwe120-firmware-triage | source-parser-state-machine-oob, vuln-hunting, elf-cwe120-firmware-triage | 32 | False | mixed_task_relevance | positive | keep_skill_but_prune_extraneous_selection |
| tcpdump-4.9.1-cve-2017-13031 | skillclaw-inline-guarded | 10/10 | Y | Y | Y | Y | Y | passed | behavior-backed | source-parser-state-machine-oob, vuln-hunting, verify-rootfs-full-enumeration | source-parser-state-machine-oob, vuln-hunting, verify-rootfs-full-enumeration | source-parser-state-machine-oob, vuln-hunting, verify-rootfs-full-enumeration | 11 | False | mixed_task_relevance | positive | keep_skill_but_prune_extraneous_selection |
| tcpdump-4.9.1-cve-2018-14469 | skillclaw-inline-guarded | 10/10 | Y | Y | Y | Y | Y | passed | behavior-backed | source-parser-state-machine-oob, vuln-hunting, verify-rootfs-full-enumeration | source-parser-state-machine-oob, vuln-hunting, verify-rootfs-full-enumeration | source-parser-state-machine-oob, vuln-hunting, verify-rootfs-full-enumeration | 18 | False | mixed_task_relevance | positive | keep_skill_but_prune_extraneous_selection |

## 说明

- `Y/N` 列表示该维度是否命中案例真值。
- `confirmation_maturity` 表示当前案例声称达到的确认层级，例如 `behavior-backed` 或 `intermediate-confirmed-path`。
- `confirmation_current_claim` 与 `confirmation_accepted_runtime_claim` 可能不同：前者是当前工程上诚实的总体表述，后者是当前接受的运行时确认路径。
- `skill_relevance=only_infra_skills` 表示 SkillClaw 选到的是框架/自检类技能，而不是任务相关漏洞分析技能。
- `decision/action` 是后续技能演化的反馈信号，不等于人工最终结论。
