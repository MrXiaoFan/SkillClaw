# 模块清单：相比原生 SkillClaw 额外开发了什么

这份文档的目标不是讲某个具体漏洞，而是回答一个更工程化的问题：

**相比原生 SkillClaw，这个仓库现在额外多了哪些模块，它们分别负责什么，核心函数是什么。**

## 1. 先说结论

当前新增内容可以分成两大块：

1. **SkillClaw 主干增强**
   - 主要体现在 `skillclaw/skill_manager.py`
   - 目标是让 server 侧 skill 更稳定地完成 inline 注入与任务对齐

2. **漏洞分析实验闭环框架**
   - 主要体现在 `experiment_scripts/` 和 `experiment_validation/`
   - 目标是把 case 执行、评分、验证、汇总、skill 反馈连成一条可复用链路

也就是说，新增内容不是只改了 skill 检索，也不是只堆了实验脚本，而是：

- 前半段改 SkillClaw 注入行为；
- 后半段补实验执行与反馈框架。

## 2. 对 SkillClaw 主干本身的改动

### 2.1 文件

- `skillclaw/skill_manager.py`

### 2.2 主要新增/强化能力

#### A. inline skill 选择

核心函数：

- `select_skills_for_inline(...)`

作用：

- 从全部 skills 中挑出当前任务最值得注入的少量 skill；
- 作为 server-side inline injection 的前置选择层。

#### B. keyword-based inline retrieval

核心函数：

- `_keyword_retrieve_for_inline(...)`

作用：

- 不只靠原始 embedding 检索；
- 对漏洞分析任务增加轻量 lexical overlap 排序；
- 对某些明显不对齐的 skill 做压制；
- 对明显对齐的 skill 做加权提升。

现在这个函数实际上承担了“skill-task alignment”的第一道工程控制。

#### C. server-side skill prompt 组织

核心函数：

- `format_inline_skills_for_prompt(...)`
- `build_inline_injection_prompt(...)`

作用：

- 把选中的 server-side skills 组织成统一 prompt 片段；
- 明确告诉 agent：
  - 这些是 SkillClaw server 已加载的 skills；
  - 不要去调用本地 Claude Code 的 `Skill(...)`；
  - 应优先使用已注入 skill 指令。

### 2.3 这部分改动的工程意义

这部分不属于“实验脚本”，而是直接改变了 SkillClaw 在漏洞分析任务中的行为边界：

- 哪些 skill 会被注入；
- 注入顺序和内容如何组织；
- 如何减少不相关 skill 抢占 top-k。

## 3. 新增的实验执行框架

这部分主要在：

- `experiment_scripts/`

它不是原生 SkillClaw 自带的能力，而是为漏洞分析实验额外搭的一层执行框架。

### 3.1 execution：执行层

#### 文件

- `experiment_scripts/execution/run_eval_case.py`
- `experiment_scripts/execution/run_case_batch.py`
- `experiment_scripts/execution/run_dynamic_case.py`
- `experiment_scripts/execution/score_agent_output.py`

#### 核心函数

- `run_case(...)`
- `run_batch(...)`
- `run_validators(...)`
- `score_output(...)`

#### 负责什么

- 单 case 执行
- 多 case 批跑
- 动态/静态 validator 调度
- 结构化评分

#### 工程意义

这层把原来零散的手工实验流程变成了固定入口：

- 输入：case JSON + mode
- 输出：prompt/raw/score/validation/final

### 3.2 postprocess：后处理层

#### 文件

- `experiment_scripts/postprocess/build_result_record.py`
- `experiment_scripts/postprocess/attach_skill_injection.py`
- `experiment_scripts/postprocess/finalize_experiment_record.py`
- `experiment_scripts/postprocess/compare_experiment_records.py`
- `experiment_scripts/postprocess/extract_skill_injection.py`

#### 核心函数

- `attach_injection(...)`
- `finalize_record(...)`

以及 `build_result_record.py` 中的：

- `_select_injection(...)`
- `_select_injection_history(...)`
- `_select_validation(...)`

#### 负责什么

- 把 score / validation / injection 拼成统一 record
- 把 SkillClaw server 侧注入记录回填到 final record
- 比较前后两次实验记录差异

#### 工程意义

这层解决的是：

- 远端跑完实验后，结果格式不统一
- 注入记录和最终结果分离
- 同一个 case 的前后版本难以对比

### 3.3 feedback：反馈层

#### 文件

- `experiment_scripts/feedback/summarize_results.py`
- `experiment_scripts/feedback/summarize_skill_feedback.py`
- `experiment_scripts/feedback/build_skill_gate_report.py`
- `experiment_scripts/feedback/build_skill_feedback_bundle.py`
- `experiment_scripts/feedback/refresh_curated_reports.py`
- `experiment_scripts/feedback/summarize_research_claims.py`

#### 核心函数

- `build_skill_feedback(...)`
- `build_gate_report(...)`
- `build_feedback_bundles(...)`
- `refresh_reports(...)`

#### 负责什么

- 生成实验矩阵
- 按 skill 聚合结果
- 生成 gate 决策
- 生成 skill 修改输入 bundle
- 一键刷新成套报告

