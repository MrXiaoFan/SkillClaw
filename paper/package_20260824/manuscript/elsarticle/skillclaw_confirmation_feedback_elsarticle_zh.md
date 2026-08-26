# 迈向面向漏洞分析的证据约束型 Skill 演化

## 中文讨论稿说明

本文档是论文 [skillclaw_confirmation_feedback_elsarticle.tex](D:/Code/SkillClaw/SkillClaw/paper/skillclaw_confirmation_feedback_elsarticle.tex) 的中文讨论稿，用于组会、学术交流和后续联合修改。  
它以英文稿当前版本为基础，尽量保持章节结构、核心论点、实验数字与结论一致，但采用更便于讨论的中文表达，不追求逐句直译。

---

# 标题

**迈向面向漏洞分析的证据约束型 Skill 演化**

---

## 摘要

可复用的自然语言 skill 正在成为大语言模型代理（LLM agent）的一种重要控制接口，但在漏洞分析这类高风险任务中，真正困难的问题并不是如何不断生成新的候选 skill，而是如何判断：一次已经完成的分析运行，是否包含了足够可靠、足够可泛化的程序性知识，从而值得写入后续运行会直接使用的 live skill 库。

本文将这一问题表述为**面向漏洞分析代理的证据约束型 skill 演化问题**。我们的基本设定是：代理先在隔离的远端虚拟机上进行 blind 漏洞分析；随后本地系统对最终输出进行评分，并结合源码谓词、逻辑 harness、行为 oracle 或 sanitizer 证据进行外部确认；只有在此之后，演化服务才允许根据该运行记录生成候选 skill，并进一步进入发布判定流程。

围绕这一问题，我们提出了一个分离分析面与确认面的闭环架构：一方面保证 blind 分析阶段不直接接触确认信息；另一方面又允许本地系统对运行结果做归档、确认、候选 skill 生成和发布控制。具体来说，系统包括：远端 blind 执行、可审计的 skill 注入记录、运行级别反馈接口、候选 skill 暂存与 gate 发布路径，以及 live skill 库的保守更新机制。

实验上，我们首先在 6 个固件漏洞案例上进行了 36 次远端 blind A/B 实验，结果表明 skill 的影响具有显著异质性：注入 skill 后的平均得分变化从 `+1.67` 到 `-1.00` 不等。随后，我们又在两个 CGI 命令注入案例上做了补充消融，结果显示：skill 的有效性不仅取决于主题是否“相关”，还强烈依赖于 skill 的程序性结构；一个更强调“先锁定分支、再沿单条分支追到 sink”的 seed skill，在某些任务上比更宽泛的 live 版本更稳定。

进一步地，我们分析了 94 条历史 gate 决策，发现当前闭环中真正的瓶颈并不是 candidate 生成能力，而是 candidate 是否应该进入 live skill 库。replay-only 的 gate 可以过滤明显较差的 candidate，但当 baseline 模型本身已经能完成任务时，它很难区分“真正带来提升的 skill”和“只是无害但冗余的 skill”。

因此，本文的核心贡献并不是宣称 skill 已经能够稳定自主进化，而是建立了一个可操作的研究框架：它使我们能够系统研究在漏洞分析场景下，哪些已验证运行应该被保留为 skill，哪些不应该。

**关键词：** LLM 代理；skill 演化；漏洞分析；外部确认；blind benchmark；发布控制

---

## 1. 引言

LLM 代理越来越多地依赖外部记忆、可复用指令和自然语言 skill 来提升跨任务表现。Voyager、ExpeL 等工作表明，代理可以从交互轨迹中沉淀程序性经验，并在后续任务中复用。SkillClaw 则进一步将这一思想扩展为共享式 skill 生态；另一方面，近期工作也开始研究如何从上下文中自动归纳 skill、如何从轨迹中蒸馏 skill，甚至如何基于环境反馈持续修正 skill。

然而，最近两类研究同时提醒我们：skill 并不天然意味着正收益。

