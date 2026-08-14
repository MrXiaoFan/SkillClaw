# Docs

先读这三份交接材料，再做服务重启、远端 VM 操作、论文修改或工程重构：

1. [handoff/20260811/01_research_and_development_state.md](handoff/20260811/01_research_and_development_state.md)
2. [handoff/20260811/03_engineering_status_tests_and_next_plan.md](handoff/20260811/03_engineering_status_tests_and_next_plan.md)
3. [handoff/20260812/01_runtime_handoff_and_service_bootstrap.md](handoff/20260812/01_runtime_handoff_and_service_bootstrap.md)

## 当前最重要的实验证据

当前 firmware 远端 blind 闭环，以这组四路对照为准：

- 汇总 JSON：
  - [reports/current/briefing_20260811/firmware_wireless_real_runs_20260811.json](../reports/current/briefing_20260811/firmware_wireless_real_runs_20260811.json)
- 汇总 Markdown：
  - [reports/current/briefing_20260811/firmware_wireless_real_runs_20260811.md](../reports/current/briefing_20260811/firmware_wireless_real_runs_20260811.md)
- 四个核心 run：
  - `runtime/imports/remote_vm/firmware2-wireless-none-20260812c/`
  - `runtime/imports/remote_vm/firmware2-wireless-seed-20260812a/`
  - `runtime/imports/remote_vm/firmware2-wireless-wrong-20260812h/`
  - `runtime/imports/remote_vm/firmware2-wireless-live-20260812i/`

这四组数据目前支持的结论是：

- 远端 `Claude -> SkillClaw -> Evolve -> replay gate` 链路真实闭环；
- `wrong skill` 和 `seed skill` 都可能进入 candidate 阶段；
- 但还没有任何一组证明 skill 已经带来可发布的正向提升。

`docs/` 只放给人读的材料，不放批量机器产物。

## 目录

- `cases/`
  - 各案例背景、现状和人工说明
- `handoff/`
  - 交接文件，优先保证别的 agent 能直接续上
- `ops/`
  - 远端 VM、手工执行、排障记录
- `plans/`
  - 下一步案例与工程计划
- `reference/`
  - 架构说明、评分规则、统一口径
- `weekly/`
  - 周报与阶段性总结

## 建议阅读顺序

如果目的是理解当前工程结构，先看：

1. `reference/extension_architecture.md`
2. `reference/extension_architecture_summary.md`
3. `cases/README.md`

如果目的是继续推进工程或实验，先看：

1. `handoff/20260812/01_runtime_handoff_and_service_bootstrap.md`
2. `handoff/20260811/03_engineering_status_tests_and_next_plan.md`
3. `reports/current/briefing_20260811/firmware_wireless_real_runs_20260811.json`

如果目的是做汇报或论文准备，先看：

1. `weekly/`
2. `handoff/20260811/02_paper_frame_and_manuscript_state.md`
3. `reports/current/briefing_20260811/firmware_wireless_real_runs_20260811.md`
