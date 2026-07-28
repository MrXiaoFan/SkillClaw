# 技能 Gate 报告

这份报告把 validator 支持的技能反馈转换成保守的 gate 决策。
它不会自动发布、改写或删除任何技能。

| skill | gate_decision | selected_count | positive | neutral | negative | mean_score | cve_hits | file_hits | function_hits | reasons | suggestions |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| source-parser-state-machine-oob | keep | 4 | 2 | 2 | 0 | 0.875 | 4 | 3 | 3 | 2 次正向样本，平均分 0.875; 共有 1 次运行选中了该技能，但与任务并不对齐; 共有 4 次 validator 通过 | 暂时保留启用，但在提升前仍需更多案例; 增加更窄的触发条件，减少过度选中 |
| elf-plt-reloc-sink-scan | demote | 3 | 0 | 3 | 0 | 0.833 | 3 | 2 | 2 | 共有 3 次错配选中，且没有任务对齐证据; 共有 3 次运行选中了该技能，但与任务并不对齐; 共有 3 次 validator 通过 | 收紧检索条件，或重命名技能，让它不再被当前任务族误选; 增加更窄的触发条件，减少过度选中 |
| cwe120-analysis-verification | demote | 2 | 0 | 2 | 0 | 0.75 | 2 | 1 | 1 | 共有 2 次错配选中，且没有任务对齐证据; 共有 2 次运行选中了该技能，但与任务并不对齐; 共有 2 次 validator 通过 | 收紧检索条件，或重命名技能，让它不再被当前任务族误选; 增加更窄的触发条件，减少过度选中 |
| elf-cwe120-plt-analysis | insufficient_evidence | 1 | 0 | 1 | 0 | 1.0 | 1 | 1 | 1 | 仅有 1 次样本，低于最少要求 2; 共有 1 次运行选中了该技能，但与任务并不对齐; 共有 1 次 validator 通过 | 先补更多 benchmark 运行，再决定是否调整其状态; 增加更窄的触发条件，减少过度选中 |
| verify-rootfs-full-enumeration | insufficient_evidence | 1 | 0 | 1 | 0 | 1.0 | 1 | 1 | 1 | 仅有 1 次样本，低于最少要求 2; 共有 1 次运行选中了该技能，但与任务并不对齐; 共有 1 次 validator 通过 | 先补更多 benchmark 运行，再决定是否调整其状态; 增加更窄的触发条件，减少过度选中 |
| vuln-hunting | insufficient_evidence | 1 | 0 | 1 | 0 | 1.0 | 1 | 1 | 1 | 仅有 1 次样本，低于最少要求 2; 共有 1 次运行选中了该技能，但与任务并不对齐; 共有 1 次 validator 通过 | 先补更多 benchmark 运行，再决定是否调整其状态; 增加更窄的触发条件，减少过度选中 |

## Gate 含义

- `promote`：当前证据较强，可考虑提高检索优先级或纳入更广基准集继续验证。
- `keep`：已有正向证据，但样本还不够，不宜直接提升。
- `revise`：定位可能有帮助，但证据缺口、CVE 识别错误或失败案例要求先修改。
- `demote`：该技能大概率与当前任务族不相关，或会带来误导。
- `insufficient_evidence`：样本数太少，暂时不能判断。
