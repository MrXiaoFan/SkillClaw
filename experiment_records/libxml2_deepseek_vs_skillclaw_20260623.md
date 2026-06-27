# libxml2 2.9.4 对照实验记录（2026-06-23）

## 实验目的

本轮实验用于比较同一远端 Ubuntu VM、同一目标软件、同一任务条件下，`Claude Code + SkillClaw key` 与 `Claude Code + DeepSeek 直连 key` 对 libxml2 2.9.4 已知越界读漏洞的定位效果。目标不是证明某一方绝对更强，而是观察 SkillClaw server-side skill 注入是否能改善漏洞定位中的文件、函数、根因和证据质量。

目标 case 为 `libxml2-2.9.4-cve-2017-8872`。Ground truth 设置为：CVE `CVE-2017-8872`，文件 `HTMLparser.c`，函数 `htmlParseTryOrFinish`，关键证据包括 `in->cur[2]`、`in->cur[3]` 和 `avail` 相关 guard/lookahead read 问题。

## 实验设置

远端环境位于 `li@192.168.1.4:~/skillclaw-eval/libxml2-2.9.4`，目标二进制为 `.libs/xmllint`。两组实验均通过 Claude Code 非交互模式执行，并在实验后运行统一评分脚本与 case-level validator。

评分规则为 10 分制：CVE 命中 2 分，文件命中 2 分，函数命中 3 分，根因命中 2 分，关键证据命中 1 分。该评分侧重漏洞定位质量，而不是自然语言报告完整度。

需要注意：当前 `validation=passed` 表示 case-level 验证通过，包括源码 ground truth 位置存在、构建产物可检查、bundle script 能识别目标 guard/lookahead 模式；它不等价于 Agent 自己完成了真实 PoC crash 触发。ASan/PoC 动态触发项目前仍处于 disabled/placeholder 状态。

## 实验结果

| 组别 | 连接方式 | 实际 skill 注入 | 得分 | CVE | 文件 | 函数 | 证据 | 根因 | 验证 |
|---|---|---|---:|---|---|---|---|---|---|
| SkillClaw | `skillclaw-model` via `http://10.12.189.47:30000` | `source-parser-state-machine-oob`, `skillclaw-proxy-introspection`, `skillclaw-skill-discovery` | 8/10 | 未命中 | 命中 | 命中 | 命中 | 命中 | passed |
| DeepSeek 直连 | `deepseek-v4-pro` via `https://api.deepseek.com/anthropic` | 无 | 6/10 | 命中 | 命中 | 未命中 | 未命中 | 命中 | passed |

SkillClaw 组没有给出正确的 `CVE-2017-8872`，而是混入了多个 libxml2 相邻 CVE；但它定位到了 `HTMLparser.c` 和 `htmlParseTryOrFinish`，并给出了 `in->cur[2]`、`in->cur[3]`、`avail` 等更贴近 ground truth 的代码证据。该结果表明 `source-parser-state-machine-oob` 这类领域 skill 对源码级根因定位有正向作用，但 CVE 映射和候选收敛仍然不足。

DeepSeek 直连组正确输出了 `CVE-2017-8872` 和 `HTMLparser.c`，但将关键函数定位到 `htmlCurrentChar`，没有命中 `htmlParseTryOrFinish`，也没有给出本 case 关注的 lookahead/avail 证据。该结果说明直连模型可能凭公共知识或语义记忆命中 CVE，但在具体源码路径和可验证证据上不一定更精确。

另外，DeepSeek 直连组未按提示输出单一 JSON 对象，而是输出自然语言说明；评分脚本因此退化为全文匹配。后续需要把“结构化输出遵循程度”加入实验质量指标，否则会低估输出格式失控对自动评估流水线的影响。

## 初步结论

这组实验支持一个更细粒度的判断：SkillClaw 并不必然提高所有维度，但可以改变模型的关注点。对于 libxml2 这一 case，SkillClaw 的优势体现在源码函数、guard 条件和局部证据定位；DeepSeek 直连的优势体现在 CVE 名称命中。二者差异说明后续研究不应只比较“是否找到漏洞”，而应拆分为 CVE 映射、文件定位、函数定位、根因解释、证据质量、验证可复现性等多个维度。

从工程角度看，下一步应强化两类机制：一是 skill 注入后的候选收敛，避免输出过多相邻 CVE 和旁路函数；二是 validator 与 Agent 输出绑定得更紧，区分“环境/源码确实存在 ground truth”与“Agent 自己是否命中 ground truth”。从研究角度看，这组结果可以作为“文本 skill 能提升局部定位但可能削弱全局 CVE 映射”的初始证据。

## 关联文件

- `libxml2-skillclaw-final-with-injection-20260623.json`
- `libxml2-direct-final-20260623.json`
- `libxml2-direct-raw-20260623.txt`
- `libxml2-direct-score-20260623.json`
- `libxml2-direct-validation-20260623.json`
