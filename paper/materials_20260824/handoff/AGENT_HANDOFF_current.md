# Agent Handoff

当前建议从下面 4 份文件进入，不要再从旧的 2026-08-15 / 2026-08-16 单篇状态文档直接起步：

1. [docs/handoff/20260820/01_necessity_plan_done_and_next.md](/D:/Code/SkillClaw/SkillClaw/docs/handoff/20260820/01_necessity_plan_done_and_next.md)
2. [docs/plans/work_plan_20260820.md](/D:/Code/SkillClaw/SkillClaw/docs/plans/work_plan_20260820.md)
3. [docs/plans/research_roadmap_20260820.md](/D:/Code/SkillClaw/SkillClaw/docs/plans/research_roadmap_20260820.md)
4. [reports/current/briefing_20260816/weekly_report_20260823_draft.md](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260816/weekly_report_20260823_draft.md)
5. [reports/current/briefing_20260816/desktop_docs_reconciliation_20260823.md](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260816/desktop_docs_reconciliation_20260823.md)

## 当前真实状态

- 主链路已经能跑到：`run -> score/confirmation -> feedback -> evolve -> gate -> publish`
- 最近可信的实验主线已经切到 `runtime/ablation/` 这一套净化盲测，不再以前期未净化结果作为主证据
- 桌面版 `20260823weekly.docx` 只覆盖到较早一轮，不包含 2026-08-20 的 84-run / 153-run / F9K / FH451 这批更新后的主证据；后续汇报应优先回看仓库内 `reports/current/briefing_20260816/` 与 `reports/current/experiment_archive_all_20260820.md`
- 论文当前只以 `paper/skillclaw_confirmation_feedback_elsarticle.tex` 为主稿；后续改稿必须先核对它与 2026-08-20 之后的实验口径，不再回到旧的 213-run/严格必要性草稿
- 到 2026-08-20 为止，关键实验结果是：
  - 84-run 清洁重跑：`oracle 35.7% / weak 14.3% / no 3.6%`
  - 153-run 必要性实验：`oracle 46.7% / weak 11.1% / no 6.7%`，诱饵命中从 `28 -> 24 -> 2`
  - F9K1122 族内区分型 oracle skill：`20% -> 66.7%`
  - FH451 族内区分为负结果：`4/15 < 6/15`，说明这类区分收益是 family-dependent，不可泛化
- 当前真正要继续补的，不是再证明“闭环存在”，而是补系统完整性证据：
  - 发布后的 skill 是否真的提升后续分析
  - catalog 检索路径是否优于当前 inline 注入
  - 检索、反馈、gate 三处是否还会继续放大误差

## 关键证据文件

- 84-run 清洁重跑记录：  
  [reports/current/briefing_20260816/planA_clean_rerun_validation_20260820.md](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260816/planA_clean_rerun_validation_20260820.md)
- 153-run 必要性实验：  
  [reports/current/briefing_20260816/plan1_necessity_frozen_validation_20260820.md](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260816/plan1_necessity_frozen_validation_20260820.md)
- F9K1122 族内区分实验：  
  [reports/current/briefing_20260816/f9k_distinguishing_validation_20260820.md](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260816/f9k_distinguishing_validation_20260820.md)
- FH451 负结果与旧数据作废：  
  [reports/current/briefing_20260816/fh451_distinguishing_validation_20260820.md](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260816/fh451_distinguishing_validation_20260820.md)  
  [reports/current/briefing_20260816/fh451_old_60run_disposition_20260820.md](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260816/fh451_old_60run_disposition_20260820.md)
- gate 修复与 pending 清空：  
  [reports/current/briefing_20260816/gate_settle_20260820.md](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260816/gate_settle_20260820.md)

## 历史入口

- 2026-08-16 阶段包：  
  [reports/current/briefing_20260816/glm_handoff_20260816.md](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260816/glm_handoff_20260816.md)  
  [reports/current/briefing_20260816/session_archive_20260816.md](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260816/session_archive_20260816.md)
- 2026-08-15 阶段包：  
  [reports/current/briefing_20260815/glm_handoff_20260815.md](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260815/glm_handoff_20260815.md)  
  [reports/current/briefing_20260815/session_archive_20260815.md](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260815/session_archive_20260815.md)
