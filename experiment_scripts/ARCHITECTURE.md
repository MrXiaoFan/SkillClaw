# 实验框架架构说明

这份文档只解释工程框架如何组织，不讨论某个具体 CVE 的漏洞细节。

## 1. 当前框架要解决什么问题

在原生 SkillClaw 之外，现在额外搭了一层面向漏洞分析实验的执行与反馈框架，目标是把下面几件事接成闭环：

1. 跑单个或多个实验 case
2. 对 agent 输出做结构化评分
3. 对结果做静态或动态 validator 校验
4. 把 skill 注入记录回填到最终实验记录
5. 从 final record 汇总出 skill 级反馈和 gate 结论

所以现在新增的并不只是“若干 case 脚本”，而是一套实验执行与反馈基础设施。

## 2. 框架层和案例层怎么区分

### 2.1 框架层

框架层主要在：

- `experiment_scripts/`
- `experiment_validation/`

它们负责统一执行、评分、验证、汇总、反馈，不绑定某个具体漏洞。

### 2.2 案例层

案例层主要在：

- `experiment_cases/`
- `experiment_records/remote_runs/`

它们负责：

- 某个目标软件
- 某个漏洞
- 某个 ground truth
- 某个 PoC / wrapper / 输入输出约束

所以：

- `run_eval_case.py` 这类文件属于通用执行器
- case JSON、`prepare_artifacts.sh`、`make_poc.py`、目标路径和触发命令属于案例适配器

## 3. experiment_scripts 的四层分工

### 3.1 execution

负责“把实验跑起来”。

- `run_eval_case.py`：单 case 主入口
- `run_case_batch.py`：批量执行入口
- `run_dynamic_case.py`：单独运行动态验证
- `score_agent_output.py`：按统一维度评分

### 3.2 postprocess

负责“把分散结果拼成标准记录”。

- `build_result_record.py`
- `attach_skill_injection.py`
- `finalize_experiment_record.py`
- `extract_skill_injection.py`
- `compare_experiment_records.py`

### 3.3 feedback

负责“把 case 级结果上升到 skill 级结果”。

- `summarize_results.py`
- `summarize_skill_feedback.py`
- `build_skill_gate_report.py`
- `build_skill_feedback_bundle.py`
- `refresh_curated_reports.py`
- `summarize_research_claims.py`

### 3.4 utils

负责辅助能力。

- `check_experiment_env.py`
- `print_case_prompt.py`
- `print_case_runbook.py`
- `skill_bundle_runner.py`
- `smoke_validate_framework.py`
- `package_experiment_framework.py`
- `send_remote_tmux.ps1`

## 4. 一条完整链路怎么走

### 4.1 跑实验

入口通常是：

- `experiment_scripts/run_eval_case.py`
- 或 `experiment_scripts/run_case_batch.py`

注意：顶层这些脚本现在主要是兼容入口，真实实现已经下沉到分层子目录。

### 4.2 生成中间产物

`run_eval_case.py` 会持续写出：

- `prompt`
- `raw`
- `stderr`
- `run.meta`
- `score.json`
- `validation.json`
- `final.json`

这样实验结果的落盘格式就是统一的。

### 4.3 回填 skill 注入

如果 run 时没有直接把 SkillClaw server 侧的注入信息带回来，就通过：

- `attach_skill_injection.py`
- 或 `finalize_experiment_record.py`

把 `session_id`、`selected_skill_names` 和注入历史补回 `final record`。

### 4.4 汇总 skill feedback

然后再从一批 `final record` 生成：

- 结果矩阵：`summarize_results.py`
- skill 汇总：`summarize_skill_feedback.py`
- gate 报告：`build_skill_gate_report.py`
- feedback bundle：`build_skill_feedback_bundle.py`

到这里才构成完整的 skill 反馈闭环。

## 5. 动态验证闭环对应工程的哪几块

动态验证闭环不是某一个脚本，而是下面几层一起完成：

1. `experiment_cases/*.json`
   - 定义 validator、artifact、命令、期望结果
2. `experiment_validation/`
   - 真实执行 `content_match / source_contains / command / artifact_exists / artifact_exec / asan_command / bundle_script`
3. `execution/run_eval_case.py`
   - 调用 validator runner
4. `postprocess/build_result_record.py`
   - 把 validation 写入标准记录
5. `feedback/*`
   - 再把 validation 结果转成 skill 级反馈

因此“动态验证闭环”应理解为：

`case 定义 -> validator 执行 -> final record -> skill feedback`

而不是“某个 PoC 脚本单独跑通了”。

## 6. 为什么还保留顶层旧脚本

例如：

- `experiment_scripts/run_eval_case.py`
- `experiment_scripts/build_result_record.py`
- `experiment_scripts/refresh_curated_reports.py`

目前仍保留，是为了：

1. 兼容已有命令
2. 兼容现有测试
3. 兼容已有实验记录和文档

所以当前是一个过渡态：

- 子目录里放真实实现
- 顶层脚本只做兼容包装

这是一种渐进式重构，不会影响继续跑实验。

## 7. 当前还不够整齐的地方

虽然比之前清楚很多，但还没有完全收口：

1. 顶层兼容脚本数量仍然偏多
2. `experiment_records/` 里历史记录和方法说明还混在一起
3. 案例适配脚本的命名和共享 helper 还可以继续统一
4. 还缺一份更短的“最小必看入口清单”

## 8. 推荐阅读顺序

如果只想先理解框架，不想先陷进具体漏洞细节，建议按这个顺序看：

1. `experiment_scripts/ARCHITECTURE.md`
2. `experiment_scripts/README.md`
3. `experiment_scripts/execution/run_eval_case.py`
4. `experiment_validation/runner.py`
5. `experiment_scripts/postprocess/build_result_record.py`
6. `experiment_scripts/feedback/summarize_skill_feedback.py`
7. `experiment_scripts/feedback/build_skill_gate_report.py`

这样会先看到主干，再回头看具体 case。
