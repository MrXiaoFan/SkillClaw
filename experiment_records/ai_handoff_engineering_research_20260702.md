# SkillClaw 工程与研究交接说明（2026-07-02）

## 1. 当前工程目标

当前工程的核心目标不是单纯改进 SkillClaw 的检索或注入效果，而是把它扩展成一个可用于漏洞分析实验的闭环框架：

```text
case 定义
-> agent 执行
-> score / validator
-> final record
-> skill injection audit
-> compare / feedback / revision
```

在此基础上，当前重点逐步从“漏洞定位”转向“漏洞确认”：

- 前半段：定位漏洞文件、函数、根因、证据、CVE
- 后半段：生成 artifact / PoC / trigger input，执行并验证行为或崩溃

## 2. 目前已经完成的工程能力

### 2.1 实验框架

目录与职责：

- `experiment_cases/`
  - benchmark case、schema、PoC 生成脚本
- `experiment_scripts/`
  - `run_eval_case.py`
  - `run_dynamic_case.py`
  - `build_result_record.py`
  - `attach_skill_injection.py`
  - `finalize_experiment_record.py`
  - `compare_experiment_records.py`
- `experiment_validation/`
  - validator registry 和多种验证模式

### 2.2 已支持的 validator

- `content_match`
- `source_contains`
- `command`
- `bundle_script`
- `artifact_exists`
- `artifact_exec`
- `asan_command`

### 2.3 实验后处理链

当前远端结果已经可以按固定流程回收到本地：

```text
remote run
-> pull final.json
-> finalize_experiment_record.py
-> final-with-injection.json
-> compare_experiment_records.py
```

这意味着：

- 不再依赖手工拼 skill injection 审计
- 不再依赖手工比较 before/after JSON

### 2.4 SkillClaw 本体侧的关键修改

主要是围绕“server-side inline skill 注入的任务相关性”做了增强：

- 过滤 `skillclaw-*` 自省类 skill 在漏洞任务中的误注入
- 对 source parser / OOB / header 类任务提高 `source-parser-state-machine-oob` 优先级
- 在 inline prompt 中显式声明：
  - 这些 skills 已经作为文本注入
  - 不要调用本地 `Skill(...)`

## 3. 当前案例状态

### 3.1 giflib-5.1.2 / CVE-2016-3977

状态：**crash-backed confirmation case**

已经跑通：

- agent 生成 artifact
- `artifact_exists`
- `artifact_exec`
- `asan_command`
- final record
- injection audit
- compare

当前它是最完整的“PoC / trigger / sanitizer 确认”案例。

### 3.2 tcpdump-4.9.1 / CVE-2017-13031

状态：**behavior-backed confirmation case**

已经跑通：

- SkillClaw confirmation
- direct-deepseek confirmation
- `artifact_exists`
- `artifact_exec`
- 行为 marker 确认（`Fragment (44)` / `[|frag]`）
- compare

注意：

- 它目前是“行为确认”，不是“ASan 崩溃确认”
- 但已经不是纯定位 case

### 3.3 libxml2-2.9.4 / CVE-2017-8872

状态：**revision-study case**

已经跑通：

- 漏洞定位 / 证据 / validator
- `cve_calibration_miss`
- feedback bundle
- template-driven skill revision
- rerun
- compare

关键结果：

- 从“定位对但 CVE 错”提升到 `10/10`
- 说明 revision loop 已经有工程和实验价值

注意：

- 它目前还没有稳定走通 crash-backed confirmation
- 因此不要把它误描述为 confirmation case

## 4. 这阶段最重要的工程修改说明

### A. confirmation schema 扩展

给 case 增加了：

- `expected_artifacts`
- `repro.build`
- `repro.run`
- `success_markers`
- `target_frames`

目的：

- 让 case 不只定义“找漏洞”
- 还定义“如何生成和验证确认产物”

### B. artifact validator

新增：

- `artifact_exists`
- `artifact_exec`

目的：

- 检查 agent 是否真的生成了可运行 PoC / trigger
- 把“漏洞确认”从文本判断推进到实际执行

### C. runner / finalize / compare 链打通

新增或增强：

- `run_eval_case.py`：支持更稳的 session linkage
- `finalize_experiment_record.py`：本地自动补 injection 并可直接 compare
- `compare_experiment_records.py`：自动输出 before/after 差异

### D. prompt contract 强化

对 confirmation 类 case，prompt 现在会明确要求：

