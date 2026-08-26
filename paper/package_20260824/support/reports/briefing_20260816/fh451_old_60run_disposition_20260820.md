# 阶段 0.4 处置：FH451 旧 60-run 数据集（ablation_results_fh451.csv）— 2026-08-20

> 归属：research_roadmap / work_plan **0.4「FH451 无效数据处置」**。
> 结论：**旧 60-run FH451 数据集标记为「已作废 / 已被有效数据取代」**，不再作为任何证据使用。

---

## 1. 背景（为什么有这个数据集）
- 早期（方案 A 之前）生成过一份 FH451 五 case 四条件对照：`runtime/ablation/results/ablation_results_fh451.csv`，60 行。
- archive §7.1 曾记录其「数据无效待排查」：四条件 YES 全 = 0，oracle 15 行全空、其余 correct 大量为空。

## 2. 数据检查（本次复核，2026-08-20）
- 总行数：60（5 case × 4 conditions（no/weak/weak-skill-2/oracle-）× 3 rounds）。
- **status 分布：completed 仅 9 行，error 51 行**（85% 报错）。
- correct 分布：DECOY 6、NO 3、空白 51；oracle 15 行 predicted_functions 全空。
- 结论：这批 60-run 存在大比例运行错误（error=51）与输出缺失（51 correct 空白），**不可判读，确实无效**。

## 3. 处置依据：已被有效数据取代
- 同样的 5 个 FH451 case（formWrlExtraSet / WrlclientSet / fromSetCfm / fromAdvSetWan / formQuickIndex）
  已被 **冻结 153-run（plan11_frozen）有效覆盖**：45 行全部 `completed`（5 case × 3 cond × 3 rounds），
  文件 `runtime/ablation/results/ablation_results_plan11_frozen.csv`。
- 另加 FH451 族内区分验证 15-run（`ablation_results_fh451_distinguish_oracle.csv`，commit 2e28257 归档）深化。
- 因此旧 60-run 数据集**不具备任何增量信息**，其分析对象已由两项有效数据取代。

## 4. 处置结论
- **状态：作废（superseded / voided）。**
- 不在任何命中统计 / 论文 / 汇报中引用 `ablation_results_fh451.csv` 的数字。
- 对 0.4 验收「FH451 状态明确」：达成——FH451 的证据以**冻结 153-run 的 45 completed runs + 15-run 族内区分**为准；
  旧 60-run 仅作为历史失败的负面积累保留在 archive §7.1，标注「已作废」。
- work_plan / roadmap 0.4 更新为 ✅。

## 5. 产物
- 本文档：`reports/current/briefing_20260816/fh451_old_60run_disposition_20260820.md`
- 原始（作废）数据：`runtime/ablation/results/ablation_results_fh451.csv`（.gitignore，不入库）
