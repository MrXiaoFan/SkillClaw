# 项目周报（用于 2026-08-17 至 2026-08-23 汇报）

> 本文内容同样来自 2026-08-10 至 2026-08-16 这一周已经真实完成的工作，只是按后半周口径拆分，供下周末继续汇报使用。

## 本周完成工作

1. 在前面完成 F453 案例接入之后，后半段继续补跑验证 run，并把分散的远端实验统一整理成一张可追踪的结果表。到本周末，F453 共累计形成 16 条实验记录，其中 15 条有效。真实目标函数 `formWriteFacMac` 被命中 2 次，另有 10 次仍然漂移到 `formexeCommand`。按是否使用 skill 粗分，无 skill 条件下命中目标 1/4，有 skill 条件下命中目标 1/11。这个结果虽然不理想，但很重要，因为它第一次把“当前 skill 还没有带来稳定正收益”这个问题，用同一案例、同一链路下的统计结果明确暴露出来了。

   统计结果：
   - 总 run：16
   - 有效 run：15
   - 命中 `formWriteFacMac`：2/15
   - 漂移到 `formexeCommand`：10/15
   - 无 skill 条件命中目标：1/4
   - 有 skill 条件命中目标：1/11

   数据文件：
   - [f453_run_table_20260815.md](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260815/f453_run_table_20260815.md)
   - [f453_run_table_20260815.csv](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260815/f453_run_table_20260815.csv)

2. 针对“看起来分数不低，但其实找错了目标函数”的问题，补上了一轮关键修正。此前只要答案里提到了部分正确线索，就可能继续得到较高分，这会让错误 run 被误送进 feedback 和 evolve。为此，这一轮新增了 `function_identity_miss` 标志，专门用来标记“文件、证据、根因部分匹配，但真正目标函数没有找对”的情况，并把这个标志继续传到 feedback 和 evolve 阶段，避免这类错误高分继续被放大。从更新后的 F453 实验表可以看到，至少有两条原本容易被看成“还不错”的 run，已经被明确标成 `function_identity_miss`，并降到 `neutral` 处理。

3. 在 skill 选取链路上，又补了一轮收紧逻辑，重点不是增加新的模式，而是先减少明显无关的 skill 混入当前任务。这里做的几件事包括：对负向词重叠过多的 skill 做硬否决，在没有合适匹配结果时补回退逻辑，以及清理 transient system reminder 对 skill 触发的干扰。结合这一轮 F453 结果看，`extraneous_skill_selection` 仍然频繁出现，所以问题还没有彻底解决，但这一步已经把“明显不该选中的 skill 也不断被混进上下文”这个现象往下压了一轮。

4. 对远端 blind run 到 evolve 的链路又补了两处稳定性改造。一处是 SSH 超时后的 artifact 自动回收，另一处是在远端 run 没有留下完整 API session 记录时，补 session 合成逻辑，让这类 run 仍然可以继续 handoff 到后续流程。这样做的结果是，远端 VM 上跑出来的实验，不再因为中途一处链路缺口就整轮报废，而是更大概率能保留结果、继续进入 feedback 和 gate。

5. 后半段还对 6 个待决的 gate job 做了定向 `real_rerun` 校验，其中 3 个被接受并自动发布到 live skill，分别是 `peplink-fiwm-firmware-analysis`、`tenda-httpd-goform-execommand-triage` 和 `cisco-vmanage-firmware-analysis`，对应 rerun score 为 0.65、0.60 和 0.80。这里要强调的是，这个结果证明了“candidate 可以经过 rerun 检查后自动发布”，也就是说闭环工程已经真正走通；但它并不自动等于“发布后的 skill 已经对 F453 带来稳定提升”。因此，这一部分更适合对外表述为工程闭环进展，而不是直接表述为漏洞分析效果已经显著提升。

   定向 rerun 结果：

   | job 数量 | accepted | 代表 skill | score |
   | --- | --- | --- | --- |
   | 6 | 3 | `peplink-fiwm-firmware-analysis` | 0.65 |
   | 6 | 3 | `tenda-httpd-goform-execommand-triage` | 0.60 |
   | 6 | 3 | `cisco-vmanage-firmware-analysis` | 0.80 |

   证据文件：
   - [validation_260816.log](/D:/Code/SkillClaw/SkillClaw/runtime/validation_260816.log)

6. 论文方面，后半段继续把这一轮真实工程与实验结果写回当前稿件，重点补的是：F453 固件案例的研究位置、远端 blind 分析与本地 feedback/evolve 链路的关系、以及当前仍未解决的边界条件，例如 skill 必要性尚未证明、natural 检索仍会混入无关 skill、以及 gate 虽然能 rerun，但还不能直接代表 live skill 已经获得稳定收益。当前工作稿仍然建议附 [paper/skillclaw_confirmation_feedback_elsarticle_v2.tex](/D:/Code/SkillClaw/SkillClaw/paper/skillclaw_confirmation_feedback_elsarticle_v2.tex)。