第一类工作指出，**skill 可能带来伤害**。即便某个 skill 在文本上看起来与任务高度相关，它也可能把代理引向错误的步骤、错误的抽象层级，甚至让模型忽略真正关键的程序路径。

第二类工作指出，**skill 的演化本身也可能出问题**。如果系统把一次“看起来成功、但其实不安全或不可泛化”的运行经验直接写入 skill 库，这种错误程序性知识就会被复用，进而污染后续运行。

与此同时，安全领域也开始出现两条相关趋势：一是面向 agentic security 的可复用 playbook / skill 演化；二是更真实、更长程的软件安全 benchmark。也就是说，skill 演化、安全代理、现实评测这三条线都已经在快速发展。但真正没有被系统回答清楚的问题是：

> 当一个漏洞分析代理完成了一次运行之后，我们究竟应该依据什么，决定它是否值得修改 live skill 库？

这就是本文的起点。

在真实漏洞分析工作流中，最难的问题并不是“让模型写出一个新的候选 skill”。更难的问题是：这次运行中是否真的产生了可复用的程序性知识？它是 case-specific 的偶然成功，还是对后续任务真正有价值的稳定经验？因此，这个问题比普通任务成功要严格得多。一次运行可以是正确的，但仍然可能是：

- 正确但冗余：即使没有这个 skill，模型也能做对；
- 正确但过拟合：只适用于当前案例，不应泛化；
- 正确但不安全：如果固化为 skill，反而会污染后续任务。

漏洞分析之所以适合研究这个问题，是因为它提供了一类通用 agent 任务里往往没有的东西：**可执行的外部确认信号**。  
根据具体 case 的不同，我们可以用源码谓词、逻辑 harness、行为 oracle，或 sanitizer 崩溃作为独立于模型叙述之外的证据，对模型的结论进行验证。

这些证据并不能直接证明“skill 在因果上帮助了模型”，但它们至少能让 skill 演化过程受到独立证据的约束。由此，研究重点就从“如何生成更好的 skill”转向了另一个更务实的问题：

> 如何把一条已经验证过的漏洞分析运行，保守而可审计地转化为一个可能进入 live skill 库的候选更新？

本文并不声称提出了一种全新的 skill 检索算法、skill 改写模型，或完整的因果归因方案。我们的目标更聚焦：研究一条完整的漏洞分析闭环，在这条闭环中，

1. blind 运行先在远端执行；
2. skill 在服务端被选择并注入；
3. 最终结果在本地被评分和外部确认；
4. 运行记录被转化为候选 skill 更新；
5. 更新只有在通过 gate 后才允许进入 live skill 库。

围绕这条闭环，我们重点回答三个问题：

1. 在 blind 安全任务中，skill 的作用到底有多不稳定？
2. 轻量级的运行后反馈是否足以支撑候选 skill 生成？
3. 在实际系统中，真正的瓶颈是 candidate 生成，还是 candidate 发布？

---

## 2. 贡献点

本文的贡献主要有四点：

### 贡献 1：提出面向漏洞分析代理的证据约束型 skill 演化生命周期

我们将“从 blind 运行到 live skill 更新”的过程表述为一个完整生命周期，包括：

- blind 执行；
- 外部确认；
- 运行归档；
- 候选 skill 生成；
- 候选发布控制；
- live skill 库更新。

这一定义的重点不是 skill 生成本身，而是**哪些运行值得被沉淀为可复用 skill**。

### 贡献 2：提出分析面 / 确认面分离的远端盲测闭环架构

我们设计了一种 split-plane 架构：远端环境负责 blind 漏洞分析，本地环境负责评分、确认、归档和演化。这样既能降低答案泄漏风险，又能支持运行后证据处理与 skill 演化。

### 贡献 3：将 live skill 发布控制问题作为一类独立研究问题提出并实证分析

我们的实验表明，当前闭环中的主要瓶颈不是 candidate skill 生成，而是：  
**candidate skill 是否应该进入 live skill 库。**

这一点在安全任务中尤为关键，因为错误 skill 一旦进入 live skill 库，会直接影响后续任务。

### 贡献 4：构建了一个用于测量 skill 效果异质性与必要性倾向的漏洞实验协议

