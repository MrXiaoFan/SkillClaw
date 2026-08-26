# 项目周报（2026-08-09 至 2026-08-15）

## 本周完成工作

### 1. 远端 firmware blind case 的真实实验链路再次打通

本周围绕 `SkillClaw -> Evolve -> gate` 这条主链路，继续做远端 VM 上的真实 blind 实验，并把结果统一回收到本地记录。当前已经能够稳定完成：

`远端 VM 运行 Claude -> 本机 SkillClaw 代理接收请求 -> 服务端代码选择并注入 skill -> 保存会话与最终结果 -> finalize_record 生成反馈 -> Evolve 消费反馈 -> 生成 candidate -> gate 决策`

其中，模型的漏洞分析、候选 skill 修改建议由上游大模型完成；skill 选择、结果归档、反馈抽取、候选管理、gate 决策与发布则由本地代码流程完成。

### 2. 完成一组 F453 固件漏洞 skill 对照实验

本周新增整理了 `f453-httpd-cmdinject-formWriteFacMac` 的 5 轮真实远端实验。实验固定 case、数据集、VM、运行链路，仅改变服务端 skill 条件。

| 条件 | score | 实际选中 skill | 结果摘要 |
| --- | ---: | --- | --- |
| 无 skill | 8.0 | 无 | 跑偏到 `formexeCommand / CVE-2018-5767` |
| 强制 Tenda skill | 8.0 | `tenda-httpd-goform-execommand-triage` | 与无 skill 基本一致 |
| 强制泛化 CGI skill | 6.0 | `embedded-cgi-command-injection-triage` | 更早偏到 `/goform/ate / TendaAte` |
| 强制泛化 CGI skill + evolve | 0.0 | `embedded-cgi-command-injection-triage` | 本轮失败，但形成完整闭环并发布新版本 |
| 自然检索 + evolve | 8.0 | 无 | 收窄后的 live skill 未被自然选中，仍跑偏到 `formexeCommand` |

结果文件：

- [`f453_skill_ablation_20260815.md`](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260815/f453_skill_ablation_20260815.md)
- [`f453_run_table_20260815.md`](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260815/f453_run_table_20260815.md)
- [`f453_run_table_20260815.csv`](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260815/f453_run_table_20260815.csv)

### 3. 拿到一条真实的“candidate -> gate -> published”闭环正例

此前的主要疑问是：实验反馈到底有没有真的进入 Evolve 并改变 skill。  
本周已经确认，`run_id = ...191115` 这轮实验虽然自身输出失败，但它的反馈确实被 Evolve 消费，并生成了候选修改，随后通过 gate，最终发布到了 live skill。

关键证据在：

- [`...191115-final-enriched.json`](/D:/Code/SkillClaw/SkillClaw/runtime/imports/remote_vm/ablation_20260815/f453-httpd-cmdinject-formWriteFacMac-blind-skillclaw-inline-guarded-20260815-191115/f453-httpd-cmdinject-formWriteFacMac-blind-skillclaw-inline-guarded-20260815-191115-final-enriched.json)

其中可见：

- `evolution_handoff.status = handed_off`
- `validation_followup.status = completed`
- candidate job `20260815111221-embedded-cgi-command-injection-triage-298fecee`
- `published_action = merge`

这说明“实验反馈形成 skill 修改”这条工程闭环已经至少有一条真实正例。

## 当前结论

1. **工程闭环已存在。**  
   当前系统已经不是“只记录结果”，而是真的可以把实验结果送入 Evolve，并在 gate 通过后改动 live skill。

2. **但 skill 必要性还没有被证明。**  
   在 F453 上，我们只能证明“skill 会改变分析路径”，还不能证明“只有某个 skill 才能找到正确漏洞”。

3. **当前主要瓶颈从“闭环是否存在”转成了“闭环是否产生正确收益”。**  
   也就是说，后续重点不是再证明工程能跑，而是要证明某个 target skill 的确能让 blind 分析更接近真实漏洞。

## 当前问题

1. **自然检索没有稳定选中目标 skill。**  
   最新一轮自然检索实验 `...193021` 中，收窄后的 live skill 没有被选中，模型仍然回到了 `formexeCommand / CVE-2018-5767` 这条历史路径。

2. **闭环虽通，但收益仍不足。**  
   已发布的新版本 skill 还没有在 F453 上体现出正向收益，因此目前不能声称“skill 进化已经有效提升漏洞分析能力”。

3. **实验解释仍需进一步收紧。**  
   现在最需要的是“弱 skill / 退化 skill / 目标 skill”三类对照，从而找到 skill 起作用的阈值，而不是继续堆更泛化的 firmware skill。

## 下周计划

1. 围绕 F453 继续做“弱 skill / 退化 skill / 自然检索 / 强制 skill”必要性实验。
2. 优先回答“什么时候 skill 真的是必要条件”这个问题。
3. 在工程上继续收紧记录与交接材料，避免新增大量零散脚本和临时文件。
4. 将当前闭环正例与必要性实验结果进一步回填到论文实验设计中。
