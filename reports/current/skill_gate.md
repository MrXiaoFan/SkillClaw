# 技能 Gate 报告

这份报告把 validator 支持的技能反馈转换成保守的 gate 决策。
它不会自动发布、改写或删除任何技能。

| skill | gate_decision | selected_count | positive | neutral | negative | mean_score | cve_hits | file_hits | function_hits | reasons | suggestions |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| source-parser-state-machine-oob | revise | 5 | 1 | 3 | 1 | 0.68 | 1 | 3 | 4 | 存在 1 次负向反馈; 并非每次被选中的运行都命中了所需证据; 共有 1 次运行选中了该技能，但与任务并不对齐 | 修改技能内容，减少误导性步骤或表述; 把证据检查清单明确写进技能; 增加更窄的触发条件，减少过度选中 |
| elf-cwe120-plt-analysis | demote | 6 | 0 | 6 | 0 | 0.733 | 2 | 4 | 5 | 共有 6 次错配选中，且没有任务对齐证据; 并非每次被选中的运行都命中了所需证据; 共有 6 次运行选中了该技能，但与任务并不对齐 | 收紧检索条件，或重命名技能，让它不再被当前任务族误选; 把证据检查清单明确写进技能; 增加更窄的触发条件，减少过度选中 |

## Gate 含义

- `promote`：当前证据较强，可考虑提高检索优先级或纳入更广基准集继续验证。
- `keep`：已有正向证据，但样本还不够，不宜直接提升。
- `revise`：定位可能有帮助，但证据缺口、CVE 识别错误或失败案例要求先修改。
- `demote`：该技能大概率与当前任务族不相关，或会带来误导。
- `insufficient_evidence`：样本数太少，暂时不能判断。
