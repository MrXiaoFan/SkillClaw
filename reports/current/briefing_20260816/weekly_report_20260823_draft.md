# 项目周报（2026-08-17 至 2026-08-23）

实验环境：目标程序放在远端 Linux 虚拟机中，由大模型在看不到 CVE 号、PoC、ground truth 和 oracle 文件的条件下做 blind 分析；本地 SkillClaw 服务端负责 skill 选取与注入、会话记录、评分与验证，后续结果再进入 feedback 和 gate 流程。

本轮实验涉及的固件与漏洞类型如下：

| 设备 / 固件 | 版本 / 来源 | 命令注入类 | 缓冲区溢出类 | 路径穿越 / 认证绕过类 | 所在实验 |
| --- | --- | --- | --- | --- | --- |
| Tenda F1202 | dataset-20260819 | `formWriteFacMac`（数据集样本，无公开 CVE） | `fromAdvSetWan`（数据集样本，无公开 CVE） | - | 84-run、153-run 主实验 |
| Tenda F453 | dataset-20260812 / 20260818 | `formWriteFacMac`（辅助诊断中对应 `CVE-2026-4554`） | `formWrlsafeset`、`fromqossetting`、`fromRouteStatic`（数据集样本，无公开 CVE） | - | 84-run、153-run 主实验；F453 辅助诊断 |
| Tenda F456 | dataset-20260812 | `formWriteFacMac`（数据集样本，无公开 CVE） | - | - | 84-run、153-run 主实验 |
| Belkin F9K1122 | dataset-20260818 | - | 多个 `webs` handler 溢出样本（如 `formCrossBandSwitch`、系统设置相关 handler，均无公开 CVE） | - | 153-run 主实验；家族区分实验 |
| Tenda FH451 | dataset-20260819 | - | `formQuickIndex`、`formWrlExtraSet`、`fromAdvSetWan`、`fromSetCfm`、`WrlclientSet`（数据集样本，无公开 CVE） | - | 153-run 主实验；家族区分实验 |
| Tenda i12 | dataset-20260812 | - | - | `R7WebsSecurityHandler` 路径穿越 / 认证绕过样本（无公开 CVE） | 153-run 主实验 |
| Wavlink WL-WN579A3 | firmware 20210219 | `login.cgi`（`CVE-2026-2527`）、`wireless.cgi`（`CVE-2026-2529`） | - | - | 辅助诊断旧实验 |

## 1. 重新清洗并重跑了当前主实验

此前部分 `oracle-skill` 结果检查后发现混入了过强的答案提示，不能继续作为正式实验结果使用。本周在 14 个固件漏洞 case 上重新做了净化对照实验，条件为 `no-skill / weak-skill / oracle-skill`，每个条件 2 轮，共 84 条 run。结果如下：

| 条件 | 正确命中 YES | 诱饵命中 DECOY | 未命中 NO | 平均分 |
| --- | ---: | ---: | ---: | ---: |
| no-skill | 1/28 = 3.6% | 9 | 18 | 4.38 |
| weak-skill | 4/28 = 14.3% | 12 | 12 | 4.34 |
| oracle-skill | 10/28 = 35.7% | 1 | 17 | 6.32 |

这一轮结果表明，旧版本中接近“全命中”的 `oracle-skill` 结果不能继续使用；在去掉泄漏因素后，`oracle-skill` 仍然提高了真实命中，并明显减少了被诱饵函数带偏的次数。

数据与记录文件：
- [reports/current/briefing_20260816/planA_clean_rerun_validation_20260820.md](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260816/planA_clean_rerun_validation_20260820.md)
- [reports/current/briefing_20260816/planA_clean_rerun_table_20260820.csv](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260816/planA_clean_rerun_table_20260820.csv)

## 2. 完成了 153 条正式必要性实验

在 84-run 净化实验之后，又把 case 集固定下来，扩展为 17 个固件 case、3 个条件、每个条件 3 轮，总计 153 条 run。统计口径按论文主实验口径执行，剔除不可区分近亲对后分母为 45。结果如下：

| 条件 | 正确命中 YES | 诱饵命中 DECOY | 未命中 NO | 平均分 |
| --- | ---: | ---: | ---: | ---: |
| no-skill | 3/45 = 6.7% | 28 | 14 | 3.92 |
| weak-skill | 5/45 = 11.1% | 24 | 16 | 3.99 |
| oracle-skill | 21/45 = 46.7% | 2 | 22 | 6.20 |

这一组数据说明，在这批固件 case 上，`oracle-skill` 条件下的真实命中率明显高于 `no-skill` 和 `weak-skill`，同时诱饵命中从 28 次和 24 次降到 2 次。

数据与记录文件：
- [reports/current/briefing_20260816/plan1_necessity_frozen_validation_20260820.md](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260816/plan1_necessity_frozen_validation_20260820.md)
- [reports/current/briefing_20260816/plan1_necessity_frozen_table_20260820.csv](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260816/plan1_necessity_frozen_table_20260820.csv)
- [reports/current/briefing_20260816/plan1_necessity_attribution_20260820.md](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260816/plan1_necessity_attribution_20260820.md)

