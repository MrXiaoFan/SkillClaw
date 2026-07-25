# 当前 Runset

清单名：`skillclaw-confirmation-runset-v1`
用途：`engineering-confirmation-regression`
是否仅论文子集：`False`
记录数：5

## 适用性说明

这份 runset 目前是工程回归集合，还不是纯论文基准集合。部分收录案例仍停留在 behavior-backed 层级，若进入论文表格，仍需要明确标注证据边界。

## 收录记录

| case_id | mode | score | validation | confirmation | benchmark_maturity | benchmark_tier | publication_ready | source_type | source_path | selected_skills | skill_relevance | record |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| giflib-5.1.2-cve-2016-3977 | skillclaw-inline-guarded | 10/10 | passed | asan-backed | current | publication-ready | True | manifest | `reports/runs/confirmations/giflib-confirmation-20260701c/manifest.json` | source-parser-state-machine-oob, ida-headless-cwe120-sink-analysis, idalib-headless-batch-diagnosis | no_task_relevant_skill | `reports/runs/confirmations/giflib-confirmation-20260701c/final-enriched.json` |
| tcpdump-4.9.1-cve-2017-13031 | skillclaw-inline-guarded | 10/10 | passed | behavior-backed | confirmed | current-confirmation | False | manifest | `reports/runs/confirmations/tcpdump-confirmation-20260702a/manifest.json` | source-parser-state-machine-oob, vuln-hunting, verify-rootfs-full-enumeration | mixed_task_relevance | `reports/runs/confirmations/tcpdump-confirmation-20260702a/final-enriched.json` |
| libxml2-2.9.4-cve-2017-8872 | skillclaw-inline-guarded | 10/10 | passed | logic-confirm | confirmed | current-confirmation | False | manifest | `reports/runs/confirmations/libxml2-logic-confirmation-20260705/manifest.json` | source-parser-state-machine-oob, vuln-hunting, elf-cwe120-firmware-triage | mixed_task_relevance | `reports/runs/confirmations/libxml2-logic-confirmation-20260705/final-enriched.json` |
| tcpdump-4.9.1-cve-2018-14469 | skillclaw-inline-guarded | 10/10 | passed | behavior-backed | confirmed | current-confirmation | False | manifest | `reports/runs/confirmations/tcpdump-isakmp-confirmation-20260707/manifest.json` | source-parser-state-machine-oob, vuln-hunting, verify-rootfs-full-enumeration | mixed_task_relevance | `reports/runs/confirmations/tcpdump-isakmp-confirmation-20260707/final-enriched.json` |
| libarchive-3.8.0-cve-2025-60753 | skillclaw-inline-guarded | 10/10 | passed | behavior-backed | confirmed | current-confirmation | True | manifest | `reports/runs/confirmations/libarchive-confirmation-20260707/manifest.json` | source-parser-state-machine-oob, idalib-headless-batch-diagnosis, ida-headless-cwe120-sink-analysis | no_task_relevant_skill | `reports/runs/confirmations/libarchive-confirmation-20260707/final-enriched.json` |

