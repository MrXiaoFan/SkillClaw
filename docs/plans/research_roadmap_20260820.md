# 研究路线图（Research Roadmap）— 2026-08-20 修订

> 本文档用于长期追踪：先给出一份基于「工程状态（旧版）」批判性复盘的研究总结（按工程架构与脉络），
> 再给出细化的阶段性开发/实验/论文计划。所有实验数字都以原始 CSV 文件为准，不凭记忆。

---

## 零、如何阅读本文档

- 本文档 = 研究总结 + 规划。总结部分（第一、二、三节）帮助任何后续接手的模型/人快速重建认知；
  规划部分（第四、五节）是按优先级串起来、可验收的行动清单。
- 关键诚实前提（来自多份 handoff 反复强调）：**工程闭环存在 ≠ 闭环带来正收益**；
  **"候选已生成" ≠ "技能已有效"**；**"发布已发生" ≠ "发布后变好"**。
  本文档的所有规划都建立在这个边界上，不夸大。

---

## 一、总体目标与研究问题

### 1.1 工程目标
在原生 SkillClaw（本地代理 + 技能注入 + evolve_server 演化/发布）之上，搭建一套面向漏洞分析的
**confirmation-aware 闭环扩展**：

```
benchmark case → blind run → 评分/确认 → feedback → evolve → candidate → gate(real_rerun) → publish
```

### 1.2 学术目标
研究**技能（skill）自进化迭代 × 漏洞分析 × 漏洞验证**三者的闭环，核心科学问题是：

1. 如何让一次漏洞分析的**验证结果**（静态/动态/崩溃/隐藏答案）真正驱动技能的生成与修改，
   而非只积累"听起来合理"的文本反馈；
2. 什么情况下自动产出的技能有效、什么情况下会误导或退化（弱技能把模型带偏到诱饵）；
3. 如何用**可执行的漏洞验证**约束"哪些经验该进入、哪些不该进入可复用技能"（安全/质量门控）。

### 1.3 论文目标
- 目标会议/期刊：Computers & Security（Elsevier，elsarticle 模板）。
- 论文定位：**evidence-grounded skill evolution for vulnerability analysis**——一个可观测、
  可审计的"运行 → 验证 → 技能演化 → 门控发布"生命周期与方法，加上诚实的实证。

---

## 二、工程架构与脉络（按架构追溯当前状态）

### 2.1 分层架构总览

| 层 | 目录/模块 | 职责 | 当前状态 |
| --- | --- | --- | --- |
| 基准层 | `benchmarks/cases/`（27 个 case） | 定义可重复漏洞分析 case + 隐藏答案/ground truth | 基本完成，**存在 1 处复制缺陷待订正** |
| 执行层 | `evaluation/runs/`（run_single/run_remote_case.py） | 本地/远端 VM 执行盲测 | 稳定 |
| 评分层 | `evaluation/runs/score_case_output.py` | 按 case 真值打分（满分 10） | 存在，需配合 function_identity_miss |
| 确认层 | `evaluation/validation/`、`evaluation/confirmation/` | 静态/动态 validator 确认 | artifact 级为主，行为级不足 |
| 整型层 | `evaluation/postprocess/finalize_record.py` | 合并为 final.json | 稳定 |
| 反馈层 | `evaluation/reporting/feedback/build_feedback_bundle.py` | 生成三态 feedback + 技能门控输入 | 已接 function_identity_miss |
| 演化层 | `evolve_server/engines/workflow.py` | 消费反馈、生成 candidate、gate 决策 | 链路通，gate 有 pending 缺陷 |
| 门控层 | `skillclaw/replay_gate_worker.py` | replay/real_rerun 验证 + 接受/发布 | 有根本局限（见 2.3） |
| 资源分层 | `skillspace/live|candidate|share` | 运行库/候选/共享快照分离 | 安全边界正确 |
| 消融实验台 | `runtime/ablation/`（oracle/weak/no + oracle_skills_json + werk） | 隔离、防作弊的三条件盲测 | 本周新增，真实性最佳 |

### 2.2 主链路与关键模块映射

- 技能选取/注入：`inline` 模式由 `skillclaw/skill_manager.py` 的 `_keyword_retrieve_for_inline`
  完成规则式检索（关键字重叠 + 负向词否决 + fallback）；`server-catalog` 由
  `skillclaw/api_server.py` 在服务端调用 selector LLM，并以 family guard/focused fallback
  做可审计约束；`catalog` 模式保留为下游模型 lazy-loading 的兼容/消融条件。