#### 工程意义

这层是“skill 反馈闭环”的主要落点：

- 先把 case 结果汇总到 skill 维度；
- 再给 skill 下 gate；
- 再把修改所需证据整理成 bundle。

### 3.4 utils：工具层

#### 文件

- `experiment_scripts/utils/check_experiment_env.py`
- `experiment_scripts/utils/print_case_prompt.py`
- `experiment_scripts/utils/print_case_runbook.py`
- `experiment_scripts/utils/skill_bundle_runner.py`
- `experiment_scripts/utils/smoke_validate_framework.py`
- `experiment_scripts/utils/package_experiment_framework.py`
- `experiment_scripts/utils/send_remote_tmux.ps1`

#### 核心函数

- `check_case_environment(...)`
- `get_case_prompt(...)`
- `render_runbook(...)`
- `run_bundle_script(...)`
- `smoke_cases(...)`

#### 负责什么

- preflight 环境检查
- 从 case JSON 生成 prompt
- 生成 case 运行说明
- 执行 bundle script
- 对验证框架做 smoke test
- 打包实验框架

#### 工程意义

这层不是实验主逻辑，但它把“能不能稳定复现和复跑”补齐了。

## 4. 新增的验证框架

这部分主要在：

- `experiment_validation/core.py`
- `experiment_validation/runner.py`
- `experiment_validation/validators.py`

### 4.1 核心函数

- `run_case_validators(...)` in `runner.py`
- `assess_skill_relevance(...)` in `core.py`
- `build_feedback(...)` in `core.py`

### 4.2 负责什么

#### A. validator 执行

`run_case_validators(...)` 负责按 case 配置执行验证链。

#### B. skill relevance 判断

`assess_skill_relevance(...)` 负责判断：

- 当前 case 选中的 skill 是否和任务匹配；
- 是 matched / mixed / mismatched。

#### C. 反馈生成

`build_feedback(...)` 负责把：

- score
- validation
- skill injection
- relevance

变成统一 feedback 结构。

### 4.3 工程意义

这部分是“validator-grounded feedback”的真正落点。  
没有这层，实验只会停留在：

- 跑了 case
- 得到了一份答案

有了这层以后，才变成：

- 跑了 case
- 验证了结果
- 形成了可汇总、可决策的 feedback

## 5. 顶层兼容层是什么

现在顶层这些脚本仍然保留：

- `experiment_scripts/run_eval_case.py`
- `experiment_scripts/refresh_curated_reports.py`
- `experiment_scripts/build_result_record.py`
- 以及其他同名脚本

它们现在不是主实现，而是**兼容包装器**。

作用只有两个：

1. 保持旧命令继续可用；
2. 让已有测试、已有文档、已有批处理脚本不必全部重写。

所以当前结构是：

- 子目录里放真实实现；
- 顶层脚本只做兼容入口。

## 6. 如果按“模块簇”来讲，现在多了什么

最简洁的说法是：

### 模块簇 A：SkillClaw inline injection 增强

- 文件：`skillclaw/skill_manager.py`
- 关键词：
  - inline selection
  - keyword retrieval
  - prompt assembly

### 模块簇 B：实验执行框架

- 文件：`experiment_scripts/execution/*`
- 关键词：
  - single-case runner
  - batch runner
  - score runner
  - validator dispatch

### 模块簇 C：结果标准化与回填

- 文件：`experiment_scripts/postprocess/*`
- 关键词：
  - final record
  - injection backfill
  - record compare

### 模块簇 D：skill 反馈与 gate

- 文件：`experiment_scripts/feedback/*`
- 关键词：
  - skill aggregation
  - gate decision
  - feedback bundle
  - curated report refresh

### 模块簇 E：validator-grounded feedback 内核

- 文件：`experiment_validation/*`
- 关键词：
  - validator runner
  - skill relevance
  - feedback synthesis

### 模块簇 F：实验复现工具

- 文件：`experiment_scripts/utils/*`
- 关键词：
  - preflight
  - prompt build
  - runbook
  - smoke test
  - bundle script execution

## 7. 现在可以怎么对外描述

如果你要对外讲“相比原生 SkillClaw，我们做了什么”，可以用下面这版：

> 我们没有只做单点 skill 修改，而是在 SkillClaw 原有 skill 注入机制上，补了一层面向漏洞分析的实验与反馈闭环。前端是 server-side inline retrieval 与 prompt injection 强化，后端是 case 执行、validator、final record、skill feedback、gate decision 和 feedback bundle 的成套框架。

## 8. 当前最值得看的核心代码

如果只挑最关键的入口，建议看：

1. `skillclaw/skill_manager.py`
2. `experiment_scripts/execution/run_eval_case.py`
3. `experiment_validation/runner.py`
4. `experiment_validation/core.py`
5. `experiment_scripts/postprocess/build_result_record.py`
6. `experiment_scripts/feedback/summarize_skill_feedback.py`
7. `experiment_scripts/feedback/build_skill_gate_report.py`

这 7 个位置，基本就把“改了什么”和“闭环怎么落地”串起来了。