我们不仅比较了有 skill / 无 skill，还进一步比较了：

- 无 skill；
- 错 skill；
- seed skill；
- 当前 live skill。

初步实验表明：skill 的效果高度 case-dependent，而且“主题相关”不等于“程序上有帮助”。

---

## 3. 问题形式化

### 3.1 任务运行与验证向量

将一次运行记为：

\[
r = (x, S_r, \tau, y, E)
\]

其中：

- \(x\)：blind 漏洞分析任务；
- \(S_r\)：该轮被选中并注入的 skill 集合；
- \(\tau\)：代理轨迹；
- \(y\)：最终输出；
- \(E\)：收集到的外部证据。

对应地，我们为每次运行保留一个验证向量：

\[
V(r) = (q_{\mathrm{task}}, q_{\mathrm{confirm}}, a_{r,s})
\]

其中：

- \(q_{\mathrm{task}}\)：任务完成质量；
- \(q_{\mathrm{confirm}}\)：外部确认强度；
- \(a_{r,s}\)：运行与 skill 的观察性相关程度。

这里我们刻意不用“因果贡献”这个词，因为本文并不声称已经解决严格因果归因问题。

### 3.2 skill 归因问题

假设一条运行得到了高任务分数和高确认强度，我们能否因此得出：

> 被注入的 skill 一定帮助了这次成功？

一般来说，不能。

设：

- \(y_0\)：没有 skill 时模型会产生的答案；
- \(y_s\)：有该 skill 时模型会产生的答案。

则 skill 的因果效应可写为：

\[
\Delta(s) = q_{\mathrm{task}}(y_s) - q_{\mathrm{task}}(y_0)
\]

如果 \(\Delta(s) > 0\)，skill 真正提供了帮助；否则它要么没帮助，要么有害。  
问题在于，要计算这个量，至少需要成对地跑有 skill / 无 skill 两组运行，而如果还要考虑模型随机性，则往往需要多轮重复。

因此，我们关心的是：

> 能否用外部可执行证据，构造一种比完整 counterfactual ablation 更便宜的近似归因方式？

### 3.3 安全发布问题

当系统根据某次运行生成候选 skill 修订 \(\Delta s\) 后，下一步问题是：

> 是否应该把它写入 live skill 库？

我们用一个保守的 gate 表达这一过程：

\[
\mathrm{Publish}(\Delta s)=
\mathbb{I}\left[
\mathrm{EvidenceSufficient}(\Delta s)\land \mathrm{FollowupPass}(\Delta s)
\right]
\]

其中：

- `EvidenceSufficient`：原始运行是否有足够的证据支撑 skill 更新；
- `FollowupPass`：候选 skill 在后续验证中是否满足发布条件。

问题在于，replay-only 的 gate 只能看到 candidate 再跑一遍的结果，却看不到“没有这个 candidate 时会怎样”。因此，它往往难以区分：

- skill 真正带来了提升；
- skill 只是冗余但无害；
- 这次成功本来就会发生。

### 3.4 研究假设

本文围绕三个假设展开：

- **H1：skill 效果不稳定**  
  注入 domain skill 后，结果不一定稳定提升，甚至可能有净伤害。

- **H2：证据可以作为低成本归因近似**  
  外部可执行证据不能完全替代因果归因，但可以作为比成对 ablation 更便宜的近似信号。

- **H3：replay-only gate 存在结构性局限**  
  这种局限不是简单调参数就能解决的。

---

## 4. 证据约束型 skill 演化框架

### 4.1 泄漏受控的 blind 执行

每个 benchmark case 都同时包含：

- 私有 ground truth；
- 面向代理渲染的 blind prompt；
- 对应的工作目录；
- 后续确认逻辑。

代理在远端虚拟机上执行分析，不能直接接触 ground truth、确认脚本或带答案信息的文件名。

### 4.2 可审计的 skill 注入

每轮运行都会记录：

- 被选中的 skill 名称；
- 注入内容摘要；
- 请求对应的 session 标识；
- 被后续演化消费的 session segment。