- run 执行：`evaluation/runs/run_remote_case.py`（远端 VM blind）。
- 评分：`score_case_output.py`；确认：`evaluation/confirmation/core.py`。
- 反馈：`build_feedback_bundle.py` + `evaluation/evolution.py:345`（validated handoff）。
- 演化：`evolve_server/engines/workflow.py`；候选：`skillspace/share/.../candidate_skills/`。
- 门控：`skillclaw/replay_gate_worker.py` → gate_jobs / gate_results / gate_decisions；
  发布 → `skillspace/live/`。

### 2.3 gate / 反馈 / 确认 三处既有机制的根本局限（关键）

以下来自「工程状态（旧版）」的批判，**多数在发布后仍部分成立**，规划时必须正视：

1. **评分给错答高分**：按 file/CVE 匹配给分，模型找到同 binary 同类型但有已知 CVE 的其它 handler，
   也能拿 8/10。→ 已用 `function_identity_miss` 缓解，但规则级评分的语义盲区仍在。
2. **确认对错答也判 passed**：confirmation 不严格校验 predicted_functions == GT，artifact 级确认
   对错误 handler 也判 passed。→ 部分缓解，行为级确认仍缺（无固件模拟器）。
3. **gate 的 replay 是 tool-free 的**：`_build_replay_skill_system` 明确"不 emit tool call"，
   验证的不是真实 agent 行为，是给定 evidence 下的文本质量。
4. **gate 不覆盖 description→检索 的影响**：改 description 后不验证"下一轮自然检索还能不能选中"，
   `...193021` 证明改完 description 后检索失效。
5. **无发布后效果追踪 / 无回退**：只证明"发布发生"，未证明"发布后变好"；唯一一次真实发布（v8）
   实际让后续检索更差。
6. **反馈 attribution 是 observational 而非 causal**，`assess_skill_relevance` 只做名称 token 交集，
   不做 trajectory 级对齐。

### 2.4 脉络（How we got here）

```
7.30-8.2   顾通工程起步：giflib 2016-3977 首次端到端闭环
8.3-8.9    拆 validation/gate 职责；新增 firmware case；F453 首轮盲测(16/15)；
           定位评分机制问题，引入 function_identity_miss
8.9-8.15   F453 skill 对照；candidate->gate->publish 一条真实正例(191115=optimize_description,
           但下游为负)；gate 改 non_inferiority+real_rerun
8.15-8.16  整理交接+论文 v2；工程状态双维度分析（旧版批判）；live skill 36 个；
           gate 101 决策/19 发布/82 拒绝/34 pending；orphaned feedback 恶化到 147
8.17-8.20  方案 A：净化 14 case×3 条件×2 轮=84 runs，oracle 97.5%→35.7%（证旧数据作弊）；
           F9K 族内区分型 oracle skill（20%→66.7%）；oracle 作弊核查；
           setpassword 数据集缺陷 100% 确证
```

**脉络主线**：从"证明闭环能跑" → "证明闭环存在但不等于有效" → "把重心从工程转向可验证的科学结论"
（净化 → 揭露旧数据作弊 → 建立可信基线 → 用族内区分回答"怎么写才有效且不泄答案"）。

---

## 三、已做实验总结（按可信度分层标注）

> 重要：**旧「工程状态」与部分 handoff 中引用的 6 case/18 case/213 run 数据，是在未净化/作弊
> 口径下产生的，已被方案 A(84-run) 部分推翻。** 以下按可信度标注。

### 3.1 可信度=中（工程闭环证明，不看命中率）
- giflib 2016-3977 首次端到端；F453 远端 blind 16 run（15 有效、命中 formWriteFacMac 2/15、
  跑偏 formexeCommand 10/15）；candidate→gate→publish 一条真实正例（191115，baseline=0，
  optimize_description，发布后下游为负）。
- **结论**：工程闭环存在；发布链路通；但"发布→变好"未成立。

### 3.2 可信度=高（本周方案 A，净化 + 新模型 deepseek-v4-flash，防作弊）
- 规模：14 case × 3 条件 × 2 轮 = 84 runs，全部完成无丢失。
- 数据（`ablation_results_rerun_model.csv`）：

| 条件 | runs | YES | DECOY | NO | 平均分 |
| --- | ---: | ---: | ---: | ---: | ---: |
| no-skill | 28 | 1 (3.6%) | 9 | 18 | 4.38 |
| weak-skill | 28 | 4 (14.3%) | 12 | 12 | 4.34 |
| oracle-skill | 28 | 10 (35.7%) | 1 | 17 | 6.32 |
- **核心结论**：旧 oracle 97.5% → clean 35.7%（-62pp），证旧 39/40 主要是技能泄答案；
  clean 下 oracle 仍显著高于 no/weak，且几乎不被诱饵带偏、平均分明显更高。

