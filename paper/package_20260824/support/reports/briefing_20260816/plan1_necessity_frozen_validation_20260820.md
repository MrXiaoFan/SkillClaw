# 阶段性工作记录：方案 1.1 三条件技能必要性实验（冻结 case 集，153 runs）— 2026-08-20

> 归属：research_roadmap 1.1 / work_plan 1.1「三条件系统必要性实验」。
> 本实验在**冻结 case 集口径（freeze_cases_20260820.md，commit 01f5830）**下，
> 用净化技能（commit 8186f34）+ deepseek-v4-flash，执行
> **17 case × 3 conditions（no-skill / weak-skill / oracle-skill）× 3 rounds = 153 runs**。
> 结果 tag：`plan11_frozen`；不碰 84-run 的 `rerun_model` 表。

---

## 1. 背景与研究问题

### 1.1 背景
- 承 2026-08-20 方案 A 三条件清洁重跑（84 runs，oracle 97.5%→35.7%）与 F9K1122 族内区分验证（15 runs，20%→66.7%）。
- 论文与路线图最关键的遗留问题：**clean 数据下 skill 是否"必要"**（能否把模型从诱饵稳定带向真实目标）。
- 冻结口径（0.3）已就绪，本实验是 1.1 在冻结 case 集上的首次正式多轮（×3 rounds）执行。

### 1.2 研究问题
Q. 在净化+冻结口径下，oracle-skill vs weak-skill vs no-skill 的命中率（YES）与诱饵（DECOY）命中如何？
   oracle 是否显著优于 weak/no，且把诱饵命中压低？

## 2. 实验设计
- **case 集**：17 个 device/firmware handler/cgi case（冻结 case 集里可由 ablation runner 覆盖的子集）。
- **条件**：
  - no-skill：不注入 skill；
  - weak-skill：注入通用 weak skill（embedded-cgi 或 elf-cwe120 统一基线，不写死目标函数）；
  - oracle-skill：注入对应 oracle skill（generic 形式；`check_no_cheat.py` 校验 clean，无一嵌入答案线索）。
- **轮次**：每 case × 条件 3 轮 → 153 runs。全部 completed。
- **runner**：`runtime/ablation/run_ablation.py --rounds 3`（output-tag `plan11_frozen`）。
- **统计口径**：按 0.2 冻结协议，**近亲（不可区分）对**（setsystemsettings + wlansetup）**不计入 per-function 命中分母**，单列为「不可区分对」汇报。

## 3. 结果

### 3.1 三条件汇总（剔除近亲对后分母 n=45，YES/DECOY/NO）
| 条件 | n | YES | YES% | DECOY | NO | 平均分(满分10) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| no-skill | 45 | 3 | 6.7% | 28 | 14 | 3.92 |
| weak-skill | 45 | 5 | 11.1% | 24 | 16 | 3.99 |
| oracle-skill | 45 | 21 | **46.7%** | **2** | 22 | 6.20 |

- oracle YES 率 46.7% ≈ no-skill(6.7%) 的 **7 倍**、weak-skill(11.1%) 的 **4.2 倍**。
- **关键：oracle 把 DECOY 命中从 no 的 28、weak 的 24，压到仅 2** —— oracle 的"控诱饵"能力在 153-run 大样本上得到强确认。
- 但 oracle 仍有 22/45 NO（48.9% 未中），远未"必须用才能找到"，**严格必要性仍未被证明**。

### 3.2 与 84-run（方案 A）对照
| 条件 | 84-run（2轮） | 153-run（3轮，冻结口径） |
| --- | ---: | ---: |
| no-skill | 3.6% | 6.7% |
| weak-skill | 14.3% | 11.1% |
| oracle-skill | 35.7% | **46.7%** |

- oracle 从 35.7%→46.7%（+11pp，且样本/case 口径更严）；no/weak 维持低位。
- 强化结论：oracle 优势是**稳健**的，不只是 84-run 偶然。

### 3.3 近亲（不可区分）对（0.2 口径，单独汇报，不计入分母）
| 条件 | setsystemsettings YES/3 | wlansetup YES/3 | 合计 YES/6 | 平均分 |
| --- | ---: | ---: | ---: | ---: |
| no-skill | 1/3 | 0/3 | 1/6 | 3.92 |
| weak-skill | 0/3 | 0/3 | 0/6 | 4.25 |
| oracle-skill | 0/3 | 0/3 | 0/6 | 6.00 |

- 符合 0.2 预期：这两者在二进制中符号相邻、token 完全相同，**generic oracle 无法用它把二者分开**（oracle 仍被判 NO）；这是数据不可分区，非 skill 盲区。真正分开需用**族内区分型 oracle**（f9k_distinguish，已把 wlansetup 掰回 3/3）。

