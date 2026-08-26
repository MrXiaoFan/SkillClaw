# Reports

`reports/` 用来保存实验结果、案例证据、发布整理物和历史归档。

一句话区分：

- `docs/`：给人读的计划、交接、操作说明、研究讨论
- `reports/`：给结果复核、实验汇总、论文取数、历史追溯用的数据与材料

## 目录说明

- `current/`
  - 当前仍在使用的结果汇总与阶段材料
  - 既包含“活的工具输出”，也包含阶段 briefing
- `runs/`
  - 结构化保存的运行结果
- `evidence/`
  - 需要长期保留的案例级证据
- `publication/`
  - 面向论文和公开整理的导出物
- `archive/`
  - 历史归档，不再作为当前状态默认入口

## 当前建议入口

如果想快速判断“现在工程和实验做到哪一步了”，建议按这个顺序看：

1. [current/README.md](current/README.md)
2. [../AGENT_HANDOFF.md](../AGENT_HANDOFF.md)
3. [../docs/handoff/20260820/01_necessity_plan_done_and_next.md](../docs/handoff/20260820/01_necessity_plan_done_and_next.md)
4. [../docs/plans/work_plan_20260820.md](../docs/plans/work_plan_20260820.md)

## 关于 `current/` 顶层那些旧名字文件

`current/` 顶层仍然保留：

- `runset.md`
- `result_matrix.md`
- `benchmark_status.md`
- `skill_feedback.md`
- `skill_gate.md`
- `skill_gate.json`
- `skill_feedback_bundle.md`
- `skill_feedback_bundle.json`
- `runset_manifest.json`

这些不是单纯历史垃圾。它们仍然被：

- 部分汇总脚本
- publication 导出流程
- 测试
- 旧 handoff / 旧周报材料

所引用。所以当前策略不是直接删除，而是：

1. 保留它们作为“工具链兼容输出”
2. 把真正的阶段性实验说明放进 `briefing_*` 或专门的验证记录中
3. 逐步减少新材料继续堆在顶层

## 原则

后续往 `reports/` 里新增内容时，优先满足这三类：

1. 当前主实验的规范化结果
2. 可复核的案例证据
3. 已明确归档用途的历史记录

不要再往这里堆：

- 一次性分析脚本输出
- 临时排查笔记
- 未说明用途的中间文本
