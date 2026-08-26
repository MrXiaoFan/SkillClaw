# Agent Handoff

建议新的 agent 先按下面顺序进入，而不是再从更早的单篇阶段文档直接起步：

1. [docs/handoff/20260820/01_necessity_plan_done_and_next.md](/D:/Code/SkillClaw/SkillClaw/docs/handoff/20260820/01_necessity_plan_done_and_next.md)
2. [docs/plans/work_plan_20260820.md](/D:/Code/SkillClaw/SkillClaw/docs/plans/work_plan_20260820.md)
3. [docs/plans/research_roadmap_20260820.md](/D:/Code/SkillClaw/SkillClaw/docs/plans/research_roadmap_20260820.md)
4. [reports/current/experiment_archive_all_20260820.md](/D:/Code/SkillClaw/SkillClaw/reports/current/experiment_archive_all_20260820.md)
5. [reports/current/briefing_20260816/weekly_report_20260823_draft.md](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260816/weekly_report_20260823_draft.md)
6. [paper/skillclaw_confirmation_feedback_elsarticle.tex](/D:/Code/SkillClaw/SkillClaw/paper/skillclaw_confirmation_feedback_elsarticle.tex)

## 当前真实状态

- 主链路已经能跑通：
  `run -> score / confirmation -> feedback -> evolve -> gate -> publish`
- 当前更可信的实验主证据，已经切到 `runtime/ablation/` 和 `reports/current/briefing_20260816/` 这批净化后的记录，不再以前期混杂 run 为主证据。
- 论文当前主稿仍然是：
  [paper/skillclaw_confirmation_feedback_elsarticle.tex](/D:/Code/SkillClaw/SkillClaw/paper/skillclaw_confirmation_feedback_elsarticle.tex)
- 2026-08-26 又做了一轮目录收紧：
  - `paper/materials_20260824/` 和 `paper/package_20260824/` 中重复保存的 `session_rollout_20260816.jsonl` 已删除
  - 原始会话主副本统一只保留在：
    [reports/current/briefing_20260816/session_rollout_20260816.jsonl](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260816/session_rollout_20260816.jsonl)
  - `skillspace/.skillclaw_backups/` 已明确视为运行时缓存，不是 canonical skill 内容
- 上一轮目录整理已同步到：
  - `28bf4c5 cleanup: dedupe paper session archives`
- GitHub 镜像 `fan/dev` 在这轮同步时因为网络连接失败没有推上去，所以可能比 `codeup/dev` 落后一个 commit。

## 当前最该看的证据文件

- 84-run 清洁重跑：
  [reports/current/briefing_20260816/planA_clean_rerun_validation_20260820.md](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260816/planA_clean_rerun_validation_20260820.md)
- 153-run 必要性实验：
  [reports/current/briefing_20260816/plan1_necessity_frozen_validation_20260820.md](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260816/plan1_necessity_frozen_validation_20260820.md)
- F9K1122 家族内区分实验：
  [reports/current/briefing_20260816/f9k_distinguishing_validation_20260820.md](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260816/f9k_distinguishing_validation_20260820.md)
- FH451 负结果与旧数据对照：
  [reports/current/briefing_20260816/fh451_distinguishing_validation_20260820.md](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260816/fh451_distinguishing_validation_20260820.md)
  [reports/current/briefing_20260816/fh451_old_60run_disposition_20260820.md](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260816/fh451_old_60run_disposition_20260820.md)
- gate settle 记录：
  [reports/current/briefing_20260816/gate_settle_20260820.md](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260816/gate_settle_20260820.md)
- 2026-08-26 清理说明：
  [reports/current/cleanup_20260826.md](/D:/Code/SkillClaw/SkillClaw/reports/current/cleanup_20260826.md)

## 本轮整理后的冒烟核对结果

- 主副本存在：
  - `reports/current/briefing_20260816/session_rollout_20260816.jsonl` 存在
- `paper/` 中重复的大 jsonl 副本已去掉：
  - `paper/materials_20260824/reports/briefing_20260816/session_rollout_20260816.jsonl` 不存在
  - `paper/package_20260824/support/reports/briefing_20260816/session_rollout_20260816.jsonl` 不存在
- `skillspace/` 主路径仍在：
  - `skillspace/live/`
  - `skillspace/source/`
  - `skillspace/share/`

## 当前建议的下一步

1. 不要继续清理目录，先回主线实验。
2. 下一步最值得做的是严格隔离的 held-out evolved-skill 实验准备，补“自动生成的 candidate skill 是否真的改善未来 blind 任务”这条证据。
3. 在那之前，如果需要继续读代码或材料，优先以 `codeup/dev` 为准，不要默认 GitHub 镜像就是最新。

## 源码仓链接

- Codeup：
  `https://codeup.aliyun.com/5ffbfe6c168c689c9272cf25/skillclaw_extention/tree/dev`
- GitHub 镜像：
  `https://github.com/MrXiaoFan/SkillClaw/tree/dev`
- 原始上游：
  `https://github.com/AMAP-ML/SkillClaw/tree/main`
