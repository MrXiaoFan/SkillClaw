# 冻结 Case 集与 Benchmark Protocol（Freeze）— 2026-08-20

> 本文档 = 阶段 0.3 产物：把论文与后续 1.x/2.x/3.x 实验锚定到**一个固定 commit/tag
> 与一份明确 benchmark protocol** 上，保证可复现、口径一致、避免再次出现
> “旧 18 case/213 run 口径 vs 新 84-run 口径”并存的混乱。

## 1. 冻结基线（固定 ref）

| 项 | 值 |
| --- | --- |
| 冻结 commit（短） | `01f5830` |
| 冻结 commit（全） | `01f583041cd89af230c136dd78a62008e5279d9f` |
| 分支 | `dev` |
| 冻结时间 | 2026-08-20 21:13 (+08:00) |
| 数据根目录 | `benchmarks/cases/` |
| 资源版本 | `skillspace/share/default/`（gate 已 settle，pending=0） |
| 净化改造提交 | `8186f34`（数据净化源头） |
| 模型 | `deepseek-v4-flash`（C402-DSv4Flash-Codex） |

> 固定 ref 含义：此后实验、统计、论文引用的 case 内容 / 管道 / 净化技能，都以
> 此 commit 及以上为准。若后续对 case 或 protocol 做更改，必须**新开冻结版本**并
> 在本文件登记，不得原地静默改动。

## 2. 冻结 Case 集（权威口径）

判定字段：每个 case JSON 的 `benchmark.include_in_current_runs`（默认 `True`）。
读取须用 `utf-8-sig`（3 个文件带 BOM：
`f453-httpd-overflow-fromRouteStatic.json`、`f453-httpd-overflow-fromqossetting.json`、
`libarchive-3.8.0-cve-2025-60753.json`）。

### 2.1 进入当前冻结集（in current = 25）
| # | case_id | tier |
| --- | --- | --- |
| 1 | giflib-5.1.2-cve-2016-3977 | publication-ready |
| 2 | libarchive-3.8.0-cve-2025-60753 | current-confirmation |
| 3 | libxml2-2.9.4-cve-2017-8872 | current-confirmation |
| 4 | tcpdump-4.9.1-cve-2017-13031 | current-confirmation |
| 5 | tcpdump-4.9.1-cve-2018-14469 | current-confirmation |
| 6 | f1202-httpd-cmdinject-formWriteFacMac | candidate |
| 7 | f1202-httpd-overflow-fromAdvSetWan | candidate |
| 8 | f453-httpd-cmdinject-formWriteFacMac | candidate |
| 9 | f453-httpd-overflow-formWrlsafeset | candidate |
| 10 | f453-httpd-overflow-fromRouteStatic | candidate |
| 11 | f453-httpd-overflow-fromqossetting | candidate |
| 12 | f456-httpd-cmdinject-formWriteFacMac | candidate |
| 13 | f9k1122-webs-overflow-formCrossBandSwitch | candidate |
| 14 | f9k1122-webs-overflow-formSetSystemSettings | candidate |
| 15 | f9k1122-webs-overflow-formWISP5G | candidate |
| 16 | f9k1122-webs-overflow-formWlanSetup | candidate |
| 17 | fh451-httpd-overflow-WrlclientSet | candidate |
| 18 | fh451-httpd-overflow-formQuickIndex | candidate |
| 19 | fh451-httpd-overflow-formWrlExtraSet | candidate |
| 20 | fh451-httpd-overflow-fromAdvSetWan | candidate |
| 21 | fh451-httpd-overflow-fromSetCfm | candidate |
| 22 | firmware2-login-cgi-cve-2026-2527 | candidate |
| 23 | firmware2-wireless-cgi-cve-2026-2529 | candidate |
| 24 | i12-httpd-overflow-formexeCommand | candidate |
| 25 | i12-httpd-path-traversal-r7webs | candidate |

