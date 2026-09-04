# Paper Workspace

`paper/` 目录现在按下面几类内容组织：

## 阅读入口

论文工作区的推荐入口是 `paper/package_20260824/README.md`。其中：

- `package_20260824/manuscript/arxiv/` 是当前 arXiv 概念占位稿；
- `package_20260824/manuscript/elsarticle/` 是较早的完整工程论文稿；
- `package_20260824/support/` 是面向论文整理的支撑材料；
- `materials_20260824/` 是带来源语义的材料快照，不应与支撑包按文件名直接合并。

根目录不再保留论文源码和 PDF；当前论文源码、说明和编译产物统一收口到 package。
- 当前论文支撑材料
  - `paper/materials_20260824/`
- 对外打包快照
  - `paper/package_20260824/`
- 本地构建与历史归档
  - `paper/archive/`

约定如下：

- 根目录主要保留工作区说明；论文源码、参考文献和编译产物统一放在 package 下。
- LaTeX 构建副产物（如 `.aux`、`.bbl`、`.blg`、`.log`、`.out`、`.spl`）不再长期留在根目录，统一进入 `paper/archive/`。
- 大体积原始会话 `jsonl` 统一只保留在 `reports/current/` 下；`paper/materials_20260824/` 和 `paper/package_20260824/` 只保留引用、摘要和整理结果，不再复制原始大文件副本。
