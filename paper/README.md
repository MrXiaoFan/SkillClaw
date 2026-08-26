# Paper Workspace

`paper/` 目录现在按下面几类内容组织：

- 当前主稿
  - `paper/skill_evolution_blind_vulnerability_analysis_arxiv.tex`
  - `paper/skillclaw_confirmation_feedback_elsarticle.tex`
- 当前论文支撑材料
  - `paper/materials_20260824/`
- 对外打包快照
  - `paper/package_20260824/`
- 本地构建与历史归档
  - `paper/archive/`

约定如下：

- 根目录下只保留需要人工直接阅读或编辑的主稿、参考文献和说明文件。
- LaTeX 构建副产物（如 `.aux`、`.bbl`、`.blg`、`.log`、`.out`、`.spl`）不再长期留在根目录，统一进入 `paper/archive/`。
- 大体积原始会话 `jsonl` 统一只保留在 `reports/current/` 下；`paper/materials_20260824/` 和 `paper/package_20260824/` 只保留引用、摘要和整理结果，不再复制原始大文件副本。
