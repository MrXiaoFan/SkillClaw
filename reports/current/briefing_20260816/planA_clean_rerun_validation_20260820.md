# 方案 A：三条件清洁对比实验（no-skill / weak-skill / oracle-skill）

> 实验记录 · 运行日期 2026-08-20 · 数据文件：runtime/ablation/results/ablation_results_rerun_model.csv
> 本文件版本化归档于 reports/current/briefing_20260816/

## 1. 实验目的
在"净化技能 + 新模型"条件下，对同一批 14 个 HTTP handler/cgi 案例做三条件盲测对照，
回答两个问题：
1. 上一版 84 runs（oracle 命中 39/40 = 97.5%）到底是真实命中还是"技能注入泄答案"的作弊产物？
2. 清洁重跑下，oracle-skill 是否仍优于 weak-skill / no-skill？即 skill 是否带来必要性收益？

## 2. 背景与动机（为什么重跑）
- 旧数据（ablation_results.csv，同 84 runs 口径）oracle-skill 命中率 97.5%，显著高于合理水平，
  且带"注入未净化技能"的历史问题。
- 复审发现旧高命中主要来自技能内容里隐含答案线索（目标函数名/诱饵/设备等）被拼进上游 prompt，
  模型并非靠真实分析命中，而是靠"读答案"——属作弊。
- commit 8186f34 完成净化改造后，决定用新模型（deepseek-v4-flash）全量重跑同口径实验。

## 3. 净化改造内容（commit 8186f34）
1. 盲测 prompt 抹掉答案线索；
2. 修复运行期 OOM；
3. inline skills 不再注入 catalog（避免技能库见底后副作用）；
4. 新增 14 案例 + elf weak skill（作为 weak 条件基线）。

## 4. 实验设计
- 案例集：14 个 HTTP handler/cgi 入口 case（见第 6 节表格）。
- 条件（condition）：no-skill / weak-skill / oracle-skill。
- 轮次：每 case × 每条件 2 rounds。
- 规模：14 × 3 × 2 = 84 runs。
- 模型后端：deepseek-v4-flash（经 CC Switch C402-DSv4Flash-Codex）。
- 执行：远程 VM blind run（evaluation.runs.run_remote_case），净化盲测词提示。
- 输出隔离：独立 output-tag `rerun_model`，写入 ablation_results_rerun_model.csv，与旧数据隔离。

## 5. 运行概况
- 总 runs：84，全部 status=completed（无失败/超时丢弃）。
- 起止：2026-08-20T08:33:59Z → 09:41:41Z（约 68 分钟）。
- 单 run 耗时：min 13.3s，max 205.8s，mean 48.4s，合计 4061.5s（约 67.7 分钟）。

## 6. 结果：总体命中率（correct = YES）
| condition | YES/total | 占比 |
| --- | --- | --- |
| no-skill | 1/28 | 3.6% |
| weak-skill | 4/28 | 14.3% |
| oracle-skill | 10/28 | 35.7% |
| **合计** | **15/84** | 17.9% |

对照：旧作弊 baseline oracle-skill 97.5% → 清洁重跑 35.7%（约 -62pp）。

## 7. 结果：逐 case × condition 命中（YES）
| case_key | target_function | 家族/设备 | no-skill | weak-skill | oracle-skill |
| --- | --- | --- | --- | --- | --- |
| f1202-cmdinject | formWriteFacMac | Tenda F1202 | 0/2 | 1/2 | 0/2 |
| f1202-credential-overflow | fromAdvSetWan | Tenda F1202 | 0/2 | 0/2 | 0/2 |
| f453-cmdinject | formWriteFacMac | Tenda F453 | 0/2 | 0/2 | 2/2 |
| f453-overflow | formWrlsafeset | Tenda F453 | 0/2 | 1/2 | 2/2 |
| f453-qossetting-overflow | fromqossetting | Tenda F453 | 0/2 | 0/2 | 0/2 |
| f453-routestatic-overflow | fromRouteStatic | Tenda F453 | 0/2 | 0/2 | 2/2 |
| f456-cmdinject | formWriteFacMac | Tenda F456 | 0/2 | 0/2 | 1/2 |
| f9k1122-crossband-overflow | formCrossBandSwitch | Belkin F9K1122 | 0/2 | 0/2 | 0/2 |
| f9k1122-overflow | formWISP5G | Belkin F9K1122 | 0/2 | 2/2 | 2/2 |
| f9k1122-setpassword-overflow | formSetPassword | Belkin F9K1122 | 0/2 | 0/2 | 0/2 |
| f9k1122-setsystemsettings-overflow | formSetSystemSettings | Belkin F9K1122 | 1/2 | 0/2 | 0/2 |
| f9k1122-wlansetup-overflow | formWlanSetup | Belkin F9K1122 | 0/2 | 0/2 | 0/2 |
| fh451-formWrlExtraSet-overflow | formWrlExtraSet | Tenda FH451 | 0/2 | 0/2 | 1/2 |
| i12-pathtraversal | R7WebsSecurityHandler | i12 | 0/2 | 0/2 | 0/2 |

## 8. 结果：辅助统计
| 指标 | no-skill | weak-skill | oracle-skill |
| --- | --- | --- | --- |
| 平均 score（/10） | 4.38 | 4.34 | 6.32 |
| 预测到诱饵函数 decoy（/28） | 9 | 12 | 1 |
| 空预测（/28） | 0 | 1 | 0 |

要点：
- oracle-skill 平均分明显更高（6.32 vs ≈4.36），且几乎不再被诱饵函数带偏（1/28 vs 9~12/28）。
- 但命中率上 oracle 仅在 6 个 case 领先（f453×3 强、f456×1、fh451×1、f9k1122-overflow 与 weak 持平），
  并非所有 case 都压倒性领先。

## 9. 关键观察与结论
1. **净化效应确认**：oracle 命中率从 97.5% 掉到 35.7%，说明旧 39/40 主要是技能泄答案的作弊，
   不是 clean 命中。
2. **oracle 仍高于 no/weak，但未完全碾压**：35.7% > 14.3% > 3.6%，方向正确；
   但 28 个 oracle run 里仍有 18 个未命中。
3. **F9K1122 家族是主要拖累**：4 个非 WISP 目标（crossband/setpassword/setsystemsettings/wlansetup）
   在 oracle 下几乎全 MISS，被同家族"最显眼"handler formWISP5G 带偏 → 这是后续"族内区分型"改良的动机
   （见姊妹记录 f9k_distinguishing_validation_20260820.md）。
4. **skill 必要性仍未证明**：清洁下 oracle 只在部分 case 上领先，尚不能说明"必须用该 skill 才能找到目标漏洞"。

## 10. 下一步（未做）
1. 逐 case 排查 oracle-skill 18 个 MISS：是清洁模型能力不足，还是该 oracle skill 强度/区分度不够。
2. 将"族内区分型"邻接指纹改良推广到其余家族（Tenda/i12/firmware2 CGI）。
3. 在更多 case 上用 oracle 压过 no/weak，进一步论证 skill 必要性。

## 11. 产物与文件
- 原始结果：runtime/ablation/results/ablation_results_rerun_model.csv（84 行，.gitignore 忽略）
- 运行日志：runtime/ablation/results/ablation_log_rerun_model.txt
- 状态文件：runtime/ablation/results/ablation_state_rerun_model.json
- 规范化归档表（纳入 git）：reports/current/briefing_20260816/planA_clean_rerun_table_20260820.csv
- 本实验记录（纳入 git）：reports/current/briefing_20260816/planA_clean_rerun_validation_20260820.md