7. 针对此前同一口径消融里 oracle-skill 命中偏高（39/40 = 97.5%）但疑似来自“技能泄答案”的问题，做了一轮**三条件清洁重跑（方案 A）**。结果用 14 个 HTTP handler/cgi 案例、在净化技能 + 新模型（deepseek-v4-flash）下做 no-skill / weak-skill / oracle-skill 三条件盲测，每案例×条件 2 轮，共 **84 runs**。重跑的核心对照是：同口径旧 oracle 命中 **97.5% → 清洁后 35.7%（-62pp）**，说明旧数据的高命中主要来自技能内容把目标函数名/诱饵/设备型号等答案线索拼进上游 prompt 的作弊，而非真实漏洞分析。

   统计结果（84 runs，平均分满分 10）：

   | 条件 | runs | 命中 YES | DECOY | NO | 平均分 |
   | --- | ---: | ---: | ---: | ---: | ---: |
   | no-skill | 28 | 1 (3.6%) | 9 | 18 | 4.38 |
   | weak-skill | 28 | 4 (14.3%) | 12 | 12 | 4.34 |
   | oracle-skill | 28 | 10 (35.7%) | 1 | 17 | 6.32 |

   值得注意的两点：一是清洁下 oracle 仍高于 weak/no（35.7>14.3>3.6），尤其把 DECOY 命中从 no/weak 的 9～12/28 压到 1/28，说明 oracle skill 的“控诱饵能力”是真实存在的；二是 oracle 也远没有完全碾压——28 个 oracle run 里仍有 17 个 NO、1 个 DECOY，所以“必须用该 skill 才能找到目标”的必要性主张仍未被证明。
   
   主要工程改动（净化，commit `8186f34 fix(ablation): purify served skills and blind prompts…`）：①盲测 prompt 抹掉答案线索；②修复运行期 OOM；③inline skills 不再注入 catalog；④新增 14 案例 + elf weak skill 作为统一 weak 基线。改动/数据落点：结果表 `runtime/ablation/results/ablation_results_rerun_model.csv`（84 行）、运行日志 `ablation_log_rerun_model.txt`、规范化表 `reports/current/briefing_20260816/planA_clean_rerun_table_20260820.csv`，详细实验记录 `planA_clean_rerun_validation_20260820.md`。

8. 在方案 A 结果上，又做了一轮**族内区分型 oracle skill** 验证，回答“skill 怎么写才既有效又不泄答案”。方案 A 里 F9K1122 家族的非 WISP 目标（crossband/setpassword/setsystemsettings/wlansetup）在 oracle 下几乎全 MISS，反复被预测成同家族“最显眼”的 `formWISP5G`；逐条核查发现 F9K1122 五份 oracle skill 的 content 逐字相同，只写“webs overflow 通用方法论”，不区分族内目标。于是把这份技能重写为**族内区分型**——每份 skill 只描述该目标在二进制字符串表中的**邻接符号指纹**（引导模型靠符号相邻关系锁定目标），**不写目标函数名、不泄答案**，素材来自 `runtime/ablation/werk/f9k_neighborhood.json / f9k_strings.json`。

   结果：5 case × oracle × 3 轮 = 15 runs（deepseek-v4-flash，净化盲测），对照同批旧 generic-oracle（5 case × 2 轮 = 10 runs）：

   | case | 旧 generic-oracle | 新 distinguishing | 预测（新） |
   | --- | ---: | ---: | --- |
   | f9k1122-overflow (formWISP5G) | 2/2 | 3/3 | formWISP5G（命中） |
   | f9k1122-crossband-overflow | 0/2 | **3/3** | formCrossBandSwitch（重新掰回） |
   | f9k1122-wlansetup-overflow | 0/2 | **3/3** | formWlanSetup（重新掰回） |
   | f9k1122-setpassword-overflow | 0/2 | 0/3 | formSelfHealing / formWISP5G（仍 MISS） |
   | f9k1122-setsystemsettings-overflow | 0/2 | 1/3 | formSetSystemSettings(r1) / formWISP5G(r2,r3) |
   | **汇总** | **2/10 (20%)** | **10/15 (66.7%)** | — |

   结论：二进制邻接指纹（不写函数名）能把原先全被 `formWISP5G` 带偏的 crossband/wlansetup 稳定掰回正确 handler，oracle 命中约 3 倍回升（20%→66.7%）且不泄答案。顽固近亲对 setpassword/setsystemsettings 属**数据集缺陷**而非 skill 盲区：两者二进制符号相邻、无区分 token，且 benchmark 里的 setpassword case 实为 setsystemsettings 的复制件（仅 case_id/notes 不同，GT/工作区/验证器全指向后者）。
   
   改动/数据落点：新技能 `runtime/ablation/oracle_skills_json/oracle-f9k-distinguishing-*.json`（5 份）、跑步器 `runtime/ablation/run_f9k_distinguish.py`（独立 output-tag `f9k_distinguish_oracle`，不碰 rerun_model 表）、结果 `runtime/ablation/results/ablation_results_f9k_distinguish_oracle.csv`（15 行）、记录 `f9k_distinguishing_validation_20260820.md` + `f9k_distinguishing_run_table_20260820.csv`。


