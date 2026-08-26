# 参考文献人工核查清单（arXiv 占坑稿）

对应稿件：
- [skill_evolution_blind_vulnerability_analysis_arxiv.tex](D:/Code/SkillClaw/SkillClaw/paper/skill_evolution_blind_vulnerability_analysis_arxiv.tex)
- [references_arxiv_checked.bib](D:/Code/SkillClaw/SkillClaw/paper/references_arxiv_checked.bib)

说明：
- 本清单只覆盖当前 arXiv 占坑稿实际使用到的参考文献。
- 我尽量全部改成了可在 arXiv 或论文页面直接核对的真实条目。
- 其中相当一部分是 2026 年的 arXiv 预印本，是真实论文，但未必已经正式发表。这个状态我在条目里单独写明。
- 我也标出了哪些条目是“保留”、哪些条目是“更正后保留”、哪些是“替换旧占位条目”。

---

## 1. Voyager

- **条目键**：`voyager`
- **真实文献**：Wang et al., *Voyager: An Open-Ended Embodied Agent with Large Language Models*, arXiv:2305.16291
- **来源**：https://arxiv.org/abs/2305.16291
- **文献类型**：真实 arXiv 论文
- **主要内容**：提出长期运行的 LLM agent，通过技能库和自动代码积累持续完成 Minecraft 中的开放任务。
- **在本文中为什么引用**：用来说明“agent 可以跨任务积累可复用 procedural knowledge”这条大背景已经成立。
- **处理结论**：保留

## 2. ExpeL

- **条目键**：`expel`
- **真实文献**：Zhao et al., *ExpeL: LLM Agents Are Experiential Learners*, arXiv:2308.10144
- **来源**：https://arxiv.org/abs/2308.10144
- **文献类型**：真实 arXiv 论文
- **主要内容**：让 agent 从历史经验中提炼文字形式的经验规则，并在后续任务中复用。
- **在本文中为什么引用**：说明“从 run 中抽取经验并复用”已经是 agent 学习的重要路线。
- **处理结论**：保留，并更正了作者信息

## 3. SkillClaw

- **条目键**：`skillclaw`
- **真实文献**：Ma et al., *SkillClaw: Let Skills Evolve Collectively with Agentic Evolver*, arXiv:2604.08377
- **来源**：https://arxiv.org/abs/2604.08377
- **文献类型**：真实 arXiv 论文
- **主要内容**：提出 SkillClaw 原生框架，核心关注共享 skill、演化器和多 agent skill 生命周期。
- **在本文中为什么引用**：我们的工程是在 SkillClaw 基础上扩展 blind 漏洞分析与 feedback/gate 链路，所以这里既是背景，也是直接系统来源。
- **处理结论**：保留

## 4. Ctx2Skill

- **条目键**：`ctx2skill`
- **真实文献**：Si et al., *From Context to Skills: Can Language Models Learn from Context Skillfully?*, arXiv:2604.27660
- **来源**：https://arxiv.org/abs/2604.27660
- **文献类型**：真实 arXiv 论文
- **主要内容**：研究怎样把上下文中的临时经验转成可复用 skill。
- **在本文中为什么引用**：它和我们都关心“经验如何沉淀为 skill”，但它更偏 context-to-skill 学习，不是漏洞分析场景。
- **处理结论**：保留

## 5. OPID

- **条目键**：`opid`
- **真实文献**：Yang et al., *OPID: On-Policy Skill Distillation for Agentic Reinforcement Learning*, arXiv:2606.26790
- **来源**：https://arxiv.org/abs/2606.26790
- **文献类型**：真实 arXiv 论文
- **主要内容**：从 agent 强化学习轨迹中蒸馏出更稳定的技能策略。
- **在本文中为什么引用**：用来代表“skill distillation / skill refinement”方向，说明 skill 进化已经在别的 agent 场景中成为问题。
- **处理结论**：保留

## 6. SPARK / Evidence Over Plans

- **条目键**：`spark`
- **真实文献**：Zhou et al., *Evidence Over Plans: Online Trajectory Verification for Skill Distillation*, arXiv:2605.09192
- **来源**：https://arxiv.org/abs/2605.09192
- **文献类型**：真实 arXiv 论文
- **主要内容**：强调 skill refinement 不应只靠 verbal reflection，而应结合在线轨迹验证与证据。
- **在本文中为什么引用**：和我们论文里“external confirmation / evidence-constrained feedback”这条思路最接近，能支撑“技能进化不能只看 narrative，要看证据”。
- **处理结论**：保留，并修正了旧 bib 中错误的标题

## 7. Trace2Skill

- **条目键**：`trace2skill`
- **真实文献**：Ni et al., *Trace2Skill: Distill Trajectory-Local Lessons into Transferable Agent Skills*, arXiv:2603.25158
- **来源**：https://arxiv.org/abs/2603.25158
- **文献类型**：真实 arXiv 论文
- **主要内容**：从局部轨迹 lesson 中抽取可迁移 skill。
- **在本文中为什么引用**：它直接对应我们关心的“run 结束后，哪些局部经验值得沉淀成长期 skill”。
- **处理结论**：保留，并修正了旧 bib 中错误的标题和作者

## 8. SkillEvolBench

- **条目键**：`skillevolbench`
- **真实文献**：Lei et al., *SkillEvolBench: Benchmarking the Evolution from Episodic Experience to Procedural Skills*, arXiv:2605.24117
- **来源**：https://arxiv.org/abs/2605.24117
- **文献类型**：真实 arXiv 论文
- **主要内容**：把 episodic-to-procedural skill evolution 当成一个专门 benchmark 问题。
- **在本文中为什么引用**：它帮助说明“skill evolution 本身已经开始成为独立评测对象”，和我们的占坑思路一致。
- **处理结论**：保留，并修正了旧 bib 中错误的 arXiv 编号和作者