### 3.3 可信度=高（F9K 族内区分型 oracle skill，本周）
- 规模：5 F9K1122 case × oracle × 3 轮 = 15 run（`ablation_results_f9k_distinguish_oracle.csv`）。
- 数据：

| case | 旧 generic-oracle | 新 distinguishing | 新预测 |
| --- | ---: | ---: | --- |
| f9k1122-overflow (formWISP5G) | 2/2 | 3/3 | formWISP5G ✓ |
| f9k1122-crossband (formCrossBandSwitch) | 0/2 | 3/3 | formCrossBandSwitch ✓ |
| f9k1122-wlansetup (formWlanSetup) | 0/2 | 3/3 | formWlanSetup ✓ |
| f9k1122-setpassword (formSetPassword) | 0/2 | 0/3 | formSelfHealing/formWISP5G ✗ |
| f9k1122-setsystemsettings (formSetSystemSettings) | 0/2 | 1/3 | 1 轮 ✓ 后 2 轮跑偏 |
| **汇总** | **2/10 (20%)** | **10/15 (66.7%)** | — |
- **结论**：不写函数名的、基于邻接符号指纹的技能能把模型从家族内显眼 handler 掰回真实目标；
  但 setpassword/setsystemsettings 这组在字符串表层面无区分 token，属数据层不可分。

### 3.4 数据集缺陷（已 100% 确证）
- `f9k1122-webs-overflow-formSetPassword.json` 实为 `formSetSystemSettings.json` 的复制件
  （仅 case_id/notes 不同；ground_truth/blind_workspace/validator 全指向后者；源侧 webs 二进制 MD5 相同）。
- **这不是技能盲区，是 dataset 复制 bug**，必须在出更多数据前订正。

---

## 四、阶段规划（Phase 0-3，按优先级串接，含前置与验收）

> 执行顺序严格 0→1→2→3。**阶段 0 不发车，则阶段 1/3 的数字都是空中楼阁**；
> 阶段 2 不做，论文只能写"闭环存在"、写不了"自进化带来收益"。

### 阶段 0 · 数据可信化（最优先，卡住一切）
**目标**：让后续所有实验站上干净、可复现的统一口径。

| # | 任务 | 做法 | 前置 | 验收 |
| --- | --- | --- | --- | --- |
| 0.1 | 订正 setpassword case | ~~作废；或从真实 vul4 样本重派生~~ **已作废（2026-08-20，path A）**：确认该 case 为 formSetSystemSettings 的字节级复制件，非真实 vul4；已设 include_in_current_runs=false。前路：如需真实 formSetPassword 用例须从 vul4 样本重派生 | — | **已达成**：case 集已剔除重复/无效项 |
| 0.2 | 处理不可分近亲对 | **口径已定（2026-08-20，选「标不可区分类别」）**：凡相邻符号且二进制字符串表 token 完全相同、无法用不泄答案的 skill 区分的近亲对，统一标为「不可区分对」，**不计入 per-function 命中分母**，单独列类别汇报；setpassword 复制件已作废（0.1）。如需真 class 分离须 oracle-only/端点级（不属 clean 实验） | 0.1 | **已达成**：命中口径明确 |
| 0.3 ✅ | 冻结 case 集 + 净化技能版本 | 已登记 `reports/current/freeze_cases_20260820.md`：固定 commit `01f5830` + 25-case frozen set + benchmark protocol；setpassword 作废、exiv2 保持 candidate、近亲对口径(0.2) 纳入统计 | 0.1,0.2 | 已达成：可复现固定口径 |

### 阶段 1 · 核心主张（skill 必要性，重做被推翻的结论）
**目标**：用 clean 数据回答"skill 是否必要/是否能把模型带向真实目标"。

