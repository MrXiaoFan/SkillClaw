# 阶段性工作记录：Gate 落定守卫修复（D1/D2）+ 21 个卡死 job 清理（2026-08-20）

## 背景与问题
- Evolve server 的 replay gate 在 `workflow.py:_finalize_validation_jobs` 中，
  `publish_ready` 需要「结果数达标 + 通过批准数 + gate 通过」，而
  `reject_ready` 只看 `rejected >= validation_max_rejections`。
- 当 `validation_required_results=1`、`validation_max_rejections=3` 时，一个
  **单条、被拒** 的结果既满足不了 publish（无批准）也够不着 reject 阈值，
  于是该 job 永远 pending，永不落定。这是计划文档 D1 所指的 “34 pending” 类缺陷源码。
- 另外 `publish_mode` 默认是 `direct`，只在 `start_evolve.ps1` 显式传
  `--publish-mode validated` 时才走 gate；若改由其他入口/兜底启动，技能会绕过门控直接发布（D2）。

## 本次改动
1. **D1（`evolve_server/engines/workflow.py`）**：在计算 `reject_ready` 后加守卫——
   只要「结果数 >= required_results 且不可发布」，就把 job 判为 reject 落定，
   不再无限挂起。原则：证据数达到门槛后 job 必须发布或拒绝，二选一。
2. **D2（`evolve_server/core/config.py`）**：`publish_mode` 默认改为 `validated`
   （dataclass 默认、归一化兜底、两处 env 回退改为 `"validated"`），使未显式指定时也不绕过 gate。
   `start_evolve.ps1` 已显式传 `--publish-mode validated`，行为不变、仅更稳。
3. 新增单元测试 `tests/test_gate_settle_guard.py`（守恒：单条被拒 → reject；
   可发布 → publish；结果数不达标 → 保持 pending；混合批准且 gate 过 → publish）。5 例全过。

## 线上清理
- 用 `ReplayGateStore` 实测：`gate_jobs + validation_jobs` 共 119 个 job，
  其中 **21 个** 有意向但无 decision、各有 1 条结果且全部被拒（real_rerun，
  score < 0.6 阈值）。
- 按 D1 新逻辑 dry-run 确认（would_reject=21、would_publish=0），随后 `--apply`
  落定这 21 个为 **rejected**（reason=settled_by_d1_guard）。
- 复检：pending（no decision）= **0**。这 21 个是“单条被拒但没到 3 次拒绝”的卡死实例，
  与 D1 根因吻合，也正好验证了修复的必要性。
- 脚本与日志：`runtime/tmp/gate_audit/audit_pending.py`、`audit_details.py`、
  `settle_pending.py`、`settle_apply_20260820_211156.txt`。

## 结论 / 验收
- pending 不再堆积：从 21 → 0；且今后单条被拒的 job 也会自动落定为 reject。
- 所有发布均走 validated（默认）或 start_evolve.ps1 显式 validated。
- 对应计划项：`work_plan_20260820.md` 第 2.1（D1+D2）已落地。
  commit：65a6472（代码）+ 本次记录（文档）。
