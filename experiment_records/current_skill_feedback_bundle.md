# 技能反馈 Bundle

这份文件汇总了可直接供 evolver 消费的、技能级别维度反馈。

| skill | gate | runs | relevant | mismatched | infra | mean_score | localization | cve_hit | cve_miss | validator_passed | artifact_generated | artifact_exec | directives | templates |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| elf-plt-reloc-sink-scan | demote | 3 | 0 | 3 | 0 | 0.833 | 2 | 3 | 0 | 3 | 3 | 3 | 增加更窄的触发条件，减少过度选中; 收紧检索条件，或重命名技能，让它不再被当前任务族误选 |  |
| cwe120-analysis-verification | demote | 2 | 0 | 2 | 0 | 0.75 | 1 | 2 | 0 | 2 | 2 | 2 | 增加更窄的触发条件，减少过度选中; 收紧检索条件，或重命名技能，让它不再被当前任务族误选 |  |
| elf-cwe120-plt-analysis | insufficient_evidence | 1 | 0 | 1 | 0 | 1.0 | 1 | 1 | 0 | 1 | 1 | 1 | 先补更多 benchmark 运行，再决定是否调整其状态; 增加更窄的触发条件，减少过度选中 |  |
| verify-rootfs-full-enumeration | insufficient_evidence | 1 | 0 | 1 | 0 | 1.0 | 1 | 1 | 0 | 1 | 1 | 1 | 先补更多 benchmark 运行，再决定是否调整其状态; 增加更窄的触发条件，减少过度选中 |  |
| vuln-hunting | insufficient_evidence | 1 | 0 | 1 | 0 | 1.0 | 1 | 1 | 0 | 1 | 1 | 1 | 先补更多 benchmark 运行，再决定是否调整其状态; 增加更窄的触发条件，减少过度选中 |  |
| source-parser-state-machine-oob | keep | 4 | 3 | 1 | 0 | 0.875 | 3 | 4 | 0 | 4 | 4 | 4 | 增加更窄的触发条件，减少过度选中; 暂时保留启用，但在提升前仍需更多案例 |  |
