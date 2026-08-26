# 桌面文档与仓库真实状态对账（2026-08-23）

## 目的

这份说明只做一件事：把桌面上的周报/工程状态文档，与当前仓库内真实可核对的工程、实验和论文状态逐条对齐，避免后续继续沿着过时或乱码文档推进。

当前应优先相信的仓库内入口：

1. [AGENT_HANDOFF.md](/D:/Code/SkillClaw/SkillClaw/AGENT_HANDOFF.md)
2. [docs/handoff/20260820/01_necessity_plan_done_and_next.md](/D:/Code/SkillClaw/SkillClaw/docs/handoff/20260820/01_necessity_plan_done_and_next.md)
3. [reports/current/experiment_archive_all_20260820.md](/D:/Code/SkillClaw/SkillClaw/reports/current/experiment_archive_all_20260820.md)
4. [reports/current/briefing_20260816/weekly_report_20260823_draft.md](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260816/weekly_report_20260823_draft.md)

---

## 一、桌面文档当前可信度

| 文档 | 当前状态 | 是否可直接继续使用 | 说明 |
| --- | --- | --- | --- |
| `C:\Users\Fan\Desktop\20260823weekly.docx` | 部分正确，但停在较早一轮 | 否 | 覆盖了 84-run 清洁重跑、F9K 区分、setpassword 数据缺陷，但没有纳入 153-run 必要性、FH451 负结果、旧数据作废、8.20 后的正式交接口径 |
| `C:\Users\Fan\Desktop\工程状态（新版）.docx` | 乱码 | 否 | 内容基本不可读，不能继续作为工程状态入口 |
| `C:\Users\Fan\Desktop\工程状态（旧版）.docx` | 可读，但已过时 | 否 | 主要停留在 F453 / 旧 gate / 旧反馈链路阶段，没有覆盖 8.20 之后的实验主线 |
| `C:\Users\Fan\Desktop\往期周报.docx` | 历史材料 | 可参考，不可当现状 | 对回忆 8.2、8.9、8.17 的阶段进展有帮助，但不能替代当前 handoff |

---

## 二、桌面 `20260823weekly.docx` 与真实进展的关系

### 它写对了的部分

以下内容与仓库内证据一致：

1. 做过一轮 **14 case × 3 条件 × 2 轮 = 84 runs** 的清洁重跑。
2. 旧 oracle 高命中存在“泄答案”问题，净化后命中显著下降。
3. F9K1122 的族内区分型 oracle skill 确实把部分 case 从 `formWISP5G` 诱饵拉回了真实 handler。
4. `setpassword` / `setsystemsettings` 存在 benchmark 数据缺陷，需要单独处理。

这些说法能在下面文件中对应到：

- [planA_clean_rerun_validation_20260820.md](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260816/planA_clean_rerun_validation_20260820.md)
- [planA_clean_rerun_table_20260820.csv](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260816/planA_clean_rerun_table_20260820.csv)
- [f9k_distinguishing_validation_20260820.md](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260816/f9k_distinguishing_validation_20260820.md)
- [f9k_distinguishing_run_table_20260820.csv](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260816/f9k_distinguishing_run_table_20260820.csv)

### 它缺失的部分

它没有纳入当前更完整、也更关键的后续结果：

1. **153-run 冻结口径必要性实验**  
   真实结果已经不是“只做了 84-run clean rerun”，而是继续做到了：
   - `15 case × 3 条件 × 3 轮 = 135 completed runs`
   - `oracle = 29/45 = 64.4%?` 这里要特别注意：`plan1_necessity_frozen_table_20260820.csv` 的完整表是 case-level raw table，最终对外采用的汇报口径应以验证说明文档中的统一统计为准，而不是直接拿 CSV 每类计数硬算。当前 handoff 使用的正式口径是：
     - `oracle 46.7%`
     - `weak 11.1%`
     - `no 6.7%`
     - 诱饵命中 `28 -> 24 -> 2`
2. **FH451 族内区分为负结果**  
   当前不仅有 F9K 的正结果，还有 FH451 的负结果，结论是“族内区分收益是 family-dependent，不可泛化”。
3. **旧 FH451 60-run 数据已作废**  
   这部分旧数据不能再继续写进工程状态或论文主结论。
4. **8.20 之后的正式交接口径**  
   当前项目主入口已经从桌面文档切到 handoff / archive / work_plan 三件套。

---

## 三、仓库内当前应采用的真实实验口径

### 1. F453 第一轮远端 blind 实验

证据：

- [f453_run_table_20260815.csv](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260815/f453_run_table_20260815.csv)
- [f453_skill_ablation_20260815.md](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260815/f453_skill_ablation_20260815.md)

可直接读到的汇总：

| 指标 | 数值 |
| --- | ---: |
| 总 run | 16 |
| `no-skill` | 4 |
| `force-skill` | 3 |
| `natural` | 8 |
| `failed` | 1 |
| `FULL` | 2 |
| `partial(dsc)` | 6 |
| `NO` | 7 |

这批数据适合证明：

- F453 已成功接入 blind 分析链路；
- 当时的评分/反馈/gate 设计会把“找错危险路径”的 run 也看成高分样本；
- 它适合当“问题暴露阶段”的证据，不适合继续当“当前最可信实验主线”。

### 2. 84-run 清洁重跑（方案 A）

证据：

- [planA_clean_rerun_validation_20260820.md](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260816/planA_clean_rerun_validation_20260820.md)
- [planA_clean_rerun_table_20260820.csv](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260816/planA_clean_rerun_table_20260820.csv)