## 3. 补了两组固件家族内部区分实验

这两组实验针对的是“模型已经知道大概危险区域，但容易落到家族里另一个高危函数上”的情况。实验对象为 Belkin F9K1122 家族和 Tenda FH451 家族，比较 `generic oracle` 和 `distinguishing oracle` 两种 skill 写法。结果如下：

| 家族 | skill 条件 | 正确命中 |
| --- | --- | ---: |
| Belkin F9K1122 | generic oracle | 2/10 = 20.0% |
| Belkin F9K1122 | distinguishing oracle | 10/15 = 66.7% |
| Tenda FH451 | generic oracle | 6/15 = 40.0% |
| Tenda FH451 | distinguishing oracle | 4/15 = 26.7% |

Belkin F9K1122 家族上，带区分线索的 skill 明显提高了命中；Tenda FH451 家族上，同样写法反而使结果变差。

数据与记录文件：
- [reports/current/briefing_20260816/f9k_distinguishing_validation_20260820.md](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260816/f9k_distinguishing_validation_20260820.md)
- [reports/current/briefing_20260816/f9k_distinguishing_run_table_20260820.csv](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260816/f9k_distinguishing_run_table_20260820.csv)
- [reports/current/briefing_20260816/fh451_distinguishing_validation_20260820.md](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260816/fh451_distinguishing_validation_20260820.md)
- [reports/current/briefing_20260816/fh451_distinguishing_run_table_20260820.csv](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260816/fh451_distinguishing_run_table_20260820.csv)

## 4. 重新归类了前一阶段旧实验结果

前面做过的一些旧实验没有删除，但不再与主实验混用，改成辅助诊断证据。

一组是 `firmware2-wireless` 和 `firmware2-login` 的 16 条 CGI profile 实验，主要用于说明不同 skill 写法会影响分析路径。结果如下：

| 案例 | none | wrong | relevant | seed |
| --- | ---: | ---: | ---: | ---: |
| firmware2-wireless | 2.67 | 3.00 | 3.00 | 4.00 |
| firmware2-login | 4.33 | 4.50 | 5.00 | 5.00 |

另一组是 Tenda F453 / CVE-2026-4554 的 blind 实验。该案例真实目标函数为 `formWriteFacMac`，危险 sink 为 `doSystemCmd`，属于命令注入场景。实验中模型多次漂移到 `formexeCommand`，并误报为 Tenda 历史漏洞 `CVE-2018-5767`。这组结果主要用于说明旧评分机制容易把“找错目标函数但命中了同类高危路径”的 run 判成高分。

辅助证据文件：
- [reports/current/briefing_20260805/firmware_skill_ablation_summary.md](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260805/firmware_skill_ablation_summary.md)
- [reports/current/briefing_20260805/firmware_ablation_summary.csv](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260805/firmware_ablation_summary.csv)
- [reports/current/briefing_20260815/f453_skill_ablation_20260815.md](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260815/f453_skill_ablation_20260815.md)
- [reports/current/briefing_20260815/f453_run_table_20260815.csv](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260815/f453_run_table_20260815.csv)

## 5. 收紧了 feedback 与 gate 流程

前面 F453 实验已经暴露出一个问题：模型即使找错目标函数，只要命中了同一二进制和相近 sink，也可能得到较高分数并进入 feedback。本周做了两项处理：一是在评分与反馈链路中保留 `function_identity_miss` 标志，用来区分“接近但找错目标函数”的结果；二是清理 replay gate 的 pending job，并把 `publish_mode` 固定为 `validated`。当前工程结果如下：

| 项目 | 结果 |
| --- | --- |
| 积压 pending gate job | 21 -> 0 |
| gate 默认发布模式 | 固定为 `validated` |
| 新增门控守护测试 | `tests/test_gate_settle_guard.py`，5 例通过 |

Gate 当前采用 rerun 方式：candidate skill 生成后，重新注入同一个 blind 分析任务再跑一遍，再根据 rerun 结果决定发布或拒绝。

数据与记录文件：
- [reports/current/briefing_20260816/gate_settle_20260820.md](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260816/gate_settle_20260820.md)

## 6. 论文稿继续推进

当前主稿已经能按 blind 漏洞分析、skill 注入、外部确认、feedback、candidate、gate、live skill 发布 这条主线组织内容，但还有几块内容没有补齐：benchmark 口径说明还需要继续整理，要把“仓库全部 case”“17 个冻结主实验 case”“辅助实验”三层关系分开；实验分层说明还需要补充，哪些结果作为主结果，哪些结果仅作为辅助诊断证据，需要写清楚；失败案例分析还需要继续补，尤其是为何一些 case 会被诱饵函数吸走、为何 FH451 家族上更细的 skill 反而变差；有效性威胁、作者单位、图表和最终结论措辞也还没有定稿。

论文主文件：
- [paper/package_20260824/manuscript/elsarticle/skillclaw_confirmation_feedback_elsarticle.tex](/D:/Code/SkillClaw/SkillClaw/paper/package_20260824/manuscript/elsarticle/skillclaw_confirmation_feedback_elsarticle.tex)
