# 工程文件收口候选审计（2026-09-03）

本文件记录收口决策和候选。删除前已做引用与 canonical 副本核对；删除操作保留在 Git 历史中。

## 当前建议的 canonical 入口

- 工程计划：`docs/plans/`
- 当前实验报告：`reports/current/`
- 当前 arXiv 概念稿：`paper/package_20260824/manuscript/arxiv/`
- 完整工程论文基础稿：`paper/package_20260824/manuscript/elsarticle/`
- 运行时原始记录：`runtime/`（不得作为论文摘要入口）

## 已完成的差异审计

`paper/materials_20260824/` 与 `paper/package_20260824/support/` 共发现：

- 78 个文件内容完全相同；
- 19 个 case/report 文件内容不同；
- 3 个报告只存在于 `materials_20260824/`。

差异不能按普通重复文件处理。19 个 case 的主要差异是：

- `materials_20260824/cases/` 保留部分 ground-truth/CVE 信息；
- `package_20260824/support/cases/` 对部分 CVE 做了去泄漏处理，适合作为论文包支持副本。

因此当前不应直接删除任一整棵目录，也不应把两边 case 文件机械覆盖。

## 建议候选

### 已完成

1. 根目录旧论文源码、中文说明、bibliography 和 checklist 已删除；对应维护版本保留在
   `paper/package_20260824/manuscript/`。
2. 当前 handoff、论文说明和实验周报的主要入口已切换到 package 路径。
3. 根目录两份旧 PDF 已确认不再作为工作入口，但因当前环境禁止直接删除，暂时保留。

### 低风险

1. 明确 `paper/package_20260824/` 为论文包 canonical 入口。已完成。
2. 对完全相同的 78 个支持文件建立逐文件映射，后续只保留一份工作副本，另一份移入 archive。
3. 保留不同版本的 19 个 case，并在 manifest 中标注 `ground_truth`、`sanitized_support` 等用途。
4. 保留 `materials_20260824/` 独有的 3 个 CVE backfill 文件，直到论文引用核对完成。

### 中风险

1. 根目录旧 arXiv/elsarticle 源码已直接删除，不再移动到 archive。
2. 根目录两份旧 PDF 待环境允许时删除；package 内 PDF 作为保留的编译快照。

### 暂不处理

1. `runtime/imports/remote_vm/` 原始实验树；先建立 primary/diagnostic/heldout/voided manifest。
2. `runtime/records/conversations.jsonl`；catalog/server-catalog 研究仍需追踪真实技能选择。
3. `skillclaw/skill_manager.py` 的字符匹配、topK、catalog 和 server-catalog 代码；它们仍是检索对照实验所需路径。
4. `evolve_server/` 的 legacy compatibility；当前仍有历史记录和对象存储读取需求。

## 当前结论

当前下一步是对明确作废的 runtime 输出做逐组审计。未经确认的历史实验仍保留；尤其不能把去泄漏论文支持副本覆盖回包含 ground truth 的材料目录，也不能把历史 runtime 原始证据当作普通缓存清理。