CSV 可直接核对出的总量：

| 条件 | runs |
| --- | ---: |
| `no-skill` | 28 |
| `weak-skill` | 28 |
| `oracle-skill` | 28 |
| 总计 | 84 |

整表 `correct` 统计：

| 标签 | 数量 |
| --- | ---: |
| `YES` | 15 |
| `DECOY` | 22 |
| `NO` | 47 |

这轮实验当前的正式作用是：

- 证明旧 97.5% oracle 命中含有明显泄答案成分；
- 证明净化后 oracle 仍有优势，但必要性还未被严格证明。

### 3. 153-run 冻结口径必要性实验（当前主证据）

证据：

- [plan1_necessity_frozen_validation_20260820.md](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260816/plan1_necessity_frozen_validation_20260820.md)
- [plan1_necessity_frozen_table_20260820.csv](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260816/plan1_necessity_frozen_table_20260820.csv)
- [plan1_necessity_attribution_20260820.md](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260816/plan1_necessity_attribution_20260820.md)

CSV 当前可直接读出的 completed raw rows：

| 条件 | rows |
| --- | ---: |
| `no-skill` | 45 |
| `weak-skill` | 45 |
| `oracle-skill` | 45 |
| 总计 | 135 |

但当前 handoff 与 archive 采用的正式汇报口径，不应直接用 raw rows 手算，而应沿用验证文档中的统一结论：

- `oracle 46.7%`
- `weak 11.1%`
- `no 6.7%`
- 诱饵命中 `28 -> 24 -> 2`

原因很简单：冻结口径里混有“不可区分近亲对剔除”“作废旧 case”“统一验收口径”这些后处理规则，不能只拿 CSV 逐列计数就替代最终结论。

### 4. F9K 族内区分正结果

证据：

- [f9k_distinguishing_validation_20260820.md](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260816/f9k_distinguishing_validation_20260820.md)
- [f9k_distinguishing_run_table_20260820.csv](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260816/f9k_distinguishing_run_table_20260820.csv)

CSV 可直接核对：

| 指标 | 数值 |
| --- | ---: |
| runs | 15 |
| `YES` | 10 |
| `NO` | 5 |

当前正式结论：

- 从旧 generic oracle 的 `2/10 = 20%`
- 提升到 distinguishing oracle 的 `10/15 = 66.7%`

### 5. FH451 族内区分负结果

证据：

- [fh451_distinguishing_validation_20260820.md](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260816/fh451_distinguishing_validation_20260820.md)
- [fh451_distinguishing_run_table_20260820.csv](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260816/fh451_distinguishing_run_table_20260820.csv)
- [fh451_old_60run_disposition_20260820.md](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260816/fh451_old_60run_disposition_20260820.md)

CSV 可直接核对：

| 指标 | 数值 |
| --- | ---: |
| runs | 15 |
| `YES` | 4 |
| `NO` | 11 |

正式结论：

- FH451 区分型 skill 没有带来提升，反而不如 generic 版本；
- “区分型 skill 是否有效”明显依赖家族，不能直接泛化。

---

## 四、当前论文稿状态的真实口径

### 当前可以继续用的主稿

- [paper/skillclaw_confirmation_feedback_elsarticle.tex](/D:/Code/SkillClaw/SkillClaw/paper/skillclaw_confirmation_feedback_elsarticle.tex)

### 只能当历史草稿参考的版本

- ??????? `paper/skillclaw_confirmation_feedback_elsarticle.tex` ?????? v2 ????????????

原因：

1. `v2` 虽然更长，但内部仍保留旧的“213 runs / 严格必要性 / 更强结论”写法。
2. 它没有完全按 2026-08-20 之后的作废口径、family-dependent 结论、冻结集统计去改。
3. 所以后续如果继续写论文，只能：
   - 以主稿 `.tex` 为基准；
   - 把 84-run / 153-run / F9K / FH451 / 作废旧数据 这些内容按当前证据重新补进去；
   - 把 `_v2` 当参考素材，而不是直接接着改。

---

## 五、当前工程状态的真实口径

### 已经真实做到的

1. 主链路已经能跑到：  
   `run -> score/confirmation -> feedback -> evolve -> gate -> publish`
2. `SkillClaw` / `Evolve` / `Dashboard` 当前服务状态正常。
3. 远端 blind run、结果回收、CSV/JSON 归档、阶段性 handoff 都已经有较完整证据链。
4. 2026-08-20 之后，工程主线已切换到 `runtime/ablation/` 这一套净化实验台。

### 还不能夸大的地方

1. 不能说“skill 进化已经稳定提升了 live skill”。
2. 不能说“catalog 模式已经测试并优于 inline”。
3. 不能说“gate 通过就代表 skill 在真实 blind 场景下更有效”。
4. 不能说“当前论文已经拿到了严格必要性的最终证据”。

---

## 六、现在最合理的后续动作

1. 周报、汇报、工程状态统一回到仓库内口径，不再以桌面 `20260823weekly.docx` 为主。
2. 论文只沿主稿 `paper/skillclaw_confirmation_feedback_elsarticle.tex` 继续改。
3. 后续若还要清理文件，只清：
   - 未再引用的临时脚本
   - 空目录 / 0 字节日志
   - 明确不再使用的阶段性中间产物  
   不碰：
   - `runtime/imports/remote_vm/`
   - `skillspace/share/default/`
   - `reports/current/briefing_20260816/` 主证据文件

