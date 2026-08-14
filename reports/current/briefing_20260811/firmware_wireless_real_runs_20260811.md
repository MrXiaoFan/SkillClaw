# Firmware Wireless 真实远端实验记录

整理时间：2026-08-12

## 1. 实验目标

这组实验只回答三个具体问题：

1. `SkillClaw -> Evolve -> replay gate` 是否已经能在远端 VM 的 blind firmware case 上真实闭环。
2. 闭环跑通后，错误 skill、弱 skill、无 skill、当前 live skill 四种条件下分别会发生什么。
3. 当前证据是否已经足够证明“skill 确实带来了可发布的正向提升”。

## 2. 固定条件

- 案例：`benchmarks/cases/firmware2-wireless-cgi-cve-2026-2529.json`
- 研究对象：固件 Web CGI 命令注入分析任务，目标是让模型从固件中的 `.cgi` 二进制和关联前端页面里定位一条真实的 HTTP 参数到命令执行路径
- 远端 VM：`li@192.168.1.4`
- 运行模式：`blind-skillclaw-inline-guarded`
- 远端模型：VM 上的 Claude
- skill 注入方式：SkillClaw 服务端先用代码规则从当前可用 skill 里选出本轮可见 skill，再以内联文本方式注入到上游模型提示词
- 结果打分：本地评分程序读取远端产出的最终 JSON，按文件、函数、根因、证据等字段进行文本评分
- 动态反馈：`finalize_record` 会把本轮会话结果整理成反馈记录，再交给 Evolve 判断是否生成 candidate skill，并由 replay gate 决定是否允许发布

## 3. 实验思路

本轮做的是四路对照，保持这些条件不变：

- 同一个 case
- 同一个远端 VM
- 同一个模型入口
- 同一条 `SkillClaw -> Evolve -> replay gate` 工程链路

只控制一个变量：

- 本轮强制给模型看到什么 skill

四组分别是：

| 组别 | run_id | 强制 skill |
| --- | --- | --- |
| 无 skill 组 | `firmware2-wireless-none-20260812c` | 无 |
| 弱 skill 组 | `firmware2-wireless-seed-20260812a` | `embedded-cgi-command-injection-triage` 的 seed 版本 |
| 错误 skill 组 | `firmware2-wireless-wrong-20260812h` | `firmware-embedded-lua-shell-extraction` |
| 当前 live skill 组 | `firmware2-wireless-live-20260812i` | 当前 live 的 `embedded-cgi-command-injection-triage` |

## 4. 关键差异

### 4.1 无 skill 组

- 不给任何 skill
- 作用：作为纯基础能力对照

### 4.2 弱 skill 组

- 给一个更短、更像“分发到分支再追 sink”的 seed 版 skill
- 重点提示模型：
  - 先找 dispatcher 变量
  - 再找同一分支里的参数提取
  - 再找同一分支里的命令构造和执行

### 4.3 错误 skill 组

- 给的是另一个固件域 skill：`firmware-embedded-lua-shell-extraction`
- 它更偏向 Lua/脚本提取，不是这类 CGI 命令注入主路径
- 作用：作为“错域 skill”对照

### 4.4 当前 live skill 组

- 给当前实际 live 的 `embedded-cgi-command-injection-triage`
- 它比 seed 版更长，覆盖面更大，也更强调：
  - 先枚举 CGI 入口
  - 看前端表单
  - 看 ELF 二进制里的 sink 和参数来源

## 5. 实验结果

| 组别 | score | selected_skill_names | skill_relevance | Evolve 结果 |
| --- | ---: | --- | --- | --- |
| 无 skill 组 | 2.0 | `[]` | `no_selected_skills` | 已 handoff，已 consumed，未生成 candidate |
| 弱 skill 组 | 3.0 | `embedded-cgi-command-injection-triage` | `has_task_relevant_skill` | 已 handoff，已 consumed，生成 1 个 candidate，replay gate 拒绝 |
| 错误 skill 组 | 2.0 | `firmware-embedded-lua-shell-extraction` | `no_task_relevant_skill` | 已 handoff，已 consumed，生成 1 个 candidate，replay gate 拒绝 |
| 当前 live skill 组 | 3.0 | `embedded-cgi-command-injection-triage` | `has_task_relevant_skill` | 已 handoff，已 consumed，未生成 candidate |

## 6. 当前结论

### 6.1 已经能确认的

1. 这条工程链路已经真实闭环：
   - 远端 VM 上的 Claude 通过本机 SkillClaw 代理发请求
   - SkillClaw 在本地记录会话、skill 选择和最终回答
   - 本地后处理生成 `final-enriched.json`
   - Evolve 能消费该反馈
   - replay gate 能对 candidate 做最终放行或拒绝

2. 当前 gate 也已经在真正起作用：
   - 不是“只要生成 candidate 就发布”
   - 而是“candidate 必须优于 baseline 才发布”

3. `selected_skill_names`、`skill_relevance`、`feedback`、`evolution_handoff` 这几类关键字段，在这四组 run 里都已经能正确落到最终记录里

### 6.2 还不能确认的

1. 还不能证明“用了正确 skill 才能找到这个漏洞”
2. 还不能证明“错误 skill 或无 skill 一定找不到”
3. 还不能证明“Evolve 已经把某个 skill 真正改好并发布到 live skill 区，再让下一轮分析变好”

换句话说：

- 工程闭环是真的
- skill 增益证据还不够

## 7. 证据文件

### 四个核心 run

- `runtime/imports/remote_vm/firmware2-wireless-none-20260812c/firmware2-wireless-none-20260812c-final-enriched.json`
- `runtime/imports/remote_vm/firmware2-wireless-seed-20260812a/firmware2-wireless-seed-20260812a-final-enriched.json`
- `runtime/imports/remote_vm/firmware2-wireless-wrong-20260812h/firmware2-wireless-wrong-20260812h-final-enriched.json`
- `runtime/imports/remote_vm/firmware2-wireless-live-20260812i/firmware2-wireless-live-20260812i-final-enriched.json`

### replay gate 证据

- 弱 skill 组：
  - `skillspace/share/default/gate_decisions/20260812045011-embedded-cgi-command-injection-triage-7c320ce2.json`
  - `skillspace/share/default/gate_results/20260812045011-embedded-cgi-command-injection-triage-7c320ce2/Fan.json`
- 错误 skill 组：
  - `skillspace/share/default/gate_decisions/20260812055115-firmware-embedded-lua-shell-extraction-213c18d3.json`
  - `skillspace/share/default/gate_results/20260812055115-firmware-embedded-lua-shell-extraction-213c18d3/Fan.json`

### 远端执行记录

- `runtime/logs/remote_vm_commands.log`

## 8. 下一步最合理的方向

1. 不再把“生成了 candidate”当成正向结果，而是只看：
   - 是否真正发布到 live skill 区
   - 发布后下一轮是否变好
2. 先减少 skill 候选干扰，必要时用空 skill / 极弱 skill 做更干净的演化对照
3. 在不继续膨胀脚本的前提下，把这四组真实对照作为当前 firmware 方向的标准证据集
