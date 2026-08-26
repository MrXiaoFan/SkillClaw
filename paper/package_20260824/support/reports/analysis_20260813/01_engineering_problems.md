# SkillClaw 工程问题分析报告

> 日期：2026-08-13
> 范围：D:\Code\SkillClaw\SkillClaw 全工程
> 方法：代码审查 + 运行时数据核验 + 实验记录回溯

---

## 一、总体判断

工程链路（远端 VM blind run → SkillClaw 服务端 skill 选择/注入 → 模型分析 → 本地评分/后处理 → Evolve 消费 → replay gate 判定）**已经真实闭环**，但闭环中存在多个**阻断 skill 进化的结构性缺陷**。当前没有任何一次 candidate skill 被证明优于 baseline 并成功带来可复用的正向效果。

---

## 二、核心问题（按严重程度排序）

### P0-1：Replay Gate 设计缺陷 —— skill 进化的根本瓶颈

**问题位置**：`skillclaw/replay_gate_worker.py`

**根本矛盾**：replay gate 试图用"无工具文本回复 + PRM 评分"来衡量 skill 的价值，但这个设计在逻辑上无法产生 candidate > baseline 的差异。

**具体机制**：
1. `_build_replay_messages` 为 baseline 和 candidate 两个分支构造几乎相同的消息：
   - 两者都收到相同的 `original_evidence`（从原始 run 的 reference_response 中提取的 evidence 文本）
   - 两者都被要求"基于相同证据推导结论，不调用工具"
   - 唯一差异是 candidate 的 system prompt 中注入了 skill 文本
2. 由于 evidence 已经包含了关键发现（如 `CONTENT_LENGTH`、`fgets(v4, n2, stdin)`、`system(byte_41BC84)` 等），baseline 和 candidate 都能从这些证据直接推导出正确结论
3. PRM 评分只有 +1/-1/0 三档，分辨率极低
4. `_accept_replay_candidate` 要求 `candidate_mean > baseline_mean`（严格大于），但在上述条件下两者产出几乎相同的回答，分数必然相等

**数据佐证**（57 条 gate_decisions）：

| 状态 | mean_score | 数量 | 说明 |
|------|-----------|------|------|
| published | 1.0 | 7 | 早期（08-11）发布，当时可能还没有 strict_improvement |
| published | 0.833 | 1 | 唯一一个 candidate 略高于 baseline 的 |
| rejected | 0.0 | 28 | candidate 和 baseline 都答不好 |
| rejected | 1.0 | 19 | candidate 和 baseline 都答"好"但分数相同，不满足 strict_improvement |
| rejected | 0.5 | 1 | — |
| rejected | 0.667 | 1 | — |

19 条 rejected|1.0 是最典型的失败模式：candidate 和 baseline 都拿到了满分，但因为相等而被拒绝。这不是 candidate 不好，而是**评判机制无法区分**。

**结论**：当前 replay gate 的设计使得 candidate 几乎不可能通过，除非 PRM 恰好给出不同的投票分布。这不是"candidate 质量不够"的问题，而是"尺子本身量不出差异"。

---

### P0-2：No-Skill 实验反馈断链 —— create_skill 无法基于反馈生成有效 skill

**问题位置**：`evolve_server/engines/workflow.py` + `evolve_server/pipeline/execution.py`

**四个断点**（已确认）：

1. **`build_feedback_bundle.py`**：当 `selected_skill_names` 为空时，`if not selected: continue` 直接跳过，no-skill 实验的反馈不会被构建
2. **`workflow.py:_paired_feedback_map`**：no-skill session 的 feedback 不进入 `feedback_by_skill` 字典
3. **`workflow.py:_handle_no_skill_sessions`**：调用 `create_skill_from_sessions(self._llm, sessions, existing_skill_names)` —— **不传 feedback_context 参数**
4. **`execution.py:create_skill_from_sessions`**：函数签名只有 `(llm, sessions, existing_skill_names)`，user_msg 只包含 session evidence + existing skill names，**完全没有 feedback section**