9. **在冻结 case 集口径下完成技能必要性三条件实验（方案 1.1，153 runs，2026-08-20）**。在净化技能 + 新模型（deepseek-v4-flash）基础上，按冻结协议（`freeze_cases_20260820.md`，固定 commit `01f5830`）执行 **17 case × 3 conditions（no/weak/oracle）× 3 rounds = 153 runs**。相较方案 A 的 84-run 又加了轮次与更严口径。

   统计结果（剔除近亲对后 n=45/条件，满分 10）：

   | 条件 | runs | YES | YES% | DECOY | NO | 平均分 |
   | --- | ---: | ---: | ---: | ---: | ---: | ---: |
   | no-skill | 45 | 3 | 6.7% | 28 | 14 | 3.92 |
   | weak-skill | 45 | 5 | 11.1% | 24 | 16 | 3.99 |
   | oracle-skill | 45 | 21 | **46.7%** | **2** | 22 | 6.20 |

   关键结论：①oracle YES 率 46.7% 约为 no 的 7 倍、weak 的 4.2 倍，且把诱饵命中从 no/weak 的 28/24 压到仅 2，oracle 的“控诱饵能力”在更大样本（153 runs）上得到稳健确认；②相比方案 A 的 oracle 35.7%，本组升至 46.7%（+11pp，口径更严），优势稳健；③但 oracle 仍有 48.9% NO，5 个 case 全不中，**严格必要性仍未证明**，论文继续标注边界。逐 oracle-NO 归因显示多为**同一固件内选错 handler**（generic oracle 无族内区分判据），与已完成的族内区分验证（crossband/wlansetup 掰回 3/3）对应，是下一步 1.2 推广的直接抓手。

   数据落点：记录 `briefing_20260816/plan1_necessity_frozen_validation_20260820.md`、规范表 `.../plan1_necessity_frozen_table_20260820.csv`（135 行弃近亲对）、原始结果 `runtime/ablation/results/ablation_results_plan11_frozen.csv`（153 行）。


---

## 8.x 更新：方案 1.2 首次推广（FH451 族内区分）→ 负结果（2026-08-20 补充）

承接 5.8 里"oracle 全不中/部分命中"的 FH451 case，复用 F9K 上验证有效的邻接符号指纹做族内区分，
结果**新 distinguishing 4/15，反而低于同批 generic-oracle 6/15**——族内区分收益 family-dependent，
非通用；对 FH451 这类 handler 高密集、邻接/参数 token 重叠度高的簇无效。详见
`briefing_20260816/fh451_distinguishing_validation_20260820.md`。
---

## 8.y 更新：方案 1.3 逐 case 归因 + 0.4 FH451 无效数据处理（2026-08-20 补充）

- **1.3 逐 case 归因（已完成）**：对冻结 153-run 中 28 个 oracle-NO round 归因成 5 类——
  A oracle 区分度不够（F9K 已验证可修）9；B FH451 高密度簇 6；C 数据集缺陷（fromSetCfm 实为 formSetCfm）3；
  D 同固件漂移（未验证可修）6；E 模型能力/诱饵 4。**区分度不够 A+B+D=21/28≈75% 主导**；
  C 为数据层缺陷、任何 skill 无法修；E 为模型硬样本。详见 `briefing_20260816/plan1_necessity_attribution_20260820.md` + `.csv`。
- **0.4 FH451 无效数据处理（已完成）**：旧 60-run（`ablation_results_fh451.csv`）复核 error 51/60、correct 空白 51、
  oracle 15 行全空 → **作废（superseded）**；同样 5 个 FH451 case 已由冻结 153-run（45 completed）+ 族内区分 15-run 取代。
  详见 `briefing_20260816/fh451_old_60run_disposition_20260820.md`；archive §7.1 已标注已作废。
- 计划状态：work_plan / roadmap 0.4 ✅、1.3 ✅。