这一层不是为了解决因果归因，而是为了保证后续至少能回答：

> 这轮运行到底暴露给了模型什么程序性先验？

### 4.3 多类型外部确认

系统把外部确认分成四类：

1. **源码证据（source-backed）**：确认某条代码谓词或边界关系确实存在；
2. **行为证据（behavior-backed）**：确认程序行为或路径符合预期；
3. **逻辑 harness（logic-backed）**：通过受控测试输入触发目标状态；
4. **sanitizer 证据（sanitizer-backed）**：由运行期检测工具给出内存安全故障等强证据。

不同类型的证据支持的结论强度不同，因此不能简单都视为“确认成功”。

### 4.4 运行级别反馈接口

在完成评分和确认后，系统会为“运行–skill”对构造一个轻量级反馈状态。  
它不是严格的因果估计器，而是一个后续演化可消费的操作性接口。

本文采用四类标签：

- **Supported**：运行正确、证据成立、skill 与运行方法一致；
- **Mismatched**：运行可能正确，但 skill 与任务/方法不匹配；
- **Contradicted**：skill 看起来把代理引向了错误路径；
- **Unknown**：现有记录不足以判断。

### 4.5 候选级发布 gate

演化服务不会直接改写 live skill，而是先生成 candidate。  
candidate 需要经过 replay / follow-up 验证后才能被接受。

当前系统的主要经验是：

- replay-only gate 可以过滤明显差的 candidate；
- 但很难回答“这个 candidate 是否真的比 baseline 更有必要”。

### 4.6 live / candidate / share 分离

系统在物理路径上区分：

- live skill；
- candidate skill；
- 共享运行与 gate 数据。

这不仅是工程组织问题，也是实验设计的一部分：  
它保证 candidate 可以被生成、验证、拒绝，而不会悄悄污染下一轮运行真正使用的 live skill 库。

---

## 5. 原型实现

本文的系统是对 SkillClaw 原始能力的一次研究性扩展。  
原系统已经提供：

- 请求代理；
- skill 选择与注入；
- 会话捕获；
- skill 共享；
- 演化服务。

我们的扩展主要增加：

- leakage-controlled benchmark；
- 远端 blind 执行；
- 漏洞场景下的多类 validator；
- 运行归档与 handoff；
- candidate gate。

### 5.1 分析面与确认面

系统被划分为两个平面：

- **分析面（analysis plane）**：远端 VM 上的代理，通过 SkillClaw 代理进行漏洞分析；
- **确认面（confirmation plane）**：本地服务负责评分、确认、归档、反馈构造和演化触发。

### 5.2 benchmark case

当前 benchmark case 用 JSON 描述，包括：

- blind 工作目录；
- 分析目标；
- 私有 ground truth；
- 评分规则；
- 确认策略。

当前原型覆盖两类 case：

1. **固件 case（firmware cases）**：以二进制静态分析为主；
2. **开源软件 case（open-source cases）**：可配合源码和运行时确认。

### 5.3 评分

评分采用 0–10 的加权规则，主要考察：

- 文件定位；
- 函数定位；
- 根因描述；
- 证据引用。

它的目标是比较 blind run 的任务质量，而不是追求解释文本的逐字等价。

### 5.4 演化服务

演化服务消费反馈 bundle，生成 candidate skill，并在进入 gate 队列前做去重。

### 5.5 模型配置

分析代理与演化服务在实验中使用同一模型后端（GLM-5.2，本地部署），以减少跨模型能力差异带来的混淆。

---

## 6. 实验方法

### 6.1 研究问题

本文实验围绕三个问题：

- **RQ1：** skill 对 blind 漏洞分析的作用有多异质？  
- **RQ2：** 轻量级运行后反馈是否足以作为演化的 triage signal？  
- **RQ3：** 在真实闭环中，瓶颈到底是 candidate 生成，还是 candidate 发布？  

### 6.2 六个固件 case 的 36 次 A/B 实验

主实验覆盖 6 个固件漏洞 case，每个 case 有两个条件：

