# 项目周报（2026-08-03 至 2026-08-09）

附件：  
- [firmware_skill_ablation_summary.md](D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260805/firmware_skill_ablation_summary.md)

## 本周完成工作

1. **继续完善 SkillClaw extension 的闭环工程**
   - 继续打通并稳定 `远端 VM 上的 Claude -> 本机 SkillClaw -> 本地评测/隐藏答案校验 -> Evolve Server -> 后续验证` 这条链路。
   - 本周重点不是新增独立脚本，而是把已有流程收拢到统一工程路径下，补强结果回填、validation followup、反馈 bundle 生成与结果汇总。
   - 涉及的核心工程文件主要包括：
     - `evaluation/evolution.py`
     - `evaluation/runs/run_single_case.py`
     - `evaluation/runs/run_remote_case.py`
     - `evaluation/postprocess/finalize_record.py`
     - `evolve_server/engines/workflow.py`
     - `evolve_server/pipeline/execution.py`

2. **梳理并重构 validation / gate 相关模块职责**
   - 本周对验证链路做了较大幅度整理，重点是把“实验结果打分与隐藏答案校验”和“候选 skill 的后续 gate 验证”在工程上进一步拆清。
   - 相关改动主要落在：
     - `evaluation/validation/`
     - `skillclaw/validation_worker.py`
     - `skillclaw/replay_gate_worker.py`
     - `skillclaw/replay_gate_store.py`
   - 当前状态是：闭环里的“结果校验”和“候选 skill 拒绝/接受”已经能分别落盘和汇总，但命名和模块边界后续仍可继续收敛。

3. **新增并接入 firmware blind benchmark case**
   - 新增了两个固件 CGI 命令注入数据集案例：
     - `firmware2-login-cgi-cve-2026-2527`
     - `firmware2-wireless-cgi-cve-2026-2529`
   - 同时补充了配套 skill 消融 profile，支持直接切换 `none / wrong / relevant / seed` 四种可见 skill 状态进行对比实验。
   - 对应工程路径：
     - `benchmarks/cases/firmware2-login-cgi-cve-2026-2527.json`
     - `benchmarks/cases/firmware2-wireless-cgi-cve-2026-2529.json`
     - `skillspace/ablation_profiles/`

4. **完成一轮可汇报的 firmware skill 消融实验**
   - 本周围绕上述两个 firmware case，累计整理出 **16 次 ablation run**：
     - `wireless`：`none=3`，`relevant=2`，`wrong=1`，`seed=2`
     - `login`：`none=3`，`relevant=2`，`wrong=2`，`seed=1`
   - 汇总结果表明：
     - `wireless` 上 `seed` 平均分 `4.0`，高于 `relevant=3.0` 和 `none=2.67`
     - `login` 上 `seed` 与 `relevant` 同为 `5.0`
   - 这说明 skill 的写法差异已经会影响 blind 漏洞分析结果，但目前还不能证明“必须依赖该 skill 才能找到漏洞”。

5. **整理形成可直接汇报的结果包**
   - 本周将实验结果收敛为当前 briefing 包，补齐：
     - 消融实验总表
     - 闭环证明表
     - 当前结果摘要
     - firmware skill 消融实验说明附件
   - 主要结果文件：
     - `reports/current/briefing_20260805/firmware_ablation_runs.csv`
     - `reports/current/briefing_20260805/firmware_ablation_summary.csv`
     - `reports/current/briefing_20260805/closed_loop_proof.csv`
     - `reports/current/briefing_20260805/summary.md`
     - `reports/current/briefing_20260805/firmware_skill_ablation_summary.md`

## 本周实验与阶段性结论

1. **闭环工程已经真实跑通**
   - 当前不再只是概念设计，而是已经能看到 `handoff -> consumed -> validation_followup` 的实际记录。
   - 即：分析结果可以进入 Evolve，Evolve 也可以产出候选 skill 修改，再进入后续验证。

2. **skill 会影响 blind 分析结果**
   - 通过 `none / wrong / relevant / seed` 四组消融，已经能看到不同 skill 状态会导致不同输出分数与不同错误模式。
   - 尤其在 `wireless` case 上，`seed` 版 skill 明显优于当前 `relevant` 版。

3. **当前瓶颈已从“链路不通”转向“进化质量不足”**
   - 本周的核心收获不是单纯提升了分数，而是更明确地定位到：  
     当前问题已经不是 Evolve 收不到结果，而是 **Evolve 生成的候选 skill 修改大多还会被后续 validation 拒绝**。
   - 也就是说，接下来需要进一步研究“什么样的 skill 提示结构才真正有助于漏洞定位”，而不是继续堆流程脚本。

## 问题与风险

1. 当前 firmware case 的实验已经能说明 skill 有影响，但证据仍不足以支持“skill 必要性”这个更强结论。  
2. 现有闭环可以产出候选 skill 修改，但候选质量还不稳定，尚未形成可稳定接受的 skill 进化结果。  
3. validation、gate、score 等概念虽然工程上已基本可用，但从命名和模块边界看，后续仍需继续收敛，以降低理解成本。

## 下周计划

1. 继续围绕 firmware case 做更细的 skill 阈值实验，重点验证“哪些 skill 内容是必要的、哪些内容是多余甚至有害的”。  
2. 在已有闭环基础上，观察并分析 candidate skill 被拒绝的原因，缩小“闭环存在”与“有效进化”之间的差距。  
3. 结合本周消融结果，进一步收敛工程模块边界，并为后续论文实验整理更稳定的实验口径与证据链。
