# AGENT HANDOFF GPT -> GLM (2026-08-09, Supplement 02)

> 生成时间：2026-08-09（周日，Asia/Shanghai）
> 目的：补充并纠正上一份 handoff，重点澄清“实验反馈是否真的改变了 skill”以及“当前工程和实验的真实状态”。
> 范围：仅归档本次会话中**重新核对过**的内容；不继续实施新的工程修改。

---

## 1. 这份补充交接要解决什么误解

上一轮 handoff 之后，GLM 对当前工程和实验状态仍有理解偏差。最关键的偏差点是：

1. 容易把“**已经产生反馈数据**”误解成“**skill 已经被演化并正式生效**”
2. 容易把“**有 candidate skill / validation job / gate decision**”误解成“**live skill 已经更新**”
3. 容易把“**已有实验结果**”误解成“**已经证明 skill 的必要性**”

本文件的目标，就是把这三件事拆开说清楚。

---

## 2. 本次会话核实后的核心结论

### 2.1 关于“测试实验有没有对 skill 形成反馈和改变”

最准确的结论是：

**有形成反馈，但目前没有足够证据说明这些反馈已经稳定转化为 live skill 的正式改动。**

请拆成两层理解：

#### A. 反馈链已经存在

- 实验结果会被整理成 feedback bundle：
  - [reports/current/skill_feedback_bundle.json](/D:/Code/SkillClaw/SkillClaw/reports/current/skill_feedback_bundle.json)
- `evaluation/evolution.py:345` 的 `handoff_validated_run(...)` 已经承担“验证后交接”的入口
- `evolve_server/engines/workflow.py:104` 的 `_load_feedback_bundle(...)` 会读取反馈包
- `evolve_server/engines/workflow.py:791` 附近会把 skill 修改动作记为 `queued_for_validation`

这说明：**实验 -> 反馈包 -> evolve 候选动作** 这段链路是存在的。

#### B. 但“正式生效修改”目前基本没有被证实

本次会话核对到的硬证据是：

- [reports/current/briefing_20260805/closed_loop_proof.csv](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260805/closed_loop_proof.csv)
  - 第 6 行 `firmware2-wireless-relevant-20260806a`
  - 第 12 行 `giflib-paper-20260801a`
  - 这些记录里都能看到：
    - `candidate_count > 0`
    - `candidates_queued > 0`
    - 但 `uploaded_count = 0`
    - 且 `published_after_validation = 0`

- [runtime/evolve/evolve_history.jsonl](/D:/Code/SkillClaw/SkillClaw/runtime/evolve/evolve_history.jsonl)
  - `2026-08-09T08:49:01Z` 这一轮：
    - `sessions = 1`
    - `actions = 2`
    - `candidates_queued = 2`
    - `published_after_validation = 0`
  - `2026-08-09T08:49:52Z` 这一轮：
    - 明确记录两个动作都变成了 `validation_rejected`
    - `published_after_validation = 0`

- 对应 gate 决策文件：
  - [skillspace/share/default/gate_decisions/20260809084901-elf-cwe120-plt-analysis-43927faa.json](/D:/Code/SkillClaw/SkillClaw/skillspace/share/default/gate_decisions/20260809084901-elf-cwe120-plt-analysis-43927faa.json)
  - 状态是：
    - `"status": "rejected"`
    - `"reason": "client validation rejected candidate"`

- 候选 skill 确实被生成了：
  - [skillspace/share/default/candidate_skills/20260809084901-elf-cwe120-plt-analysis-43927faa/SKILL.md](/D:/Code/SkillClaw/SkillClaw/skillspace/share/default/candidate_skills/20260809084901-elf-cwe120-plt-analysis-43927faa/SKILL.md)

但这不等于 live skill 已被替换。

#### C. 当前最稳妥的总判断

当前工程已经做到：

**实验 -> 反馈 -> 候选修改 -> 验证判定**

但还没有稳定做到：

**验证通过 -> 自动发布 -> live skill 生效 -> 下轮实验直接使用新 skill**

换句话说：

**反馈闭环“前半段”存在；演化真正落地到 live 的“后半段”尚未被这次会话验证成功。**

---

### 2.2 关于“当前是否已经证明了 skill 的必要性”

结论：

**还没有。**

目前已有实验说明的是：

- 不同 skill 配置会影响 blind 分析结果
- 某些 skill 会明显误选
- 某些 skill 内容更适合当前任务

但这还不是严格意义上的：

**“使用这个 skill 就能找到漏洞，不使用它或换错 skill 就找不到”**

也就是说，目前已有的是：

- **影响性证据**

还不是：

- **必要性证据**

后续如果要证明必要性，实验设计必须更严格：

1. 固定 case、模型、提示模板、环境、可用工具
2. 只控制 skill 变量
3. 至少比较：
   - no-skill
   - target-skill
   - wrong-skill
   - degraded-skill / ablated-skill
4. 用同一评分口径反复跑，并保留原始记录

---

### 2.3 关于“当前 live skill 长度和结构是否失衡”

本次会话对 `skillspace/live/*/SKILL.md` 做了长度审计。

范围：

- 只审计当前启用目录：`skillspace/live`
- 不包含：
  - `skillspace/share/default/skills` 的历史版本
  - `skillspace/share/default/candidate_skills` 的候选版本

审计结果：

- Skill 总数：`35`
- 总行数：`1400`
- 平均行数：`40`
- 中位行数：`34`
- 最短：`10` 行
- 最长：`154` 行
- 平均字符数：`2680`
- 中位字符数：`2358`
- 字符范围：`1160 ~ 7830`

