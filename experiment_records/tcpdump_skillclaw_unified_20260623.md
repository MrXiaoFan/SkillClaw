# tcpdump 4.9.1 SkillClaw 统一 runner 实验记录（2026-06-23）

## 实验目的

本轮实验用于验证新建的 `run_eval_case.py` 统一入口能否在远端 VM 上真实调用 `Claude Code + SkillClaw key`，并观察 SkillClaw 在 tcpdump 4.9.1 已知 IPv6 fragmentation header buffer over-read case 上的漏洞定位效果。

目标 case 为 `tcpdump-4.9.1-cve-2017-13031`。Ground truth 设置为：CVE `CVE-2017-13031`，文件 `print-frag6.c`，函数 `frag6_print`，关键证据包括 `ND_TCHECK`、`ip6f_offlg`、`ip6f_ident`。

## 实验设置

远端环境位于 `li@192.168.1.4:~/skillclaw-eval/tcpdump-4.9.1`，目标二进制为 `./tcpdump`。本轮通过 `experiment_scripts/run_eval_case.py` 启动真实 Agent 运行，模式为 `skillclaw-inline`，模型配置为 `skillclaw-model`，远端 Claude Code 当前连接 SkillClaw proxy。

统一 runner 自动生成 prompt、raw 输出、score、validation 和 final record。该轮 run metadata 显示 `agent_ran=true`，`run_status=0`，说明确实调用了 Claude Code 并正常结束。

## 实验结果

| 维度 | 结果 |
|---|---|
| 总分 | 8/10 |
| CVE | 未命中，输出为 `CVE-2017-12932` |
| 文件 | 命中 `print-frag6.c` |
| 函数 | 命中 `frag6_print` |
| 证据 | 命中 `ND_TCHECK`、`ip6f_offlg`、`ip6f_ident` |
| 根因 | 命中 IPv6 fragment header insufficient bounds check |
| validation | passed |

本轮结果说明，模型在源码位置、函数和关键字段证据上定位较好，但 CVE 编号仍然错误。这与此前 libxml2 case 的现象相似：SkillClaw/LLM 可以较好地定位局部代码证据，但 CVE 映射容易偏到相邻漏洞或错误编号。

## Skill 注入观察

本轮 SkillClaw 实际注入的 skill 为：

- `skillclaw-proxy-introspection`
- `skillclaw-claude-env`
- `skillclaw-skill-discovery`

这三个都是 SkillClaw 机制/环境/检索类 skill，而不是 tcpdump、IPv6 parser 或二进制漏洞分析类 skill。因此，本轮 `8/10` 不能简单归因于“漏洞定位 skill 有效”。更合理的解释是：基础模型本身完成了主要定位，而 SkillClaw 的检索器没有选到任务相关 skill。

这暴露出一个重要工程和研究问题：如果 feedback 机制只根据分数和 validation 状态给出 positive，就会把模型自身能力误记为系统自省类 skill 的贡献。因此本轮实验后已补充 `skill_relevance` 字段：当选中的 skill 全部为 `skillclaw-*` 基础设施/自省类 skill，且没有与 case 的项目、函数、文件、漏洞类型或根因关键词匹配时，feedback 从 positive 修正为 neutral，并给出 `inspect_retrieval_before_promoting_skill`。

## 初步结论

本轮实验验证了统一 runner 的可用性，也提供了一个负向/警示样本：高分结果并不必然说明 SkillClaw 选中的 skill 有效。如果 skill 检索选中了不相关 skill，而模型仍然得分较高，则该样本应被标注为“base-model capability with irrelevant skill injection”，不能作为 skill 进化正反馈。更新后的 final record 已将本轮反馈标记为 neutral。

后续工程上应优先改进两点：第一，在 final record 中显式记录 skill relevance；第二，在 feedback 生成时区分“answer positive”和“skill positive”，避免把模型自身能力误记为 skill 的贡献。

## 关联文件

- `tcpdump-skillclaw-final-with-injection-20260623.json`
- `tcpdump-skillclaw-raw-20260623.txt`
- `tcpdump-skillclaw-score-20260623.json`
- `tcpdump-skillclaw-validation-20260623.json`
