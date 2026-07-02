# 工程修改说明（截至 2026-07-02）

## 一、对原始 SkillClaw 的核心扩展

### 1. inline skill 检索与注入

- 调整 `skillclaw/skill_manager.py` 中 inline 检索逻辑
- 降低 `skillclaw-*` 自省类 skill 在漏洞任务中的误注入
- 对 parser / source / OOB 类任务提高 `source-parser-state-machine-oob` 的优先级

效果：

- 减少无关 skill 抢占 top-k
- 让 server-side skill 更贴近漏洞分析任务

### 2. injected skill prompt 约束

- 强化 server-side loaded skill prompt
- 明确这些 skill 已作为文本注入
- 明确不要调用本地 `Skill(...)`

效果：

- 降低远端 Claude Code 将 injected skill 与本地 Skill tool 混淆的概率

## 二、实验执行与记录链路

### 1. 统一 runner

新增/增强：

- `experiment_scripts/run_eval_case.py`
- `experiment_scripts/check_experiment_env.py`
- `experiment_scripts/print_case_prompt.py`
- `experiment_scripts/print_case_runbook.py`

效果：

- 统一 case 执行
- 支持 provider preflight
- 支持确认 prompt / runbook 自动生成

### 2. session / injection 自动回填

新增/增强：

- `attach_skill_injection.py`
- `finalize_experiment_record.py`
- `run_eval_case.py` 中 session linkage 推断

效果：

- final record 不再高度依赖手工 post hoc 回填
- 远端 final 拉回本地后可自动补 skill injection

### 3. before/after 自动对比

新增：

- `compare_experiment_records.py`

效果：

- 自动比较 score / CVE / file / function / validation / artifact / feedback 等维度
- 不再手工翻两个 final JSON

## 三、validator 与 dynamic confirmation 扩展

### 1. validator 框架

已有 / 完善：

- `content_match`
- `source_contains`
- `command`
- `bundle_script`
- `asan_command`

### 2. 新增 artifact 验证能力

新增：

- `artifact_exists`
- `artifact_exec`

效果：

- 不只验证“回答写得对不对”
- 还验证 agent 是否真的生成并执行了 artifact

### 3. case schema 扩展

在 case schema 中加入：

- `expected_artifacts`
- `repro.build`
- `repro.run`
- `success_markers`
- `target_frames`

效果：

- case 从“漏洞定位题”扩成“漏洞确认题”

## 四、feedback / revision / evolver 扩展

### 1. skill-level feedback

新增：

- `summarize_skill_feedback.py`
- `build_skill_gate_report.py`
- `build_skill_feedback_bundle.py`

效果：

- 实验结果从 case-level 聚合到 skill-level
- 支持 `promote / keep / revise / demote / insufficient_evidence`

### 2. 维度化反馈

新增或明确：

- localization
- evidence
- root cause
- CVE calibration
- artifact generated
- artifact execution passed

以及：

- `cve_calibration_miss`

效果：

- 能区分“定位正确”和“CVE 正确”

### 3. evolver 输入增强

新增：

- `feedback/SUMMARY.md`
- `feedback/PLAYBOOK.md`
- `revision_directives`
- `revision_templates`

效果：

- evolver 不再只依赖 session summary
- 开始消费 validator-backed feedback

## 五、已完成的三条实验主线

### 1. giflib

定位：

- crash-backed confirmation case

已完成：

- artifact generation
- artifact execution
- ASan confirmation
- compare

### 2. tcpdump

定位：

- behavior-backed confirmation case

已完成：

- SkillClaw confirmation
- direct confirmation
- artifact generation
- artifact execution
- behavior marker validation
- compare

### 3. libxml2

定位：

- revision-study case

已完成：

- localization / evidence validation
- `cve_calibration_miss`
- template-driven revision
- rerun
- compare

## 六、当前工程边界

### 已经做到的

- 闭环原型已经建立
- 两条 confirmation 线（giflib / tcpdump）
- 一条 revision 线（libxml2）

### 还没做到的

- 更多 confirmation case 覆盖
- 更强的 crash-backed confirmation 覆盖
- 足以支撑泛化结论的样本规模

## 七、下一阶段建议

1. 优先新增新的 confirmation case
2. 继续沿统一链路跑：
   - remote run
   - finalize
   - compare
3. 暂时不要急着基于 3 个 CVE 做强抽象归类
