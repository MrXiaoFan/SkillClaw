# Publication Inputs

这里仅保留面向论文或对外整理的“可再生协议文件”，不长期堆派生报表。

## 保留内容

- `runset_manifest.json`
  - 定义发布候选子集包含哪些 case 和 run
- `compare_manifest.json`
  - 定义发布候选子集上的成对比较协议

## 不长期保留的派生内容

下面这些都可以按需重新生成，因此不作为长期主树文件保留：

- `runset.md`
- `matrix.md` / `matrix.csv`
- `skill_feedback.md` / `skill_feedback.csv`
- `skill_feedback_bundle.md` / `skill_feedback_bundle.json`
- `skill_gate.md` / `skill_gate.json`
- `compare.md` / `compare.csv`
- `generated/compare_runs/`

## 重新生成入口

- 发布子集 runset：
  - `evaluation/reporting/publication/build_publication_runset.py`
- 发布子集 compare 协议：
  - `evaluation/reporting/publication/build_publication_compare_manifest.py`
- 发布子集 compare 表：
  - `evaluation/reporting/publication/build_publication_compare_table.py`
