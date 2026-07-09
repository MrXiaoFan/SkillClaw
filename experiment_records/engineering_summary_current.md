# 当前工程总结

## 1. 当前工程目标

当前工程不是单纯修改几个 Skill，也不是只补几个漏洞 case，而是在原生 SkillClaw 之上补了一条面向漏洞分析任务的实验闭环，目标包括：

1. 让 SkillClaw 的 server-side skill 注入更贴近漏洞分析任务；
2. 让单个漏洞 case 能以统一方式执行、评分、验证和落盘；
3. 让 case 结果能上升为 skill 级反馈，而不只停留在单次实验记录；
4. 为后续 skill 修改、PoC 生成与确认性实验提供统一工程底座。

## 2. 相比原生 SkillClaw，新增了什么

当前新增内容可以分成两部分。

### 2.1 SkillClaw 主干增强

主要文件：

- `skillclaw/skill_manager.py`

主要增强点：

1. `select_skills_for_inline(...)`
   - 为漏洞分析任务选择少量更值得注入的 skills。
2. `_keyword_retrieve_for_inline(...)`
   - 在 embedding 检索之外增加 lexical overlap 排序和任务对齐控制。
3. `format_inline_skills_for_prompt(...)`
   - 统一组织 server-side skill 注入内容。
4. `build_inline_injection_prompt(...)`
   - 生成最终注入 prompt，并明确区分 SkillClaw server skills 与本地 Claude Code skills。

这部分改动直接影响 SkillClaw 的运行行为，而不是实验脚本层面的包装。

### 2.2 漏洞分析实验闭环框架

主要目录：

- `experiment_scripts/`
- `experiment_validation/`
- `experiment_cases/`

这部分是原生 SkillClaw 没有的额外实验框架。

## 3. 当前工程结构形态

`experiment_scripts/` 已整理为四层结构。

### 3.1 execution

负责执行实验。

关键文件：

- `execution/run_eval_case.py`
- `execution/run_case_batch.py`
- `execution/run_dynamic_case.py`
- `execution/score_agent_output.py`

关键函数：

- `run_case(...)`
- `run_batch(...)`
- `run_validators(...)`
- `score_output(...)`

### 3.2 postprocess

负责把中间结果拼成标准实验记录。

关键文件：

- `postprocess/build_result_record.py`
- `postprocess/attach_skill_injection.py`
- `postprocess/finalize_experiment_record.py`
- `postprocess/compare_experiment_records.py`

关键能力：

- score / validation / injection 合并
- skill 注入记录回填
- final record 比较

### 3.3 feedback

负责把 case 结果汇总成 skill 级反馈。

关键文件：

- `feedback/summarize_results.py`
- `feedback/summarize_skill_feedback.py`
- `feedback/build_skill_gate_report.py`
- `feedback/build_skill_feedback_bundle.py`
- `feedback/refresh_curated_reports.py`

关键函数：

- `build_skill_feedback(...)`
- `build_gate_report(...)`
- `build_feedback_bundles(...)`
- `refresh_reports(...)`

### 3.4 utils

负责 preflight、prompt、runbook、smoke test 和 bundle script 等辅助能力。

关键文件：

- `utils/check_experiment_env.py`
- `utils/print_case_prompt.py`
- `utils/print_case_runbook.py`
- `utils/skill_bundle_runner.py`
- `utils/smoke_validate_framework.py`

## 4. 动态验证闭环怎么落地

当前“动态验证闭环”不是某一个脚本，而是以下链路共同组成：

1. `experiment_cases/*.json`
   - 定义 ground truth、artifact、validator、command、script。
2. `experiment_validation/runner.py`
   - 按 case 配置执行验证项。
3. `experiment_validation/validators.py`
   - 实现不同类型验证，例如：
   - `content_match`
   - `source_contains`
   - `command`
   - `bundle_script`
   - `asan_command`
4. `execution/run_eval_case.py`
   - 把 validator 纳入单 case 主执行流程。
5. `postprocess/build_result_record.py`
   - 把 validation 结果写入统一 final record。
6. `feedback/*`
   - 再把 validation 上升为 skill 级反馈。

因此当前闭环应理解为：

`case 定义 -> validator 执行 -> final record -> skill feedback`

而不是“某个 PoC 脚本能跑”就算闭环完成。

## 5. skill 反馈闭环怎么落地

当前“skill 反馈与 gate 闭环”主要由以下模块组成：

1. `summarize_skill_feedback.py`
   - 按 skill 聚合多个 final record。
2. `build_skill_gate_report.py`
   - 基于样本数、平均分、定位命中、validator 是否通过等信号给出 gate。
3. `build_skill_feedback_bundle.py`
   - 将 skill 修改所需证据整理成结构化 bundle。
4. `refresh_curated_reports.py`
   - 将矩阵、feedback、gate、bundle 刷新成固定顺序的整套输出。

这一层的重点不是自动改 skill，而是把“是否该改、为什么改、改哪一维”结构化。

## 6. 当前核心执行入口

如果只保留最关键的入口，当前应重点看：

1. `skillclaw/skill_manager.py`
2. `experiment_scripts/execution/run_eval_case.py`
3. `experiment_validation/runner.py`
4. `experiment_validation/core.py`
5. `experiment_scripts/postprocess/build_result_record.py`
6. `experiment_scripts/feedback/summarize_skill_feedback.py`
7. `experiment_scripts/feedback/build_skill_gate_report.py`

这 7 个位置基本串起了“Skill 注入增强 + case 执行 + validator + final record + skill feedback”。

## 7. 当前最重要的工程文档

目前仓库里已经形成了四份互补文档：

- `experiment_scripts/QUICKSTART.md`
  - 最小入口与最常用命令。
- `experiment_scripts/ARCHITECTURE.md`
  - 架构视角说明。
- `experiment_scripts/README.md`
  - 目录分层说明。
- `experiment_scripts/MODULE_INVENTORY.md`
  - 相比原生 SkillClaw 新增模块清单。

这四份文档已经足够支撑后续汇报、交接和论文思路梳理。

## 8. 当前工程已经达到什么状态

当前状态可以概括为：

1. `experiment_scripts` 已完成结构整改；
2. 顶层兼容入口仍保留，旧命令不受影响；
3. 关键回归测试已通过；
4. 工程主干已经从“零散脚本”收拢为“可解释的分层框架”；
5. 现在可以继续将工作重心切回 case 扩展、动态验证强化和 PoC/confirmation 实验。

## 9. 现阶段最适合对外怎么描述

如果要用一段较稳定的话描述当前工作，可以直接说：

> 我们在原生 SkillClaw 的 server-side skill injection 基础上，补了一层面向漏洞分析任务的实验与反馈闭环。前端包括 inline skill selection、keyword-based retrieval 和 prompt injection 组织；后端包括 case 执行、validator、final record、skill feedback、gate decision 和 feedback bundle。当前工程已经从零散 case 脚本收拢为可复用的分层实验框架。

## 10. 下一步主线

当前结构整改已经基本完成，后续主线建议回到工程开发与实验本身：

1. 增加更多 confirmation case，而不是只围绕少数 CVE 做归纳；
2. 扩展动态验证方式，减少对 case 定制脚本的依赖；
3. 继续观察 skill-task alignment 与 validator-grounded feedback 的实际效果；
4. 逐步把关注点从“漏洞定位”延伸到“PoC 生成与验证”。