- **NS（no skill）**
- **WS（with skill）**

每个条件跑 3 轮，因此总计：

\[
6 \times 2 \times 3 = 36
\]

### 6.3 补充 CGI profile 消融

为了进一步回答“topic relevant 是否足够”这个问题，我们又在两个 CGI 命令注入 case 上做了 profile 消融：

- `none`
- `wrong`
- `relevant`
- `seed`

这个补充实验共有 16 条归档运行，主要用于机制解释，而不是并入主 A/B 平均值。

---

## 7. 实验结果

### 7.1 主 A/B 结果：skill 的影响高度异质

| Case | Skill | NS scores | NS mean | WS scores | WS mean | Δ | 结论 |
| --- | --- | --- | ---: | --- | ---: | ---: | --- |
| f453-cmdinject | tenda-triage | 6,8,8 | 7.33 | 6,8,6 | 6.67 | -0.67 | 有害 |
| f453-overflow | elf-triage | 6,2,6 | 4.67 | 6,2,6 | 4.67 | 0.00 | 中性 |
| f9k1122-overflow | elf-triage | 2,6,6 | 4.67 | 6,6,6 | 6.00 | +1.33 | 有帮助 |
| i12-overflow | elf-triage | 3,8,3 | 4.67 | 3,8,8 | 6.33 | +1.67 | 有帮助 |
| firmware2-wireless | cgi-triage | 5,5,5 | 5.00 | 5,5,2 | 4.00 | -1.00 | 有害 |
| firmware2-login | cgi-triage | 5,4,5 | 4.67 | 5,5,5 | 5.00 | +0.33 | 边际提升 |

关键观察：

1. skill 的作用不是稳定正向的；
2. 同一个 skill 在不同 case 上可能分别表现为有帮助、中性或有害；
3. 即使是文本上看起来很相关的 skill，也可能把模型引向错误路径；
4. 模型本身的随机波动足够大，会遮蔽中等规模的 skill 效果。

### 7.2 补充 CGI profile 消融：程序结构比主题相关更重要

| Case | None | Wrong | Relevant | Seed |
| --- | ---: | ---: | ---: | ---: |
| firmware2-wireless | 2.67 | 3.00 | 3.00 | **4.00** |
| firmware2-login | 4.33 | 4.50 | **5.00** | **5.00** |

这一结果说明：

1. **主题相关不等于有效**  
   `relevant` 和 `wrong` 在 `wireless` 上都只到 3.0，远不如 `seed`。

2. **程序结构很重要**  
   `seed` 更强调“先定位 dispatcher，再沿单条分支追 sink”；  
   `relevant` 更强调“先看整个 CGI / 表单结构，再找危险点”。  
   在当前 CGI case 上，前者更稳定。

3. **还不能据此证明严格必要性**  
   在 `login` case 上，`seed` 和 `relevant` 打平，因此我们还不能说“只有这个 skill 才能找到漏洞”。

### 7.3 轻量级反馈与 A/B 结果的关系

目前证据表明，四级反馈标签在方向上是合理的：

- 正向增益 case 往往更接近 `supported`
- 负向增益 case 往往更接近 `contradicted`
- 零增益或弱增益 case 往往更接近 `mismatched`

但本文并不把它解释为严格因果证据，而是把它视为**演化 triage signal**。

### 7.4 gate：真正的瓶颈在发布，而不是生成

当前归档的 gate 决策统计如下：

| 指标 | 数值 |
| --- | ---: |
| 总 gate 决策数 | 94 |
| published | 12 |
| rejected | 82 |
| 含 baseline-aware non-inferiority 元数据的 published | 2 |

这一结果说明：

- candidate skill 可以生成；
- 但 candidate 很难稳定进入 live skill 库；
- 真正难的是判断 candidate 是“真正提升”还是“只是无害冗余”。

---

## 8. 讨论

### 8.1 证据–归因鸿沟

本文最重要的理论认识之一是：

> 外部证据可以验证代理“找到了什么”，但不能直接验证代理“为什么能找到”。

这就是所谓的证据–归因鸿沟。

