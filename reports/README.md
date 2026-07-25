# Reports

`reports/` 用来保存当前有效结果、关键案例证据和历史归档。

一句话区分：

- `docs/`：给人读的说明、计划、周报、操作记录
- `reports/`：给结果复核、数据汇总、论文取数用的产物

## 目录说明

- `current/`
  - 当前主结果集
  - 包含 runset、结果矩阵、成熟度、技能反馈、技能门控
- `runs/`
  - 当前仍在引用的运行结果目录
  - 目前主要看 `runs/confirmations/`
- `evidence/`
  - 需要长期保留的关键案例证据
- `publication/`
  - 面向论文整理的清单、对比输入和导出结果
- `archive/`
  - 历史运行归档
  - 只用于追溯，不再作为当前工程状态的默认依据

## `runs/confirmations/` 中常见文件

- `manifest.json`
  - 这次运行的总体元信息
- `run_index.json`
  - 该目录下有哪些过程文件和结果文件
- `agent.json`
  - 原始模型输出抽取后的结构化结果
- `validation.json`
  - validator 执行结果
- `compare.json` / `compare.md`
  - 两种运行方式之间的对比结果
- `final.json`
  - 标准最终记录
- `final-enriched.json`
  - 在 `final.json` 基础上补充注入、反馈或额外字段后的结果

## 推荐阅读顺序

如果只想看“现在做到哪一步了”，按这个顺序看：

1. `current/runset.md`
2. `current/result_matrix.md`
3. `current/benchmark_status.md`
4. `current/skill_feedback.md`
5. `current/skill_gate.md`

如果要看某个案例的长期证据，再看：

- `evidence/cases/`

如果要追溯旧实验，再看：

- `archive/legacy_runs/`

## 关于历史路径和旧命名

部分 `final*.json`、`manifest.json`、`run_index.json` 里，
可能仍保留历史执行路径或旧脚本名，例如：

- `/home/li/skillclaw-eval/...`
- 旧时代的 `experiment_*`
- 早期确认脚本名

这些内容属于**历史运行证据**的一部分，不代表当前活跃工程结构仍依赖旧目录。
凡是以当前仓库结构为准时，应优先看：

- `benchmarks/`
- `evaluation/`
- `reports/current/`
- `reports/runs/confirmations/`

## 当前原则

`reports/` 里只允许三类内容继续增长：

1. 当前主结果集
2. 必要的案例证据
3. 已封存的历史归档

不再往这里堆零散临时笔记、临时脚本输出或未归类中间文件。