### 2.2 排除在冻结当前集之外（excluded = 2）
| case_id | 原因 | benchmark.include_in_current_runs |
| --- | --- | --- |
| exiv2-0.26-cve-2017-17725 | 仍为 candidate：仅中间运行时确认路径，未拿到 `getULong/types.cpp` 级最终证据（见 `reports/current/benchmark_status.md`） | `False` |
| f9k1122-webs-overflow-formSetPassword | 数据集复制缺陷：formSetSystemSettings 的 byte-identical 复制件，2026-08-20 作废（0.1）；见 case `notes` INVALIDATED 说明 | `False` |

### 2.3 近亲（不可区分）对处理（承 0.2）
- `f9k1122-webs-overflow-formSetSystemSettings` vs `f9k1122-webs-overflow-formWlanSetup` 等同族 handler：
  字符串表相邻且 token 完全相同的近亲对，**不计入 per-function 命中分母**，另列「不可区分对」类别单独汇报。
- setpassword 复制件**已作废**（0.1），不进入任何命中统计。

> 注：`f9k1122-webs-overflow-formSetSystemSettings`（in current=True）与已作废的
> setpassword 复制件指向同一真实目标；setpassword 的删除不影响本 case 的有效性。

## 3. Benchmark Protocol（冻结口径）

### 3.0 三条件定义
- **no-skill**：不注入任何 skill。
- **weak-skill**：注入通用 weak skill（统一基线，不写死目标函数名）。
- **oracle-skill**：注入 oracle skill；对属于 0.2 近亲对 / 数据不可分的情境，
  必须用**族内区分型**（邻接符号指纹）而非 generic，且不泄漏答案（净化后）。

### 3.1 Clean 集（方案 A 口径，84-run 已出）
- 案例：见第 2 节 frozen set；命中统计排除 setpassword 复制件与不可区分对。
  （方案 A 原始 84-run 含 `f9k1122-setpassword-overflow` 一行，**该行结果因数据集缺陷作废**，
  重算时应剔除或用 formSetSystemSettings 替代，见 §4。）
- 条件：no-skill / weak-skill / oracle-skill；每 case × 条件 ≥ 2 轮（多轮为增大样本）。
- 结果文件：`runtime/ablation/results/ablation_results_rerun_model.csv`（84 行）。
- 原始 run：`runtime/imports/remote_vm/ablation-*`。
- 规范表：`briefing_20260816/planA_clean_rerun_table_20260820.csv`。

### 3.2 族内区分（F9K1122，15-run 已出）
- 方法：二进制的邻接符号指纹把模型从族内显眼 handler 掰回真实目标。
- 结果：generic-oracle 2/10 → distinguishing-oracle 10/15 (66.7%)。
- 复现：`runtime/ablation/run_f9k_distinguish.py`。

### 3.3 复现命令
```
python runtime/ablation/run_ablation.py            # 方案 A 三条件重跑
python runtime/ablation/run_f9k_distinguish.py     # F9K1122 族内区分
python runtime/tmp/gate_audit/freeze_report.py     # 重新盘点 frozen set 成员
```

## 4. 统计口径注意（论文锚定）
1. **旧 18 case/213 run / 53-of-54 / strictly necessary**：受污染（oracle 97.5% 泄答案），
   已作废，不得作为论文主结论。论文以 clean 84-run（§3.1）+ 族内区分（§3.2）为准。
2. 方案 A 的 84-run 中 `f9k1122-setpassword-overflow` 行因数据缺陷作废（其 0 命中不构成
   skill 盲区证据）；统计上层案例集合 = frozen set − setpassword − 不可区分对手感，
   具体在 1.1 正式多轮中落地。
3. oracle 97.5% → clean 35.7%（-62pp）这一对照是本方法学“净化防作弊”的核心论据。
4. clean 下 oracle（35.7%）仍高于 weak（14.3%）/ no（3.6%），但 skill 必要性尚未证明，
   论文在 1.1 正式多轮前不做“strictly necessary”强结论。

## 5. 状态
- roadmap 0.3：✅（本文件登记固定 ref + protocol）
- work_plan 0.3：✅