### 8.2 对 skill 库设计的启示

同一个 skill 在不同 case 上可能有完全不同的作用，这说明：

- skill 选择必须 case-sensitive；
- skill 评估也必须 case-sensitive；
- 不能仅凭文本相似度决定 skill 是否应该长期保留。

### 8.3 为什么需要更强的 gate

当前 replay-only gate 的局限很明确：

- 如果 baseline 本来就高，candidate 很难证明自己“更好”；
- 于是系统会在“真正提升”和“无害冗余”之间长期摇摆。

未来更合理的方向包括：

1. **counterfactual ablation gate**  
   明确比较 with-skill / no-skill。

2. **non-inferiority gate**  
   允许“至少不更差”的 candidate 先进入 live skill，再在更长周期做 retention 决策。

### 8.4 与已有工作的关系

本文与已有工作最重要的区别，不是“我们也有 skill”，而是：

1. 我们聚焦的是**漏洞分析场景**；
2. 我们研究的是**从运行到 live skill 库**的完整过渡；
3. 我们强调的是**发布控制问题**，而不是单纯的生成问题。

---

## 9. 相关工作

### 9.1 skill 生成、复用与演化

Voyager、ExpeL、Reflexion、MemGPT、SkillClaw、Ctx2Skill、OPID 等工作已经表明，skill 的生成、积累与复用是 LLM agent 研究的重要方向。

### 9.2 verifier / environment 驱动的 skill 修正

SPARK、Trace2Skill、VeriSkill、SkillEvolBench 等工作已经把环境反馈、verifier 反馈和 skill 演化联系起来。  
本文不再声称“运行后反馈”本身是一个全新观点，而是更强调它在漏洞分析闭环中的工程和研究位置。

### 9.3 skill 失败、misevolution 与治理

skillharmful、misevolution、detourhijack 这类工作共同说明：  
skill 不仅可能没用，还可能有害；因此 skill 系统需要治理逻辑，而不仅是生成逻辑。

### 9.4 安全代理、playbook 与 benchmark

PentestGPT、漏洞分析相关工作、EvoHunt、SEC-bench Pro 等说明，安全代理与现实 benchmark 已经成为快速发展的方向。  
本文的切入点则是：如何把一次已验证运行转化为 skill 生命周期中的可治理对象。

---

## 10. 有效性威胁

本文当前版本的主要局限包括：

1. **样本量仍小**：A/B 主实验每个条件只有 3 轮；
2. **模型波动较大**：会遮蔽中等 skill 效果；
3. **只验证了一个模型家族**；
4. **固件 case 主要依赖静态分析，证据强度不如 sanitizer-backed case**；
5. **四级反馈不是严格因果估计器**；
6. **94 条 gate 决策来自多个开发阶段的 gate 版本**；
7. **blind case 仍可能存在答案泄漏风险**；
8. **validator 自身也可能不完备**。

---

## 11. 结论

本文研究的核心问题不是“skill 能不能生成”，而是：

> 一次 blind 漏洞分析运行，什么时候应该被转化为 live skill？

我们已经初步完成了以下几件事：

1. 把 blind 执行、外部确认、运行归档、候选生成、发布 gate 和 live skill 更新连接成一条可操作闭环；
2. 用 36 次远端 blind A/B 实验表明，skill 的作用具有显著异质性；
3. 用补充 CGI 消融表明，skill 的程序结构至少和主题相关性一样重要；
4. 用 94 条 gate 决策证明：当前真正的瓶颈是 candidate 发布，而不是 candidate 生成。

因此，本文当前最稳妥的结论不是“skill 已经能稳定自主进化”，而是：

> 我们已经建立了一个足以系统研究这一问题的框架，并且已经定位到：未来最关键的研究难点在于，如何用更可靠的 gate 区分真正有价值的 skill 增益与无害但冗余的 candidate。

---

## 参考文献说明

本文中文讨论稿不单独列出中文参考文献列表，所有参考文献与英文稿一致，请以：

- [references.bib](D:/Code/SkillClaw/SkillClaw/paper/references.bib)

为准。

