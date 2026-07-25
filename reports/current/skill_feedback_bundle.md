# 技能反馈 Bundle

这份文件汇总了可直接供 evolver 消费的、技能级别维度反馈。

| skill | gate | runs | relevant | mismatched | infra | mean_score | localization | cve_hit | cve_miss | validator_passed | artifact_generated | artifact_exec | directives | templates |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| vuln-hunting | demote | 3 | 0 | 3 | 0 | 1.0 | 3 | 3 | 0 | 3 | 2 | 2 | reduce over-selection by adding narrower trigger conditions; tighten retrieval or rename the skill so it is not selected for this task family |  |
| ida-headless-cwe120-sink-analysis | demote | 2 | 0 | 2 | 0 | 1.0 | 2 | 2 | 0 | 2 | 2 | 2 | reduce over-selection by adding narrower trigger conditions; tighten retrieval or rename the skill so it is not selected for this task family |  |
| idalib-headless-batch-diagnosis | demote | 2 | 0 | 2 | 0 | 1.0 | 2 | 2 | 0 | 2 | 2 | 2 | reduce over-selection by adding narrower trigger conditions; tighten retrieval or rename the skill so it is not selected for this task family |  |
| verify-rootfs-full-enumeration | demote | 2 | 0 | 2 | 0 | 1.0 | 2 | 2 | 0 | 2 | 2 | 2 | reduce over-selection by adding narrower trigger conditions; tighten retrieval or rename the skill so it is not selected for this task family |  |
| elf-cwe120-firmware-triage | insufficient_evidence | 1 | 0 | 1 | 0 | 1.0 | 1 | 1 | 0 | 1 | 0 | 0 | collect more benchmark runs before changing publication status; reduce over-selection by adding narrower trigger conditions |  |
| source-parser-state-machine-oob | promote | 5 | 3 | 2 | 0 | 1.0 | 5 | 5 | 0 | 5 | 4 | 4 | reduce over-selection by adding narrower trigger conditions; 可进入更广基准集继续验证；若后续没有明显证据缺口，可考虑提高默认检索优先级 |  |