### 3.4 逐 case × 条件命中（剔除近亲对，YES/3）
| case | no-skill | weak-skill | oracle-skill |
| --- | ---: | ---: | ---: |
| f1202-cmdinject | 1 | 1 | **3** |
| f1202-credential-overflow | 0 | 0 | 0 |
| f453-cmdinject | 1 | 0 | 1 |
| f453-overflow | 0 | 0 | **3** |
| f453-qossetting-overflow | 0 | 0 | 0 |
| f453-routestatic-overflow | 0 | 0 | 1 |
| f456-cmdinject | 1 | 1 | **3** |
| f9k1122-crossband-overflow | 0 | 0 | 0 |
| f9k1122-overflow | 0 | **3** | **3** |
| fh451-WrlclientSet-overflow | 0 | 0 | 0 |
| fh451-formQuickIndex-overflow | 0 | 0 | **3** |
| fh451-formWrlExtraSet-overflow | 0 | 0 | 2 |
| fh451-fromAdvSetWan-overflow | 0 | 0 | 1 |
| fh451-fromSetCfm-overflow | 0 | 0 | 0 |
| i12-pathtraversal | 0 | 0 | 1 |

- oracle 全中（3/3）case：f1202-cmdinject、f453-overflow、f456-cmdinject、f9k1122-overflow、fh451-formQuickIndex（共 5 个）。
- oracle 全不中（0/3）case：f1202-credential-overflow、f453-qossetting-overflow、f9k1122-crossband-overflow、fh451-WrlclientSet-overflow、fh451-fromSetCfm-overflow（共 5 个）→ 归因见 §3.5。
- 值得注意：f9k1122-overflow 下 weak-skill 也 3/3 全中（ELF 溢出 triage 对该案例确实足够）。

### 3.5 oracle 未命中 NO 案例的预测（归因线索）
- f1202-credential-overflow（target=fromAdvSetWan）：预测漂到 `formDefinePwd`/`getwebuserpwd`/`decodePwd`（认证/密码类，同固件但错 handler）。
- f9k1122-crossband-overflow（target=formCrossBandSwitch）：**3 次全预测 formWISP5G**（同族"最显眼"handler）→ 恰是被族内区分型 skill 修复的那一类（f9k_distinguish 里 crossband 已 3/3 掰回）。
- fh451-WrlclientSet-overflow：3 次全预测 `formWrlsafeset`（同固件另一 handler）→ 家族内区分仍不足。
- fh451-fromSetCfm-overflow：预测 `formSetCfm`/`formWrlsafeset`/`formWrlBasicSet`（都在同固件、错 handler）。
- f453-qossetting-overflow：预测 `formWrlsafeset`/`formBulletinBoard`/`formSetIptv`（同固件其它 handler）。

**归因分层**：这些 oracle-NO 大多不是"oracle skill 完全无效"，而是**同一固件内多个相邻/相似 handler 中选错**——generic oracle 只给"方法论"不给族内区分判据。逐一对应 f9k_distinguish 已验证「族内区分型 skill 能把这类掰回」；因此把 generic→distinguishing 推广到全部 17 case 是提升 oracle 命中、从而强化必要性的直接抓手（工作_plan 1.2）。

## 4. 讨论 / 结论
1. **净化+冻结口径下 oracle 优势稳健**：46.7% vs no 6.7% / weak 11.1%，且把 DECOY 命中压到 2/45；oracle 的"控诱饵 + 引导真实目标"是真实效应。
2. **必要性仍非"严格"**：oracle 仍有 48.9% NO，尚有 5 个 case 全不中；不能下"必须用该 skill"结论，论文继续标注边界。
3. **提升路径明确（1.2）**：oracle-NO 多为"族内选错"，可直接用邻接指纹族内区分型 skill 覆盖（crossband 已验证 3/3 可救）。
4. 近亲对（0.2）按协议单列，不从命中分母剔除造成误导。

## 5. 可信度
- **高**：153 runs 全 completed、净化技能（check_no_cheat clean）、冻结口径、×3 轮；可与 84-run 对照。
- 局限：case 集为 17 个（冻结集可被 ablation runner 覆盖子集），需补水出版级开源 case 与 firmware2 的覆盖（论文 3.1）。

## 6. 产物文件
- 原始结果：`runtime/ablation/results/ablation_results_plan11_frozen.csv`（153 行，.gitignore）
- 运行日志：`runtime/ablation/results/ablation_log_plan11_frozen.txt`
- 分析脚本：`runtime/ablation/analysis/analyze_plan11_frozen.py`
- 规范化表（纳入 git）：`reports/current/briefing_20260816/plan1_necessity_frozen_table_20260820.csv`（135 行，剔除近亲对）
- 本文档（纳入 git）：`reports/current/briefing_20260816/plan1_necessity_frozen_validation_20260820.md`
- commit 待更新 AGENT_HANDOFF / work_plan / roadmap 状态。
