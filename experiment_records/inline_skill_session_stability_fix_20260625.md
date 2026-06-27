# Inline Skill Session Stability Fix - 2026-06-25

## 背景

在远端 VM 使用 `Claude Code + SkillClaw key` 进行漏洞定位实验时，SkillClaw 的 inline 注入会在每个 main turn 重新检索 skill。实际实验中出现过首轮选中 `source-parser-state-machine-oob`、`elf-cwe120-firmware-triage` 等领域 skill，但后续 tool 回合因为上下文中出现 `SkillClaw`、`server-side skills`、`ssh` 等词，检索结果漂移到 `skillclaw-skill-discovery`、`ssh-password-recon-workflow` 等无关 skill。

这会导致两个问题：

1. 实验结果难以解释，因为同一会话内 skill 条件不稳定。
2. SkillClaw 组可能因为注入漂移而弱于 DeepSeek 直连组，无法判断是 skill 内容无效，还是检索/注入机制干扰了任务。

## 修改内容

本次修改在 `skillclaw/api_server.py` 中增加 session-stable inline skill cache：

1. `_handle_openclaw_request()` 将 `session_id` 传入 `_inject_skills()`。
2. `_inject_skills()` 在 inline/server-inline 模式下，对同一 `session_id` 的首次任务型 skill 选择进行固定。
3. 后续 main turn 若 skill 集合版本未变化，则复用首次选中的 skill 正文，不再根据 tool 输出重新检索。
4. 如果首次请求是 SkillClaw 元任务，例如查询 skill catalog/count，只选中 `skillclaw-*` 元 skill，则不固定会话，避免污染后续真正漏洞任务。
5. 会话关闭时清理 `_session_inline_skill_cache`。

新增注入元数据字段：

```json
{
  "stable_session": true,
  "stable_action": "pin|reuse|none",
  "stable_generation": 0
}
```

其中 `pin` 表示本轮首次固定，`reuse` 表示复用缓存，`none` 表示未固定。

## 测试

新增 `tests/test_inline_skill_session_cache.py`：

1. `test_inline_skill_selection_is_pinned_within_session`
   - 首轮漏洞任务选中 `source-parser-state-machine-oob`、`vuln-hunting`。
   - 第二轮上下文包含 `ssh` 等干扰词。
   - 期望第二轮仍复用首轮 skill，且 `stable_action=reuse`。

2. `test_inline_skill_meta_tasks_do_not_pin_session`
   - 首轮只查询 SkillClaw skill catalog/count。
   - 期望不固定 `skillclaw-skill-discovery`。
   - 第二轮漏洞任务仍能正常选择领域 skill。

已通过测试：

```text
python -m pytest tests/test_inline_skill_session_cache.py tests/test_experiment_scripts.py
22 passed

python -m pytest tests/test_responses_native.py tests/test_session_upload_trigger.py tests/test_inline_skill_session_cache.py
24 passed
```

## Remote Smoke Test

重启主机 SkillClaw proxy 后，从远端 VM 的 `tmux` 会话中使用 `curl` 连续发送两次 `/v1/messages` 请求，二者使用同一个 `x-session-id`：

1. 第一轮：tcpdump parser state machine OOB 漏洞任务。
2. 第二轮：继续同一 tcpdump 任务，但故意加入 `ssh password recon` 干扰词。

服务端日志显示：

```text
[SkillManager] inlining 3 skill(s) stable=pin:
source-parser-state-machine-oob, elf-cwe120-firmware-triage, verify-rootfs-full-enumeration

[SkillManager] inlining 3 skill(s) stable=reuse:
source-parser-state-machine-oob, elf-cwe120-firmware-triage, verify-rootfs-full-enumeration
```

结论：同一 session 内后续 turn 已经复用首次任务型 skill 集合，没有因为第二轮的 `ssh` 干扰词漂移到 `ssh-password-recon-workflow` 或 `skillclaw-*` 元技能。

## Real Claude Code Probe

随后在远端 VM 的真实 Claude Code `-p` 模式中运行一次短版 tcpdump probe。该 probe 使用 SkillClaw key，实际触发多轮 Claude Code 工具调用。由于 Windows SSH 注入中文 prompt 时远端显示为 `???`，本次不作为正式 A/B 对照实验，只作为真实链路验证与问题观察。

真实会话日志显示：

```text
[SkillManager] inlining 3 skill(s) stable=pin:
source-parser-state-machine-oob, cwe120-analysis-verification, elf-cwe120-firmware-triage

[SkillManager] inlining 3 skill(s) stable=reuse:
source-parser-state-machine-oob, cwe120-analysis-verification, elf-cwe120-firmware-triage
```

后续多个 tool turn 均保持 `stable=reuse`，说明真实 Claude Code 多轮工具调用中也没有发生 skill 漂移。

远端生成文件：

```text
/home/li/skillclaw-eval/tcpdump-4.9.1/frag6-oob-read.json
```

本地归档文件：

```text
experiment_records/tcpdump-skillclaw-stable-probe-frag6-oob-read-20260625.json
experiment_records/tcpdump_skillclaw_stable_probe_scores_20260625.jsonl
```

评分结果：

```text
case: tcpdump-4.9.1-cve-2017-13031
mode: skillclaw-inline-stable-probe
session: be313205-1c21-4efc-affb-b6e19a460c3a
score: 8/10
file: hit, print-frag6.c
function: hit, frag6_print
evidence: hit, ND_TCHECK / ip6f_offlg / ip6f_ident
root cause: hit
CVE: miss, predicted CVE-2017-12986 instead of CVE-2017-13031
```

观察：

1. Session-stable 注入在真实 Claude Code 链路中生效。
2. SkillClaw 组能够定位到正确文件、函数和关键边界检查缺陷。
3. CVE 映射仍不稳定，说明“漏洞位置定位”和“CVE 命名”需要分开评分。
4. Agent 没有严格遵守“最多 6 个工具调用”和“只输出 JSON”的约束，后续应加强输出 schema 和 runner 层约束。
5. Windows 到 Linux 的 tmux 注入需要避免中文，正式实验应使用 ASCII prompt 或 base64/文件传输方式写入 prompt。

为解决第 5 点，新增：

```text
experiment_scripts/send_remote_tmux.ps1
```

该脚本将命令块按 UTF-8 base64 传输到远端，再解码并粘贴到指定 `tmux` 会话。已用中文 echo 验证，不再出现 `???` 编码损坏。

## 对实验的意义

该修改不是证明 SkillClaw skill 一定有效，而是先消除一个关键混杂变量：同一会话内 skill 注入条件漂移。后续对照实验中，可以把 SkillClaw 组拆成：

1. SkillClaw inline + session-stable skill。
2. DeepSeek 直连 baseline。
3. 可选：SkillClaw inline 但关闭稳定缓存，用于消融检索漂移的影响。

这样才能更清楚地区分三类问题：

1. skill 本身质量不足。
2. skill 检索/注入机制不稳定。
3. LLM 执行复杂任务时即使读到 skill 也可能偷懒或偏离。

## 剩余风险

当前策略按 session 固定 skill，适合“一次会话只分析一个目标”的实验设置。如果用户在同一 Claude Code 会话中明显切换任务，后续可增加显式重选机制，例如用户输入 `reset skill context` 或检测到目标项目/CVE 变化后清空缓存。