## 9. VeriSkill

- **条目键**：`veriskill`
- **真实文献**：Jia et al., *VeriSkill: A Self-Evolution Framework for Program Verification Skills*, arXiv:2607.27733
- **来源**：https://arxiv.org/abs/2607.27733
- **文献类型**：真实 arXiv 论文
- **主要内容**：研究 program verification 任务中的 self-evolving skills。
- **在本文中为什么引用**：它说明“skill 进化 + 外部验证”并不限于安全漏洞场景，我们的工作是把这条路延展到 blind 漏洞分析。
- **处理结论**：保留，并修正了旧 bib 中错误的 arXiv 编号和作者

## 10. Agent Skills Can Be Harmful

- **条目键**：`skillharmful`
- **真实文献**：Dong et al., *Agent Skills Can Be Harmful: An Empirical Study of Skill-Induced Failures in LLM Agents*, arXiv:2608.11888
- **来源**：https://arxiv.org/abs/2608.11888
- **文献类型**：真实 arXiv 预印本
- **主要内容**：系统分析 skill 不仅可能帮助 agent，也可能把它推向错误路径。
- **在本文中为什么引用**：这是我们论文“为什么不能只堆 skill，为什么必须研究 skill evolution / publication control”的关键背景支撑。
- **处理结论**：保留，并修正了旧 bib 中匿名作者占位

## 11. Practice Makes Unsafe

- **条目键**：`misevolution`
- **真实文献**：Mao et al., *Practice Makes Unsafe: Skill Misevolution in Self-Improving LLM Agents*, arXiv:2608.12851
- **来源**：https://arxiv.org/abs/2608.12851
- **文献类型**：真实 arXiv 预印本
- **主要内容**：关注 self-improving agents 中 skill 反而向不安全方向演化的问题。
- **在本文中为什么引用**：它支撑我们文中“candidate 生成不是终点，发布策略和治理才是核心难点之一”。
- **处理结论**：保留，并修正了旧 bib 中匿名作者占位

## 12. PentestGPT

- **条目键**：`pentestgpt`
- **真实文献**：Deng et al., *PentestGPT: An LLM-Empowered Automatic Penetration Testing Tool*, arXiv:2308.06782
- **来源**：https://arxiv.org/abs/2308.06782
- **文献类型**：真实 arXiv 论文
- **主要内容**：用 LLM 辅助渗透测试流程，是安全 agent 方向的代表工作之一。
- **在本文中为什么引用**：用来说明安全任务里已经有 agent 化工作，但大多不直接讨论 skill 进化和 run-to-skill transition。
- **处理结论**：保留

## 13. To Err is Machine

- **条目键**：`steenhoek2024vulndetect`
- **真实文献**：Steenhoek et al., *To Err is Machine: Vulnerability Detection Challenges LLM Reasoning*, arXiv:2403.17218
- **来源**：https://arxiv.org/abs/2403.17218
- **文献类型**：真实 arXiv 论文
- **主要内容**：研究 LLM 在漏洞检测任务中的真实能力和推理局限。
- **在本文中为什么引用**：用来替代旧 draft 中那个过于模糊、来源不稳的 `gpt4vuln` 占位条目，作为“LLM 漏洞分析经验研究”引用。
- **处理结论**：替换旧占位条目

## 14. EvoHunt

- **条目键**：`evohunt`
- **真实文献**：Liu et al., *Transferable Self-Evolving Playbooks for Agentic Security Auditing*, arXiv:2606.16420
- **来源**：https://arxiv.org/abs/2606.16420
- **文献类型**：真实 arXiv 预印本
- **主要内容**：研究安全审计中的可迁移、可自演化 playbook。
- **在本文中为什么引用**：它是和我们最相邻的安全方向工作之一，但它更偏 playbook 演化，我们更聚焦 blind 漏洞分析中的 skill 进化闭环。
- **处理结论**：保留

## 15. SEC-bench Pro

- **条目键**：`secbenchpro`
- **真实文献**：Lee et al., *SEC-bench Pro: Can Language Models Solve Long-Horizon Software Security Tasks?*, arXiv:2605.26548
- **来源**：https://arxiv.org/abs/2605.26548
- **文献类型**：真实 arXiv 预印本
- **主要内容**：构建更真实、更长程的软件安全任务 benchmark。
- **在本文中为什么引用**：我们论文里一直强调 long-horizon blind analysis 和 leakage control，这篇工作能支撑“现实安全任务不能只靠简单单轮问答评估”。
- **处理结论**：保留，并修正了旧 bib 中错误的 arXiv 编号

---

## 本轮我做的主要修正

1. 新建了独立引用库：
   - [references_arxiv_checked.bib](D:/Code/SkillClaw/SkillClaw/paper/references_arxiv_checked.bib)
   当前 arXiv 占坑稿现在只用这份“已核对”的 bib。

2. 修正了多条旧 bib 中不准确的信息，包括：
   - `spark` 标题错误；
   - `trace2skill` 标题和作者错误；
   - `skillevolbench` arXiv 编号错误；
   - `veriskill` arXiv 编号和作者错误；
   - `secbenchpro` arXiv 编号错误；
   - `skillharmful`、`misevolution` 旧版匿名作者占位；
   - `gpt4vuln` 替换为可核对的真实论文 `To Err is Machine`。

3. 当前仍需你人工把关的地方：
   - 有些 2026 年相关工作都是 arXiv 预印本，虽然是真实论文，但还未正式发表；
   - 是否保留所有这些“很新”的 2026 引文，要看你希望论文更偏“前沿占坑”还是更偏“保守稳妥”。