**对比**：`evolve_skill_from_sessions` 函数正确接收并使用 `feedback_context`，通过 `_build_feedback_context()` 构建反馈段落注入到 prompt 中。

**影响**：即使 no-skill 实验发现了"模型在没有 skill 时表现差"这一信号，这个信号也无法传递到 create_skill 的 LLM 调用中。create_skill 只能看到 session 摘要，看不到"这个 session 失败了，失败原因是缺少 X 知识"的反馈。

**状态**：已设计改动方案（约 50 行，不新增文件），用户要求暂记为 TODO。

---

### P1-1：评分体系分辨率不足

**问题位置**：`evaluation/scoring/score_case_output.py` + `skillclaw/prm_scorer.py`

**两层评分都有分辨率问题**：

**实验评分**（score_case_output.py）：
- 满分 10 分，5 个维度（cve/file/function/evidence/root_cause），每维 2 分
- 但匹配方式是**纯关键词/子串匹配**：只要 agent 的回答中包含 ground truth 中的字符串就算 hit
- 四组核心实验的分数：none=2.0, seed=2.0, wrong=2.0, live=3.0
- none（无 skill）和 seed（有正确 skill）分数相同，说明评分无法区分 skill 的作用
- 甚至 wrong skill 和 no skill 分数也相同

**PRM 评分**（prm_scorer.py）：
- 只有 +1（helpful）/ -1（unhelpful）/ 0（unclear）三档
- 虽然 `_run_replay_branch` 使用了 mean vote 来增加分辨率（如 [1,1,-1] → 0.667），但基础粒度仍然太粗
- 对于"回答基本正确但缺少关键细节"的情况，PRM 倾向于给 +1，无法区分"完美回答"和"勉强及格"

---

### P1-2：Live Skills 库冗余严重

**现状**：skillspace/live/ 下有 35 个 skill 目录

**与当前固件实验直接相关的 skill**（约 6 个）：
- `embedded-cgi-command-injection-triage`
- `firmware-embedded-lua-shell-extraction`
- `elf-cwe120-plt-analysis`
- `elf-cwe120-firmware-triage`
- `embedded-router-cgi-cmd-injection-exploitation`
- `source-parser-state-machine-oob`

**与当前实验无关的 skill**（约 29 个）：
- cisco 相关（4 个）：`cisco-iosxe-webui-*`, `cisco-wsma-*`, `cisco-vmanage-*`
- IDA/idalib 相关（8 个）：`ida-headless-*`, `idalib-*`
- SkillClaw 自省相关（5 个）：`skillclaw-claude-env`, `skillclaw-proxy-introspection`, `skillclaw-retrieval-optimization`, `skillclaw-skill-discovery`, `skillclaw-internal-mechanics-inspection`
- 其他通用/不相关（12 个）：`ssh-password-recon-workflow`, `windows-dotnet-cmd-injection-triage`, `webui-auth-bypass-discovery`, `vuln-hunting`, `vuln-hunting-claw` 等

**影响**：
- skill 选择时，35 个 skill 的 catalog 全部注入 system prompt，消耗大量 token
- embedding 检索时，不相关的 skill 可能干扰匹配
- 实验变量不干净：模型看到的 skill 列表包含大量噪声

---

### P1-3：实验样本量严重不足

**现状**：
- 四组核心对照实验（none/seed/wrong/live），每组只有一个 case（firmware2-wireless-cgi-cve-2026-2529）
- Z 盘案例库虽然有大量固件案例，但都是裸二进制，没有运行环境，只能做静态分析
- 累计只有约 10 组真实远端 VM 实验

**影响**：
- 无法做统计显著性检验
- 单 case 的分数差异可能来自随机性而非 skill 作用
- 无法证明 skill 的"可复用性"（同一 skill 在不同 case 上的效果一致性）

---

### P2-1：静态分析评分天花板

**问题**：Z 盘案例和当前 case 都只有二进制文件，没有固件运行环境