代表性偏长 skill：

- [skillspace/live/source-parser-state-machine-oob/SKILL.md](/D:/Code/SkillClaw/SkillClaw/skillspace/live/source-parser-state-machine-oob/SKILL.md)
  - `154` 行，`7830` 字符
- [skillspace/live/cisco-vmanage-firmware-analysis/SKILL.md](/D:/Code/SkillClaw/SkillClaw/skillspace/live/cisco-vmanage-firmware-analysis/SKILL.md)
  - `100` 行，`5133` 字符

代表性偏短 skill：

- [skillspace/live/skillclaw-skill-discovery/SKILL.md](/D:/Code/SkillClaw/SkillClaw/skillspace/live/skillclaw-skill-discovery/SKILL.md)
  - `10` 行，`1160` 字符
- [skillspace/live/embedded-cgi-command-injection-triage/SKILL.md](/D:/Code/SkillClaw/SkillClaw/skillspace/live/embedded-cgi-command-injection-triage/SKILL.md)
  - `10` 行，`1451` 字符

这说明当前 live skill 在“信息密度和边界表达”上差异很大，后续很可能需要：

1. 压缩过长 skill
2. 补强过短 skill
3. 统一触发条件 / 排除条件 / 核心步骤的组织方式

---

## 3. 本次会话实际运行的命令与结果

### 3.1 读取现有 handoff 和工作区状态

- `Get-ChildItem -Name AGENT_HANDOFF*`
  - 结果：
    - `AGENT_HANDOFF.md`
    - `AGENT_HANDOFF_GPT_TO_GLM_20260809.md`

- `Get-Content AGENT_HANDOFF_GPT_TO_GLM_20260809.md -First 220`
  - 结果：
    - 控制台显示有明显乱码，说明这份文件至少在当前控制台读取链路里不适合作为唯一权威交接材料

- `git status --short`
  - 结果：
    - 工作区仍然是明显 dirty 状态
    - 本次会话未尝试清理或提交这些改动

### 3.2 核对 feedback / evolve / candidate / gate

- `Get-Content reports\\current\\skill_feedback_bundle.json -First 220`
  - 结果：
    - 反馈包存在
    - 至少包含 `elf-cwe120-plt-analysis` 等 skill 的 gate 信息和 case 摘要

- `Get-Content runtime\\evolve\\evolve_history.jsonl -Tail 40`
  - 结果：
    - 看到近期多次 evolve 周期
    - 关键记录表明：
      - 有候选被排入验证
      - 有验证拒绝
      - `published_after_validation` 仍为 `0`

- `Get-Content skillspace\\share\\default\\gate_decisions\\20260809084901-elf-cwe120-plt-analysis-43927faa.json -First 220`
  - 结果：
    - 明确为 rejected

- `Get-ChildItem skillspace\\share\\default\\candidate_skills | Sort-Object LastWriteTime -Descending | Select-Object -First 10 ...`
  - 结果：
    - 最近候选 skill 目录确实存在

### 3.3 审计 live skill 长度

- 对 `skillspace/live/*/SKILL.md` 执行行数、字符数、字节数统计
  - 结果：
    - 共 `35` 个 skill
    - 平均 `40` 行
    - 最长 `154` 行
    - 最短 `10` 行

---

## 4. 本次会话未做的事

为了避免再把状态说得比实际更“完成”，这里明确列出本次会话**没有做**的事：

1. **没有修改任何业务代码**
   - 除本 handoff 文件外，本次会话没有实施新的工程改动

2. **没有重新跑新的 case**
   - 本次会话只做状态核对，不新增实验执行

3. **没有证明 live skill 已经被自动演化更新**
   - 目前看到的是 candidate、gate、rejected
   - 不是 accepted + published + live replaced

4. **没有证明 skill 必要性**
   - 目前最多只能说“skill 会影响结果”

---

## 5. GLM 接手时最应该先核验什么

优先级从高到低：

### P0. 先核验“是否真的有 skill 已经发布到 live”

重点不要再混淆这三层：

1. `reports/current/skill_feedback_bundle.json`
   - 这是反馈包，不是 live skill
2. `skillspace/share/default/candidate_skills/...`
   - 这是候选 skill，不是 live skill
3. `skillspace/live/.../SKILL.md`
   - 这才是当前注入时真正会被使用的 skill

只要没有拿到“accepted + published_after_validation > 0 + live 文件确实变化”的连续证据，就不要写成“skill 已演化成功”。

### P1. 先核验 candidate -> validation -> publish 这条链为什么大多停在 rejected

本次会话已经看到：

- rejected 决策文件存在
- evolve history 里也有 `validation_rejected`

下一步应该明确：

1. 拒绝规则是什么
2. 拒绝发生在哪一层
3. 是否是评分 / gate / artifact / 命名边界导致的

### P2. 如果要继续写论文或汇报，描述必须守住这个边界

目前可以说：

- 已打通实验反馈到候选 skill 修改的链路
- 已形成 candidate + validation + gate 的工程闭环雏形

目前不能说：

- 已经稳定完成 skill 自动进化
- 已经证明某 skill 对某漏洞分析是必要条件

---

## 6. 本次新增归档文件

- [AGENT_HANDOFF_GPT_TO_GLM_20260809_02.md](/D:/Code/SkillClaw/SkillClaw/AGENT_HANDOFF_GPT_TO_GLM_20260809_02.md)

---

## 7. 一句话给 GLM

**请先把“反馈存在”和“演化生效”彻底分开，再继续判断当前工程成熟度；当前证据支持前者，不足以宣称后者已经稳定成立。**
