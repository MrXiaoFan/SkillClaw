# tcpdump 4.9.1 对照实验记录（2026-06-23）

## 实验目的

本轮实验比较 `Claude Code + SkillClaw key` 与 `Claude Code + DeepSeek 直连 key` 在 tcpdump 4.9.1 已知 IPv6 fragmentation header buffer over-read case 上的漏洞定位表现，并验证统一入口 `run_eval_case.py` 是否能稳定产出 prompt、raw、score、validation 和 final record。

目标 case 为 `tcpdump-4.9.1-cve-2017-13031`。Ground truth 设置为：CVE `CVE-2017-13031`，文件 `print-frag6.c`，函数 `frag6_print`，关键证据包括 `ND_TCHECK`、`ip6f_offlg`、`ip6f_ident`。

## 实验结果

| 组别 | 连接方式 | 实际 skill 注入 | 得分 | CVE | 文件 | 函数 | 证据 | 根因 | 验证 |
|---|---|---|---:|---|---|---|---|---|---|
| SkillClaw | `skillclaw-model` via `http://10.12.189.47:30000` | `skillclaw-proxy-introspection`, `skillclaw-claude-env`, `skillclaw-skill-discovery` | 8/10 | 未命中，输出 `CVE-2017-12932` | 命中 | 命中 | 命中 | 命中 | passed |
| DeepSeek 直连 | `deepseek-v4-pro` via `https://api.deepseek.com/anthropic` | 无 | 8/10 | 未命中，输出 `CVE-2017-13034` | 命中 | 命中 | 命中 | 命中 | passed |

两组都准确定位到 `print-frag6.c:frag6_print` 以及关键字段/检查逻辑，但都没有给出正确 CVE 编号。这说明在 tcpdump case 上，源码级定位能力和 CVE 精确映射能力需要分开评价。模型能找到正确代码位置，并不代表能稳定映射到正确 CVE。

## 关键观察

SkillClaw 组虽然得分较高，但实际注入的是三个系统自省/环境类 skill，而不是 tcpdump、IPv6 parser 或二进制漏洞分析相关 skill。因此本轮不能证明相关漏洞定位 skill 产生了直接增益。更新后的 feedback 逻辑已将该情况标记为 `neutral`，建议 `inspect_retrieval_before_promoting_skill`，避免把基础模型能力错误归因给无关 skill。

DeepSeek 直连组没有 skill 注入，得分同为 8/10。更新后的 feedback 将其标记为 `use_as_baseline_positive`，表示它可作为强基线样本，而不是 skill 进化正反馈。

这组实验与 libxml2 case 形成互补：libxml2 中 SkillClaw 对局部证据定位更强，但 CVE 映射较差；tcpdump 中两组均能定位源码和函数，但 CVE 均偏移。后续实验应继续拆分评价维度，而不是只比较总分。

## 工程结论

统一 runner 已能支持真实 Agent 调用和结果归档。`skill_relevance` 字段是必要的，因为仅靠 `score + validation` 会误判 skill 贡献。后续应继续改进 SkillClaw 检索策略，让任务提示中的项目、协议、漏洞类型、函数名等信号更强地影响 skill 选择。

## 关联文件

- `tcpdump-skillclaw-final-with-injection-20260623.json`
- `tcpdump-direct-final-20260623.json`
- `tcpdump-skillclaw-raw-20260623.txt`
- `tcpdump-direct-raw-20260623.txt`
- `tcpdump-skillclaw-score-20260623.json`
- `tcpdump-direct-score-20260623.json`
- `tcpdump-skillclaw-validation-20260623.json`
- `tcpdump-direct-validation-20260623.json`
