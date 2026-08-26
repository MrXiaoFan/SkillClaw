# F453 Skill Ablation Summary (2026-08-15)

研究对象：`f453-httpd-cmdinject-formWriteFacMac`

目标：在同一个 firmware blind case 上，固定数据集、VM、模型与运行链路，只改变服务端 skill 条件，观察分析路径、最终结论和闭环反馈是否发生可解释变化。

## 对照条件

| 条件 | 服务端 skill 条件 | 实际选中 skill | score | 结果摘要 |
| --- | --- | --- | ---: | --- |
| A | `disable` | 无 | 8.0 | 跑偏到 `formexeCommand / CVE-2018-5767` |
| B | `force_names=tenda-httpd-goform-execommand-triage` | `tenda-httpd-goform-execommand-triage` | 8.0 | 仍然跑偏到 `formexeCommand / CVE-2018-5767` |
| C | `force_names=embedded-cgi-command-injection-triage` | `embedded-cgi-command-injection-triage` | 6.0 | 更早跑偏到 `/goform/ate / TendaAte` |
| D | `force_names=embedded-cgi-command-injection-triage` + `evolve-after-run` | `embedded-cgi-command-injection-triage` | 0.0 | 该次 run 自身失败，但成功触发 `candidate -> gate -> published` |
| E | 自然检索 + `evolve-after-run` | 无 | 8.0 | 收窄后的 live skill 未被自然选中，模型再次跑偏到 `formexeCommand / CVE-2018-5767` |

## 关键观察

1. 这不是“加 skill 一定更好”的情况。  
   在 F453 上，强制注入更泛化的 `embedded-cgi-command-injection-triage` 后，分数从 8.0 降到 6.0，说明不合适的 skill 会主动改变分析方向，而且可能带来负效果。

2. 当前 case 上，Tenda 历史先验很强。  
   无 skill 与强制 Tenda skill 两组都落到 `formexeCommand / CVE-2018-5767`，说明模型会被已有显著字符串和既有漏洞原型牵引。

3. server-side skill 注入链路确实会影响推理。  
   条件 C 从 `formexeCommand` 进一步偏到 `/goform/ate / TendaAte`，说明注入并不是“只在记录里出现”，而是真的改变了模型分析路径。

4. “工程闭环已通”与“目标 case 已被 skill 改善”是两件不同的事。  
   条件 D 已证明 `run -> feedback -> candidate -> gate -> published` 可以真实发生；但条件 E 说明，当前 live skill 还没有把自然检索带到 `formWriteFacMac` 这条正确路径上。

## 当前结论

- SkillClaw 的服务端 skill 注入是“真生效”的；
- Evolve + gate + publish 这条后半段链路至少已有一条真实正例；
- 但 F453 这个 case 上，当前 live skill 还不足以证明“有它才能找到漏洞”；
- 下一步更值得做的是“弱 skill / 退化 skill / 目标 skill”的必要性实验，而不是继续堆更泛化的 firmware skill。

## 结果文件

- 详细实验表：[`f453_run_table_20260815.md`](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260815/f453_run_table_20260815.md)
- CSV 数据：[`f453_run_table_20260815.csv`](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260815/f453_run_table_20260815.csv)
- 周报：[`weekly_report_20260815.md`](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260815/weekly_report_20260815.md)
