# experiment_scripts 目录说明

建议按下面顺序阅读：

1. `QUICKSTART.md`
2. `ARCHITECTURE.md`
3. 本文档

`experiment_scripts/` 现在已经按职责拆成四层：`execution / postprocess / feedback / utils`。  
顶层同名脚本仍然保留，但它们主要是兼容入口，方便旧命令和旧文档继续可用。

## 1. execution

负责真正跑实验主链路。

- `execution/run_eval_case.py`
  - 单个 case 的统一入口
  - 串起 prompt 生成、preflight、agent 调用、评分、validator 执行、final record 输出
- `execution/run_case_batch.py`
  - 按 manifest 批量执行多个 case
- `execution/run_dynamic_case.py`
  - 单独运行动态验证链路
- `execution/score_agent_output.py`
  - 按文件、函数、漏洞类型、根因、证据、输出纪律等维度评分

## 2. postprocess

负责把实验过程中产生的分散结果整理成统一记录。

- `postprocess/build_result_record.py`
  - 合并 score / validation / injection
- `postprocess/attach_skill_injection.py`
  - 后补 SkillClaw server 侧的 skill 注入记录
- `postprocess/finalize_experiment_record.py`
  - 对远端拉回的实验结果做最后整理
- `postprocess/extract_skill_injection.py`
  - 从日志中抽取注入信息
- `postprocess/compare_experiment_records.py`
  - 比较两份实验记录

## 3. feedback

负责把 case 级结果上升到 skill 级反馈。

- `feedback/summarize_results.py`
  - 生成结果矩阵
- `feedback/summarize_skill_feedback.py`
  - 汇总 skill 维度表现
- `feedback/build_skill_gate_report.py`
  - 输出 gate 结论，例如 `promote / keep / revise / demote / insufficient_evidence`
- `feedback/build_skill_feedback_bundle.py`
  - 生成供 skill 修改使用的反馈包
- `feedback/refresh_curated_reports.py`
  - 固定顺序刷新整套 curated 报告
- `feedback/summarize_research_claims.py`
  - 从结果里提炼可复述的研究观察

## 4. utils

负责辅助功能，不直接定义实验主逻辑。

- `utils/check_experiment_env.py`
- `utils/print_case_prompt.py`
- `utils/print_case_runbook.py`
- `utils/package_experiment_framework.py`
- `utils/skill_bundle_runner.py`
- `utils/smoke_validate_framework.py`
- `utils/send_remote_tmux.ps1`

## 5. 顶层兼容入口

例如：

- `experiment_scripts/run_eval_case.py`
- `experiment_scripts/build_result_record.py`
- `experiment_scripts/refresh_curated_reports.py`

这些文件当前主要有两个作用：

1. 兼容旧命令
2. 避免已有测试、已有文档、已有批处理脚本一次性全部改写

因此现在的推荐做法是：

- 新实现优先写进分层子目录
- 顶层入口先保留
- 等实验链路完全稳定后，再决定是否进一步收口

## 6. 如何理解当前工程形态

可以把它看成三层：

1. `experiment_scripts/`  
   负责“怎么跑、怎么记、怎么汇总、怎么反馈”
2. `experiment_validation/`  
   负责“怎么验证”
3. `experiment_cases/`  
   负责“验证哪个目标、哪个漏洞、用什么 case 配置和适配脚本”

也就是说，当前新增的重点已经不只是“多了几个 case 脚本”，而是形成了一套：

`case 定义 -> 执行 -> 评分 -> validator -> final record -> skill feedback`

的实验闭环。
