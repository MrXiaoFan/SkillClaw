# 阶段性工作记录：F9K1122 族内区分型 oracle skill 验证（2026-08-20）

## 背景与动机
- 方案 A 清洁重跑（净化 + deepseek-v4-flash，commit 8186f34）后，oracle 命中率从旧作弊 baseline 的 97.5%
  掉到 35.7%。逐案例排查发现：F9K1122 家族的非 WISP 目标（crossband/setpassword/setsystemsettings/wlansetup）
  几乎全部被模型预测到同家族"最显眼"的 formWISP5G（详见 ablation_results_rerun_model.csv 的 oracle-skill 行）。
- 根因定位：oracle skill 存在同质化——F9K1122 五份（oracle-case-08/09/10/11/12）content 逐字相同，
  只描述"webs overflow 通用方法论"，不区分族内目标；模型把通用方法论套到最出名的 handler 上。
- 对策（选项 1）：把 oracle skill 重写为"族内区分型"，用二进制字符串表的**邻接符号指纹**区分族内 handler，
  且不泄目标函数名。素材来自 runtime/ablation/werk/f9k_neighborhood.json / f9k_strings.json。

## 实验设计
- 新技能：runtime/ablation/oracle_skills_json/oracle-f9k-distinguishing-*.json（5 份：wisp5g / crossband /
  wlan-setup / set-system-settings / set-password）
- 跑步器：runtime/ablation/run_f9k_distinguish.py（独立 output-tag `f9k_distinguish_oracle`，不碰 rerun_model CSV）
- 规模：5 case × oracle-skill × 3 rounds = 15 runs，deepseek-v4-flash，净化盲测
- 对照 baseline：同批 F9K1122 案例旧 generic-oracle（ablation_results_rerun_model.csv，oracle-skill，5 case × 2 rounds = 10 runs）

## 结果对比（per-case oracle 命中 YES 率：旧 generic → 新 distinguishing）
| case_key | 旧 generic-oracle | 新 distinguishing | 预测（新） |
| --- | --- | --- | --- |
| f9k1122-overflow (WISP5G) | 2/2 | 3/3 | formWISP5G（命中） |
| f9k1122-crossband-overflow | 0/2 | **3/3** | formCrossBandSwitch（重新掰回） |
| f9k1122-wlansetup-overflow | 0/2 | **3/3** | formWlanSetup（重新掰回） |
| f9k1122-setpassword-overflow | 0/2 | 0/3 | formSelfHealing / formWISP5G（仍 MISS） |
| f9k1122-setsystemsettings-overflow | 0/2 | 1/3 | formSetSystemSettings(r1) / formWISP5G(r2,r3) |
| **汇总** | **2/10 (20%)** | **10/15 (66.7%)** | — |

关键结论：族内区分型 skill（二进制邻接指纹）能把原先全被 formWISP5G 带偏的 crossband/wlansetup
稳定掰回正确 handler，oracle 命中率约 3 倍回升（20% → 66.7%），且技能不写目标函数名、不泄答案。

## 顽固案例 setpassword / setsystemsettings：数据集缺陷，非 skill 盲区
- 逐字段比对 f9k1122-webs-overflow-formSetPassword.json 与 formSetSystemSettings.json：
  仅 case_id 与 notes 不同，其余（target.source_root、blind_workspace、ground_truth、required_evidence、
  validators、confirmation、prompt、oracle_only_paths）逐字节相同。
- 源侧 Z 盘对照：vul4(真 formSetPassword，poc 打 /goform/formSetPassword) 与 vul5(formSetSystemSettings，
  poc 打 /goform/formSetSystemSettings) 的 webs 二进制 MD5 相同(205E6972...) 、formsDefine.c 相同，
  仅 vul_function 源与 description/poc 不同。
- 结论：benchmark 里的 setpassword case 是从 setsystemsettings case 复制、只改 case_id/notes，从未从
  vul4 真样本重新派生。ablation 里它在"vul5 二进制上找 formSetPassword 这个不存在的目标"。
- 近亲不可分根因：同份 webs 字符串表里 formSetSystemSettings(445) 与 formSetPassword(446) 是相邻符号，
  邻接 token 完全相同，二进制层面无区分 token；唯一能区分的是 poc 打哪个 /goform/* 端点（oracle-only，不给模型）。
- 处理建议：setpassword case 应从 14 案例集作废，或改用 vul4 真样本重派生；非 oracle skill 质量问题。

## 产物清单
- 技能：runtime/ablation/oracle_skills_json/oracle-f9k-distinguishing-*.json（5 份）
- 跑步器：runtime/ablation/run_f9k_distinguish.py
- 原始结果：runtime/ablation/results/ablation_results_f9k_distinguish_oracle.csv（15 行）
- 运行日志：runtime/ablation/results/f9k_distinguish_run.log
- 邻接素材：runtime/ablation/werk/f9k_neighborhood.json、f9k_strings.json
- 本记录：reports/current/briefing_20260816/f9k_distinguishing_run_table_20260820.csv + 本 md
- 注：runtime/ 目录在 .gitignore 中，未纳入 git；本 md 与 table 位于 reports/ 下可供版本化/汇报。

## 下一步（未做）
1. dataset 订正 setpassword case（作废或从 vul4 重派生）。
2. 族内区分推广到其余家族（Tenda F1202/F453/F456/FH451、i12、firmware2 CGI），复用同样邻接指纹模式。
3. 对顽固近亲对（二进制不可分）在数据层处理 + 考虑提高 oracle-only 判据。