**影响**：
- ASAN 验证（`evaluation/confirmation/checks.py` 中有 `DEFAULT_SANITIZER_MARKERS`）无法真正执行
- 评分只能依赖文本匹配，无法验证漏洞是否真的可利用
- `confirmation.maturity` 字段标注为 "artifact"，`benchmark.publication_ready` 为 false
- 这意味着即使模型分析完全正确，也只能拿到"静态分析正确"的分，无法证明"动态可利用"

---

### P2-2：工程文件膨胀与数据治理问题

**现状**：
- 57 个 gate_decisions JSON 文件，其中大量是重复 skill 名的重复候选
- 35 个 live skill 目录，但只有约 6 个在用
- `git status` 显示 38 个已修改文件，工作区不干净
- `reports/current/` 下有多个汇总文件，部分内容重叠
- runtime/ 下有大量历史实验记录

**已完成的治理**：
- candidate skill content-hash 去重（`workflow.py:_queue_validation_job`，用 SHA-256 比对 skill 文本内容）
- runtime/tmp/ 重复 payload 已清理
- 旧 wireless run 已归档

**仍需治理**：
- live skill 库需要裁剪
- gate_decisions 历史文件需要归档或清理
- 工作区需要 commit 或 stash

---

### P2-3：配置与环境脆弱性

**现状**：
- VM IP（192.168.1.4）是局域网地址，宿主机 IP 可能变化
- VM 上的 `~/.claude/settings.json` 指向宿主机 SkillClaw 代理，每次实验前需手动核对
- config.yaml 中 API key 明文存储
- PRM 和 LLM 共用同一个 DeepSeek API endpoint 和 model

**影响**：
- 远端实验的可重复性依赖网络环境稳定性
- PRM 和 LLM 用同一个模型评分，可能存在系统性偏差

---

## 三、问题依赖关系

```
P0-1 (Replay Gate 缺陷)
  └─→ 导致：candidate 永远无法发布到 live
  └─→ 导致：skill 进化闭环断在最后一环
  └─→ 阻塞：P1-3 的实验结论无法形成"skill 确实变好了"的证据

P0-2 (No-Skill 反馈断链)
  └─→ 导致：即使 no-skill 实验发现模型能力不足，也无法触发有效 create_skill
  └─→ 阻塞：skill 从零生成的能力

P1-1 (评分分辨率不足)
  └─→ 加剧 P0-1：PRM 无法区分 candidate 和 baseline
  └─→ 加剧 P1-3：实验分数无法体现 skill 的边际贡献

P1-2 (Live Skills 冗余)
  └─→ 干扰 skill 选择和实验变量纯净性
  └─→ 增加每次请求的 token 消耗

P1-3 (样本量不足)
  └─→ 无法对上述任何结论做统计验证
```

---

## 四、建议优先级

| 优先级 | 问题 | 建议 |
|--------|------|------|
| **P0** | Replay Gate 缺陷 | 重新设计：让 candidate 分支真正使用工具（而非无工具 replay），或改用更细粒度的评分维度，或取消 strict_improvement 改为绝对阈值 + 相对阈值组合 |
| **P0** | No-Skill 反馈断链 | 按已设计的 50 行改动方案修复（用户当前要求暂记 TODO） |
| **P1** | 评分分辨率 | 引入更多评分维度（如 evidence 完整性、root_cause 准确性、confidence 校准），或使用连续分数而非二元 hit |
| **P1** | Live Skills 冗余 | 裁剪到只保留当前实验相关的 6 个 skill，其余归档 |
| **P1** | 样本量 | 扩展 case 集，至少每个 bug class 有 3-5 个 case |
| **P2** | 静态分析天花板 | 寻找或构建可动态运行的固件环境 |
| **P2** | 文件膨胀 | commit 当前工作区，归档历史数据 |
| **P2** | 配置脆弱性 | 脚本化 VM 环境检查，分离 PRM 和 LLM 的模型配置 |
