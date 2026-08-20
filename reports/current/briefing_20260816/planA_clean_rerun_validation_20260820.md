# 阶段性工作记录：方案 A 清洁重跑（no-skill / weak-skill / oracle-skill 对照组，2026-08-20）

本记录对应"方案 A：净化后全量重跑的三条件对照实验"——即提到过的
"oracle 命中率 97.5% → 35.7%" 那一组 84 runs 数据。

## 背景
- 旧的 84 runs（ablation_results.csv，14 case × 3 condition × 2 round）是在注入"未净化"技能下跑的，
  当时 oracle-skill 命中率 39/40 (97.5%)。
- 复查发现该高命中主要来自"技能注入泄答案"的作弊效果，并非 clean 命中。
- commit 8186f34 做了"净化"：(1) 盲测 prompt 抹掉答案线索；(2) 修复 OOM；(3) inline skills 不注入 catalog；
  (4) 新增 14 案例 + elf weak skill。
- 随后用新模型 deepseek-v4-flash + 净化技能完整重跑 84 runs → ablation_results_rerun_model.csv（独立 output-tag，与旧数据隔离）。

## 实验设计
- 14 个 case（全部为 HTTP handler/cgi 入口）：f1202×2、f453×4、f456×1、f9k1122×5、fh451×1、i12×1
- 3 个 condition：no-skill / weak-skill / oracle-skill
- 各 2 rounds → 14×3×2 = 84 runs
- 模型：deepseek-v4-flash（CC Switch C402-DSv4Flash-Codex）；净化盲测；远程 VM blind run

## 总体命中率（correct=YES）
| condition | YES/total | 占比 |
| --- | --- | --- |
| no-skill | 1/28 | 3.6% |
| weak-skill | 4/28 | 14.3% |
| oracle-skill | 10/28 | 35.7% |
| **合计** | **15/84** | — |

对照旧作弊 baseline：oracle-skill 97.5% → 清洁重跑 35.7%（约掉 62pp）。

## 逐 case × condition 命中（YES）
| case_key | target | no-skill | weak-skill | oracle-skill |
| --- | --- | --- | --- | --- |
| f1202-cmdinject | formWriteFacMac | 0/2 | 1/2 | 0/2 |
| f1202-credential-overflow | fromAdvSetWan | 0/2 | 0/2 | 0/2 |
| f453-cmdinject | formWriteFacMac | 0/2 | 0/2 | 2/2 |
| f453-overflow | formWrlsafeset | 0/2 | 1/2 | 2/2 |
| f453-qossetting-overflow | fromqossetting | 0/2 | 0/2 | 0/2 |
| f453-routestatic-overflow | fromRouteStatic | 0/2 | 0/2 | 2/2 |
| f456-cmdinject | formWriteFacMac | 0/2 | 0/2 | 1/2 |
| f9k1122-crossband-overflow | formCrossBandSwitch | 0/2 | 0/2 | 0/2 |
| f9k1122-overflow | formWISP5G | 0/2 | 2/2 | 2/2 |
| f9k1122-setpassword-overflow | formSetPassword | 0/2 | 0/2 | 0/2 |
| f9k1122-setsystemsettings-overflow | formSetSystemSettings | 1/2 | 0/2 | 0/2 |
| f9k1122-wlansetup-overflow | formWlanSetup | 0/2 | 0/2 | 0/2 |
| fh451-formWrlExtraSet-overflow | formWrlExtraSet | 0/2 | 0/2 | 1/2 |
| i12-pathtraversal | R7WebsSecurityHandler | 0/2 | 0/2 | 0/2 |

## 关键观察
1. oracle-skill 在 6 个 case 上领先（f453×4、f456×1、fh451×1、f9k1122-overflow 与 weak 持平），
   但并非在所有 case 上压倒性领先。
2. F9K1122 家族 4 个非 WISP 目标（crossband/setpassword/setsystemsettings/wlansetup）在 oracle-skill 下
   几乎全部 MISS——被同家族"最显眼"handler formWISP5G 带偏（这正是后续"族内区分型"改良的动机，见
   f9k_distinguishing_validation_20260820.md）。
3. 其余大量 oracle-skill MISS 案例（f1202×2、i12、f9k1122 家族 4 个、f453-qossetting）分为两类：
   清洁模型能力不足，或该 oracle skill 本身强度/区分度不够（需逐 case 进一步排查）。

## 结论（阶段性）
- 净化后 oracle 未能在全部案例上压倒性领先，skill 必要性尚未证明；
- oracle-skill 的命中以 F9K 家族外的独立性较强的 case 为主，F9K 家族需要"族内区分"方向的改良。

## 产物清单
- 原始结果：runtime/ablation/results/ablation_results_rerun_model.csv（84 行，.gitignore 忽略）
- 运行日志：runtime/ablation/results/ablation_log_rerun_model.txt、ablation_state_rerun_model.json
- 规范化归档表（纳入 git）：reports/current/briefing_20260816/planA_clean_rerun_table_20260820.csv
- 本记录：reports/current/briefing_20260816/planA_clean_rerun_validation_20260820.md

## 下一步（未做）
1. 逐 case 排查 oracle-skill MISS 原因（能力不足 vs skill 不够强）。
2. 将"族内区分型"改良推广到其余家族。
3. 论证 skill 必要性（clean 下 oracle 需在更多 case 上压倒 no/weak）。
