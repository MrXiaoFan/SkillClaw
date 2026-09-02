# 新版论文稿分析（2026-09-02）

## 文件关系

当前工作稿为同目录下的 `skill_evolution_blind_vulnerability_analysis_arxiv.tex`，来源为 2026-09-02 用户提供的下载文件。此前工程中的两个版本已保存到：

- `paper/archive/manuscript_snapshot_20260824/skill_evolution_blind_vulnerability_analysis_arxiv_root_20260824.tex`
- `paper/archive/manuscript_snapshot_20260824/skill_evolution_blind_vulnerability_analysis_arxiv_package_20260824.tex`

后续论文修改以 `paper/package_20260824/manuscript/arxiv/` 为工作路径，不再直接把工程根目录 `paper/` 下的旧稿当作当前稿。

## 新稿的研究主线

新稿将问题定义为：漏洞分析 Agent 在看不到漏洞答案的条件下执行任务，如何把一次运行转化为可追溯、可筛选、可验证的可复用 skill，并控制错误经验进入长期 skill 库。论文不把“生成 candidate”本身当作进化成功，而是区分运行证据、反馈构造、candidate 生成、候选准入和后续迁移。

## 新稿已经具备的内容

1. 引言明确解释了为什么漏洞分析需要 skill、为什么 blind 分析中的错误目标和答案泄漏会污染进化信号。
2. 相关工作覆盖 Agent skill、skill induction、skill refinement、验证器和漏洞分析 Agent，并将本文定位为漏洞分析场景中的证据约束型 skill 生命周期。
3. 方法部分给出了 skill 状态、运行结果、归因、candidate、准入和持久化之间的形式化关系，并明确区分“技能改变了行为”和“技能真正提高了未来任务性能”。
4. 系统流程覆盖服务端 skill 暴露、blind run、目标感知评分、外部确认、feedback、candidate 隔离、replay/rerun gate 和 live 发布。
5. 实验部分包含 153-run 控制实验、答案泄漏控制实验、F9K/F453 迁移实验、候选生命周期记录和公开 CVE 来源说明。
6. 结果部分没有把 candidate 生成写成自动提升，而是保留了 candidate 导致负迁移、目标函数漂移和非区分性线索污染等结果。
7. 讨论和限制部分明确说明：当前数据证明了 skill 内容会改变盲分析行为、工程生命周期可以被记录和治理，但尚未证明自动生成的 skill 能稳定改善未见任务。

## 当前稿可使用的主要工程与实验依据

- `reports/publication/paper_blind_runset.md`
- `reports/current/briefing_20260827/clean_f9k_transfer_followup_20260827.md`
- `reports/current/briefing_20260827/clean_f453_transfer_followup_20260827.md`
- `reports/current/briefing_20260827/clean_f9k_transfer_summary_20260827.csv`
- `reports/current/briefing_20260827/clean_f453_transfer_summary_20260827.csv`
- `evaluation/runs/run_heldout_evolved_skill.py`
- `tests/test_heldout_evolved_skill_runner.py`

这些文件中的数字和实验状态优先于旧周报、旧 handoff 和论文中的历史数字。论文中的每个统计量都应回查到原始 CSV 或 JSON，不应凭历史摘要重新计算。

## 需要重点复核的地方

1. 摘要中的 153-run、46.7%、5/45、3/45、decoy 数量及其分母，必须逐项与当前冻结 CSV 核对。
2. 摘要和正文对 F9K/F453 的描述应明确这是迁移实验中的失败或负迁移证据，不能写成稳定提升。
3. “16 public CVE records reported by two team members” 属于项目 provenance 说明，除非有完整清单和可公开核验来源，不应写成独立的算法效果指标。
4. `external confirmation`、`replay gate` 和 `real rerun` 需要保持含义一致：前者确认漏洞结果，后两者用于判断候选是否可以继续进入持久化状态，不能把它们混写成同一种验证。
5. 方法中的归因公式目前是可审计的定性或代理信号，不应表述为已经完成因果识别。
6. 相关工作中的文献条目应逐篇检查真实性、题名、作者、年份和链接；引用清单不能只依赖工程已有的 BibTeX。
7. 实现映射部分应作为复现说明，不应让工程文件名和内部模块细节主导正文叙事。

## 当前论文结论边界

可以主张：在 blind 漏洞分析中，skill 暴露会改变 Agent 的搜索和定位行为；如果运行没有目标、证据或归因约束，错误路径和泄漏信息可能被错误地转化为 skill 进化信号；通过 candidate 隔离、目标感知反馈和准入记录，可以形成可审计的 skill 生命周期。

暂时不能主张：自动生成的 candidate 已经在未参与生成的新漏洞任务上稳定提升发现率；candidate 已经优于人工或 seed skill；当前 gate 已经充分解决技能贡献的因果归因问题。

## 后续论文工作顺序

1. 先冻结实验数字和引用清单，逐项建立正文数字到 CSV/JSON 的对应关系。
2. 再检查摘要、贡献、RQ、结果和结论是否使用同一组证据边界。
3. 补充一张清晰的实验协议表，说明 source、candidate、held-out、no-skill、seed-skill 和 candidate-skill 的关系。
4. 单独说明当前正向证据、负迁移证据和尚未完成的自动演化证据。
5. 最后再做语言压缩和版式调整，不用工程代码细节替代研究问题、实验变量和结果解释。
