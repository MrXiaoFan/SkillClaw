# experiment_scripts 目录说明

建议先读：

1. `QUICKSTART.md`
2. `ARCHITECTURE.md`
3. 本文档

`experiment_scripts/` 现在按“执行层 / 反馈层 / 后处理层 / 工具层”分层，顶层仍保留同名兼容入口，保证旧命令还能继续运行。

## 1. execution

负责真正跑实验主链路。

- `execution/run_eval_case.py`
  - 单个 case 的统一入口。
  - 负责：生成 prompt、可选 preflight、调用 agent、评分、跑 validator、写出 final record。
- `execution/run_case_batch.py`
  - 按 manifest 批量执行多个 case。
- `execution/run_dynamic_case.py`
  - 跑动态验证脚本链路。
- `execution/score_agent_output.py`
  - 对 agent 输出按漏洞定位维度打分。

## 2. feedback

负责把 final record 汇总成可分析的反馈结果。

- `feedback/summarize_results.py`
  - 生成结果矩阵。
- `feedback/summarize_skill_feedback.py`
  - 汇总 skill 反馈统计。
- `feedback/build_skill_gate_report.py`
  - 生成 skill gate 决策结果。
- `feedback/build_skill_feedback_bundle.py`
  - 生成可用于 skill 修改的反馈包。
- `feedback/refresh_curated_reports.py`
  - 固定顺序刷新整套 curated report。
- `feedback/summarize_research_claims.py`
  - 从结果中提炼研究观察。

## 3. postprocess

负责把评分、注入记录、比较结果拼成最终实验记录。

- `postprocess/build_result_record.py`
  - 将 score / validation / injection 合并成标准 record。
- `postprocess/attach_skill_injection.py`
  - 后补 skill 注入信息和 feedback。
- `postprocess/finalize_experiment_record.py`
  - 对拉回的结果做最终整理并可选输出 compare。
- `postprocess/extract_skill_injection.py`
  - 从日志里抽取 skill 注入记录。
- `postprocess/compare_experiment_records.py`
  - 比较两个实验记录。

## 4. utils

负责环境检查、提示打印、打包、辅助执行。

- `utils/check_experiment_env.py`
- `utils/print_case_prompt.py`
- `utils/print_case_runbook.py`
- `utils/package_experiment_framework.py`
- `utils/skill_bundle_runner.py`
- `utils/smoke_validate_framework.py`
- `utils/send_remote_tmux.ps1`

## 5. 顶层兼容层

例如：

- `experiment_scripts/run_eval_case.py`
- `experiment_scripts/build_result_record.py`
- `experiment_scripts/refresh_curated_reports.py`

这些文件现在只是薄包装器，主要作用是：

1. 兼容旧命令；
2. 避免已有测试、已有文档、已有批处理脚本全部改一遍。

也就是说：

- 新实现应优先写在分层子目录里；
- 旧路径先保留，等整套实验链路稳定后再考虑是否彻底移除。
