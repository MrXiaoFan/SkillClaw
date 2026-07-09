# 实验框架架构说明

这份文档只说明“工程框架怎么组织”，不讨论某个具体 CVE 的漏洞细节。

## 1. 当前框架的目标

当前在原生 SkillClaw 之外，额外搭了一条面向漏洞分析实验的闭环：

1. 用统一入口跑单个或多个 case；
2. 对 agent 输出做结构化评分；
3. 对结果做静态/动态 validator 校验；
4. 把 skill 注入记录回填到最终实验记录；
5. 从 final record 汇总出 skill 级反馈、gate 决策和反馈 bundle。

也就是说，现在这套东西不是“单纯多了几个 case 脚本”，而是多了一层实验执行与反馈分析框架。

## 2. 哪些是框架，哪些是 case

### 2.1 框架层

框架层主要在：

- `experiment_scripts/`
- `experiment_validation/`

它们负责统一执行、评分、验证、汇总、反馈，不绑定某一个具体漏洞。

### 2.2 case 层

case 层主要在：

- `experiment_cases/`
- `experiment_records/remote_runs/`

它们负责某个目标软件、某个漏洞、某个 PoC、某组 ground truth 和输出记录。

所以要区分：

- `run_eval_case.py` 这种是通用执行器；
- 某个 case JSON 里写的 `prepare_artifacts.sh`、`make_poc.py`、目标二进制路径、触发命令，才是具体 case 内容。

## 3. experiment_scripts 分层

现在 `experiment_scripts/` 被拆成四层。

### 3.1 execution

负责“跑起来”。

- `execution/run_eval_case.py`
  - 单 case 主入口；
  - 串起 prompt 生成、preflight、调用 agent、评分、validator、final record 输出。
- `execution/run_case_batch.py`
  - 多 case 批跑入口；
  - 对 manifest 里的每个 case 复用 `run_eval_case`。
- `execution/run_dynamic_case.py`
  - 单独执行 validator 链。
- `execution/score_agent_output.py`
  - 按文件、函数、根因、证据、CVE 等维度打分。

### 3.2 postprocess

负责“把零散结果拼成标准记录”。

- `postprocess/build_result_record.py`
  - 合并 score / validation / injection。
- `postprocess/attach_skill_injection.py`
  - 给 final record 回填 server 侧 skill 注入记录。
- `postprocess/finalize_experiment_record.py`
  - 对远端拉回结果做最终整理。
- `postprocess/compare_experiment_records.py`
  - 比较两份 final record。
- `postprocess/extract_skill_injection.py`
  - 从注入日志里提取需要的字段。

### 3.3 feedback

负责“从 case 结果上升到 skill 结果”。

- `feedback/summarize_results.py`
  - 生成实验矩阵。
- `feedback/summarize_skill_feedback.py`
  - 按 skill 聚合多个 case 的结果。
- `feedback/build_skill_gate_report.py`
  - 给 skill 打 gate：`promote / keep / revise / demote / insufficient_evidence`。
- `feedback/build_skill_feedback_bundle.py`
  - 生成供 skill 修改使用的反馈包。
- `feedback/refresh_curated_reports.py`
  - 固定顺序刷新整套最新报告。
- `feedback/summarize_research_claims.py`
  - 从 final records 中提炼研究观察。

### 3.4 utils

负责辅助能力，不直接定义实验逻辑。

- `utils/check_experiment_env.py`
- `utils/print_case_prompt.py`
- `utils/print_case_runbook.py`
- `utils/skill_bundle_runner.py`
- `utils/smoke_validate_framework.py`
- `utils/package_experiment_framework.py`
- `utils/send_remote_tmux.ps1`

## 4. 一条完整链路怎么走

### 4.1 跑实验

入口通常是：

- `experiment_scripts/run_eval_case.py`
- 或 `experiment_scripts/run_case_batch.py`

注意：顶层这些脚本现在是“兼容入口”，真实实现已经在子目录里。

### 4.2 生成中间产物

`run_eval_case.py` 会写出：

- `prompt`
- `raw`
- `stderr`
- `run.meta`
- `score.json`
- `validation.json`
- `final.json`

这一步解决的是“实验结果落盘不统一”的问题。

### 4.3 回填 skill 注入记录

如果 run 时不能直接把 SkillClaw server 的注入记录带回来，就用：

- `attach_skill_injection.py`
- 或 `finalize_experiment_record.py`

把 `session_id`、`selected_skill_names`、注入历史重新补到 final record 里。

### 4.4 汇总 feedback

再从一批 final record 生成：

- 结果矩阵：`summarize_results.py`
- skill 聚合：`summarize_skill_feedback.py`
- gate 报告：`build_skill_gate_report.py`
- feedback bundle：`build_skill_feedback_bundle.py`

这一步才构成“skill 反馈闭环”。

## 5. 动态验证闭环在工程里对应哪几块

动态验证闭环不是单个脚本，而是下面几层一起完成的：

1. `experiment_cases/*.json`
   - 定义 validator、artifact、命令、期望结果；
2. `experiment_validation/`
   - 真正执行 `content_match / source_contains / command / bundle_script / asan_command`；
3. `execution/run_eval_case.py`
   - 调用 validator runner；
4. `postprocess/build_result_record.py`
   - 把 validation 写入标准 record；
5. `feedback/*`
   - 再把 validation 结果转成 skill 级反馈。

所以“动态验证闭环”是：

`case 定义 -> validator 执行 -> final record -> skill feedback`

而不是“某个 PoC 脚本自己跑通了”就算闭环完成。

## 6. skill 反馈与 gate 闭环在工程里对应哪几块

skill 反馈与 gate 闭环主要是：

1. `summarize_skill_feedback.py`
   - 把多个 final record 聚合到 skill 维度；
2. `build_skill_gate_report.py`
   - 按样本数、均值、定位成功、validator 是否通过等信号做 gate；
3. `build_skill_feedback_bundle.py`
   - 生成可交给 skill 修改阶段的 bundle；
4. `refresh_curated_reports.py`
   - 把上面几步固定成一条刷新链。

这一步的重点不是“自动改 skill”，而是先把“该不该改、为什么改、改哪一维”结构化。

## 7. 为什么还保留顶层旧脚本

比如下面这些：

- `experiment_scripts/run_eval_case.py`
- `experiment_scripts/build_result_record.py`
- `experiment_scripts/refresh_curated_reports.py`

目前仍然保留，是为了：

1. 兼容已有命令；
2. 兼容现有测试；
3. 兼容已有实验记录和文档。

所以当前是“双层形态”：

- 子目录里放真实实现；
- 顶层脚本只做兼容包装。

这是一种过渡性重构，不会影响你继续跑实验。

## 8. 当前还不够整齐的地方

现在已经比之前清楚很多，但还没到完全收口：

1. 顶层兼容脚本数量仍然较多；
2. `experiment_records/README.md` 还保留较多历史实验叙述；
3. 框架脚本与 case 文档虽然已经分层，但命名风格还没有完全统一；
4. 还缺一份“最小必看入口清单”给新读者快速上手。

## 9. 现阶段建议的阅读顺序

如果只想理解框架，不想先陷进 case 细节，建议按这个顺序看：

1. `experiment_scripts/ARCHITECTURE.md`
2. `experiment_scripts/README.md`
3. `experiment_scripts/execution/run_eval_case.py`
4. `experiment_validation/runner.py`
5. `experiment_scripts/postprocess/build_result_record.py`
6. `experiment_scripts/feedback/summarize_skill_feedback.py`
7. `experiment_scripts/feedback/build_skill_gate_report.py`

这样会先看到主干，再回头看具体 case。