| # | 任务 | 做法 | 前置 | 验收 |
| --- | --- | --- | --- | --- |
| 1.1 ✅ | 三条件系统必要性实验 | clean case 集下 oracle/weak/no 多轮，替代旧的 18 case/213 run 口径；**153-run 已出（冻结口径：no 6.7% / weak 11.1% / oracle 46.7%，DECOY no28→weak24→oracle2）** | 0.x | **已达核心验收**：oracle≫weak/no（46.7 vs 11.1/6.7）且诱饵从 28 压到 2；严格必要性仍待 1.2 族内区分推广后再下 |
| 1.2 🔶 | 族内区分推广 | 邻接指纹方法推广到其他家族。**FH451 已跑但为负结果**（5 case×3 轮，distinguishing 4/15 vs generic 6/15）：FH451 的 5 个脆弱 handler 及近邻聚集在重叠度极高的无线/WAN 字符串表集群，邻接运行几乎相同、参数 token 被多个近邻共享，模型按语义取名漂移（fromWanPortParam/formWrlLoginfo/formSetCfm 等）；fromSetCfm 还因二进制实为 formSetCfm 而不可命中。**对比 F9K(20%→66.7%)，结论：族内区分收益 family-dependent，非通用增益**；仅在目标在字符串表分离度高的家族适用 | 0.x | 修正后验收：区分型 skill 只应用于分离度足够的家族，并维护每家族分离度+结果记录（FH451 已记） |
| 1.3 ✅ | 逐 case 归因 | 对 oracle 未命中（NO）区分"模型能力不足 vs oracle 区分度不够"，出归因表 | 0.x | **已达成**：28 oracle-NO round 归因 5 类（区分度不足 A+B+D=75% 主导、数据集缺陷 C=3、模型能力 E=4）；见 briefing_20260816/plan1_necessity_attribution_20260820.md |

### 阶段 2 · 系统完整性（闭环能否自证收益）
**目标**：把"闭环能跑"升级为"闭环带来可追踪的正收益"。

| # | 任务 | 做法 | 前置 | 验收 |
| --- | --- | --- | --- | --- |
| 2.1 | 修 gate reject_ready | workflow.py 让每候选完成既定次数验证再下结论，清理 34 pending | 0.x | pending 不再堆积 |
| 2.2 | 发布后效果追踪+回退 | freeze live 快照 → hold-out 集对比 no/baseline/evolved live；加回退 | 0.x | 拿到前/后对比 + "发布→效果"证据 |
| 2.3 | 完成 catalog 检索对比 | server-inline-lexical (`inline`) vs server-catalog；model-side catalog 作为兼容/消融条件；当前已完成 F9K 两 case 的初步诊断，仍需冻结口径 | 0.x | 有选择有效性和下游结果对比数据，并明确失败边界 |

### 阶段 3 · 论文对齐（成稿前必做）
**目标**：论文每个数字都能在 clean csv 里找到，结论与干净数据一致。

| # | 任务 | 做法 | 前置 | 验收 |
| --- | --- | --- | --- | --- |
| 3.1 | 重写实验章节 | 替换 v2 tex 里旧的 18 case/213 run/53-of-54/strictly necessary 口径 | 1.x | 论文数字与 clean csv 对齐 |
| 3.2 | 写入本轮新内容 | 净化防作弊、数据集订正、族内区分 | 1.x | 论文反映真实方法与数据 |
| 3.3 | 跑通模板出 PDF | COSE elsarticle | 3.1,3.2 | 可编译 PDF |

### 编排说明
- 每周优先做：0.1、0.3、1.1（研究可信度根基）与 2.1（系统阻塞）。
- **建议的首轮执行序列（按依赖串接）**：
  1. 先做 0.1 + 0.2（1 天内订正 setpassword、明确不可分近亲对口径）→ 冻结 case 集（0.3）；
  2. 再在干净集上做 1.1 三条件必要性实验（论文最有说服力的一格）；
  3. 并行推进 2.1 gate 修复（纯工程、不依赖实验数据，是可立即动工的阻塞项）；
  4. 1.1 出数后接 1.2 族内区分推广 与 1.3 逐 case 归因，最后 3.x 论文对齐。
- 阶段性手记：每完成一档即更新本文档对应验收列，并归档到 `reports/current/`（纳入 git）。

---

## 五、风险与边界（常驻提醒）

1. 评分/确认的语义盲区依然存在（规则级匹配、artifact 级确认为主，无行为级模拟器）。
2. gate 的 tool-free replay 与"不覆盖 description→检索"问题，使 gate 通过 ≠ 真实有效。
3. "发布后无效果追踪/回退"未解决，发布有负面下游风险。
4. clean 数据下 skill 必要性尚未证明，论文严禁用旧 54/54 类强结论。
5. 数据集含复制缺陷（setpassword），出任何新综述/论文前必须先订正。

---

*文档生成：2026-08-20 · 数据来源：runtime/ablation/results/ 原始 CSV + docs/handoff/ + 工程状态（旧版）*

