# 技能反馈 Bundle

这份文件汇总了可直接供 evolver 消费的、技能级别维度反馈。

| skill | gate | runs | relevant | mismatched | infra | mean_score | localization | cve_hit | cve_miss | validator_passed | artifact_generated | artifact_exec | directives | templates |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| elf-cwe120-plt-analysis | demote | 3 | 0 | 3 | 0 | 0.6 | 2 | 0 | 2 | 3 | 3 | 3 | 保留有价值的定位指导，但要补上独立的 CVE 身份识别段落和不确定性回退。; 增加更窄的触发条件，减少过度选中; 把源码定位与精确 CVE 识别分开；只有在 advisory、patch 或版本范围证据存在时，才能命名 CVE。; 把证据检查清单明确写进技能; 收紧检索条件，或重命名技能，让它不再被当前任务族误选; 补充规则：只有在 advisory、patch 或版本元数据支持时，才能输出精确 CVE | cve_identity_miss |
| source-parser-state-machine-oob | revise | 3 | 2 | 1 | 0 | 0.6 | 2 | 0 | 2 | 3 | 3 | 3 | 保留有价值的定位指导，但要补上独立的 CVE 身份识别段落和不确定性回退。; 修改技能内容，减少误导性步骤或表述; 增加更窄的触发条件，减少过度选中; 把源码定位与精确 CVE 识别分开；只有在 advisory、patch 或版本范围证据存在时，才能命名 CVE。; 把证据检查清单明确写进技能; 检查负向案例，删除或收窄会造成误导的流程步骤。; 补充规则：只有在 advisory、patch 或版本元数据支持时，才能输出精确 CVE | cve_identity_miss |