- 生成 artifact
- 保留 wrapper / repro 脚本
- 透传 crash / exit code

这解决了前面 “脚本自己返回 0，吃掉底层 crash” 的问题。

## 5. 当前研究目标

当前研究目标不应表述为：

- “SkillClaw 一定优于 direct baseline”

更准确的主线是：

### 5.1 研究目标

在漏洞分析任务中，构建一个：

- **validator-grounded**
- **dimension-aware**
- **auditable**

的 skill evolution / confirmation framework。

### 5.2 当前最稳的研究问题

1. 如何让漏洞分析不只停留在定位，而能延伸到确认？
2. 如何用 validator 而不是会话摘要判断 skill 是否真正有效？
3. 如何区分：
   - localization 能力
   - CVE calibration 能力
   - artifact / confirmation 能力
4. 如何把这些结果反过来用于 skill revision？

## 6. 当前最稳的研究结论

### 6.1 SkillClaw 的收益不是绝对的

它并不稳定强于 direct baseline。

更稳的结论是：

- 在某些 case 中，SkillClaw 和 direct 都能做对
- 在某些 case 中，SkillClaw 的优势更多来自匹配 skill
- 在某些 case 中，skill mismatch 会把模型带偏

### 6.2 漏洞分析必须拆维度评估

已经明确出现过的现象：

- 文件/函数定位正确
- 根因解释正确
- 但 CVE 错误

所以必须拆成：

- localization
- evidence
- root cause
- CVE calibration
- artifact generation / confirmation

### 6.3 当前 confirmation loop 已可行，但远未“完成”

现在最多只能说：

- 闭环原型已经做出来了
- `giflib` 跑通了 crash-backed confirmation
- `tcpdump` 跑通了 behavior-backed confirmation
- `libxml2` 跑通了 revision-study loop

但不能说：

- 动态验证闭环已经充分完成
- 或已经具备广泛泛化能力

## 7. 当前最现实的短板

### 7.1 case 数量仍然偏少

目前真正成型的主案例只有：

- `giflib`
- `tcpdump`
- `libxml2`

这不足以支撑强泛化结论。

### 7.2 confirmation 覆盖还不够

目前只有：

- 1 个 crash-backed confirmation case（giflib）
- 1 个 behavior-backed confirmation case（tcpdump）

还需要继续补新的 confirmation case。

### 7.3 case 仍存在较强的 CVE-specific 开发痕迹

当前很多 artifact / marker / harness 仍然是为特定历史 CVE 手工构造的。

这不是现在立刻要抽象成 taxonomy 的时候，但后面必须继续扩 case，避免系统只在少量定制样本上成立。

## 8. 近期工程优先级建议

### 第一优先级：继续补 confirmation case

目标不是马上抽象归类，而是先把 confirmation coverage 扩起来。

建议：

1. 再找 1 个 **crash-backed** confirmation case
2. 跑通：
   - SkillClaw
   - direct baseline
   - artifact / validator / compare

### 第二优先级：保持这三个 case 的链路稳定

对现有三条线，确保：

- 远端 run
- 本地 finalize
- compare

都能按同一流程稳定执行。

### 第三优先级：等样本更多后，再考虑抽象

目前不建议急着基于 3 个 CVE 做强归类。

更合适的节奏是：

- 先把 confirmation case 从 2 条扩到 3-4 条
- 再回头看是否真的存在稳定的“漏洞族模板”

## 9. 建议给 AI 继续思考时的提示词方向

如果你接下来想把这份工程交给别的 AI 辅助思考论文，可以让它围绕下面几个问题：

1. 当前系统更适合被表述为：
   - skill evolution framework
   - vulnerability confirmation framework
   - 还是两者结合？
2. 现有三条 case 里，哪些结果足以形成方法 claim，哪些只能算 feasibility evidence？
3. 在 confirmation case 数量还少时，如何诚实但有说服力地组织实验章节？
4. 如何区分：
   - 通用框架贡献
   - CVE-specific harness 贡献
5. 接下来新增 case 时，应该优先补什么类型的目标，才能最快提升说服力？

## 10. 当前一句话总结

当前工程最准确的定位是：

> 一个基于 SkillClaw 扩展出来的、面向漏洞定位与漏洞确认任务的实验闭环原型；它已经在 `giflib`、`tcpdump`、`libxml2` 三条线上证明了可行性，但仍处于小样本扩展阶段，下一步重点应是继续补 confirmation case，而不是过早抽象归类。
