# Firmware Skill 消融实验整理

整理时间：2026-08-06

## 1. 当前实验技术流程

远端 VM 上的 Claude 在 blind 工作区分析样本，请求先经过本机 `SkillClaw`。`SkillClaw` 先用代码规则从当前 `skillspace/live/` 中挑选可见 skill：它不会让 LLM 先选，而是根据任务文本与 skill 的 `name`、`description`、`category` 做关键词重叠打分，再取 top-k 注入。之后 Claude 基于注入后的 prompt 做漏洞分析，输出固定 JSON：`predicted_cves`、`predicted_files`、`predicted_functions`、`root_cause`、`evidence`、`confidence`。本地评测程序再做两步：一是按 ground truth 打分；二是用 agent 不可见的隐藏答案文件做 `oracle 校验`，即隐藏标准答案校验。最终生成 `final-enriched.json`，再交给 `Evolve Server` 产出 skill 修改候选，并进入后续验证与接受/拒绝流程。

## 2. 实验思路

本轮实验的研究对象是两个固件 CGI 命令注入案例。

- `wireless`：`wireless.cgi` 在 `page=DeleteMac` 分支中读取 HTTP POST 参数，拼接 shell 命令并最终 `system()` 执行。
- `login`：`login.cgi` 在 `page=login` 路径中读取 `ipaddr` 参数，拼接 `/sbin/applogin.sh ...` 后 `system()` 执行。

实验设计上，保持以下条件不变：同一个 case、同一台远端 VM、同一个 Claude 通道、同一种 blind prompt、同一套评分与隐藏答案校验、同一条 `SkillClaw -> Evolve -> validation` 流程。只改变一个变量：当前对 LLM 可见的 firmware skill 版本。

## 3. 实验变量

| 版本 | 含义 | 关键差异 |
| --- | --- | --- |
| `none` | 不注入该类 skill | 没有固件 CGI 专用引导 |
| `wrong` | 注入错误方向 skill | 注入 `firmware-embedded-lua-shell-extraction`，它偏 Lua/脚本抽取，不适合当前 CGI ELF 参数流分析 |
| `relevant` | 当前相关版 skill | 先枚举 `/cgi-bin/`、表单、请求结构，再找 sink |
| `seed` | 早期种子版 skill | 先找 `page/action/mode/cmd` 分发点，再沿单条分支追到 `system()` |

一句话概括两版核心差异：

- `relevant`：先看“整个 CGI 面”，再找危险点。
- `seed`：先锁定“哪条分支真正执行命令”，再沿分支往下追。

## 4. 实验结果

本轮 firmware 消融共跑了 16 次：

- `wireless`：`none=3`，`relevant=2`，`wrong=1`，`seed=2`
- `login`：`none=3`，`relevant=2`，`wrong=2`，`seed=1`

打分规则是默认 10 分制：

- CVE 命中：2 分
- 文件命中：2 分
- 函数命中：3 分
- 关键证据命中：1 分
- 根因描述命中：2 分

汇总结果如下：

| case | none | relevant | wrong | seed |
| --- | ---: | ---: | ---: | ---: |
| `wireless` | 2.67 | 3.0 | 3.0 | **4.0**（最高 5.0） |
| `login` | 4.33 | **5.0** | 4.5 | **5.0** |

代表性单次结果：

- `wireless + relevant`：命中了命令注入方向，但文件、函数、CVE 没对上，得分 `3/10`
- `login + seed`：命中了目标文件 `login.cgi`，并给出了合理根因，但函数和 CVE 没命中，得分 `5/10`

## 5. 结论

1. 当前工程已经真实跑通了 `SkillClaw -> 打分/隐藏答案校验 -> Evolve -> 后续验证` 的闭环。
2. skill 内容差异会改变 blind 漏洞分析结果，不是“注不注入都一样”。
3. 对当前固件 CGI 命令注入任务，`seed` 这种“先分支、后 sink”的写法，比 `relevant` 这种“先枚举表面、后找 sink”的写法更有潜力。
4. 但目前还不能下结论说“只有用了这个 skill 才能找到漏洞”，因为 `login` case 上 `seed` 和 `relevant` 还打平。
5. 现阶段最稳妥的结论是：我们已经证明了 skill 会影响结果，也证明了反馈闭环存在；但还没有证明 skill 的必要性阈值。

## 6. 证据

### Case 与隐藏答案规则

- [firmware2-wireless-cgi-cve-2026-2529.json](D:/Code/SkillClaw/SkillClaw/benchmarks/cases/firmware2-wireless-cgi-cve-2026-2529.json)
- [firmware2-login-cgi-cve-2026-2527.json](D:/Code/SkillClaw/SkillClaw/benchmarks/cases/firmware2-login-cgi-cve-2026-2527.json)

### 打分实现与默认权重

- [score_case_output.py](D:/Code/SkillClaw/SkillClaw/evaluation/runs/score_case_output.py)
- [loader.py](D:/Code/SkillClaw/SkillClaw/evaluation/cases/loader.py)

### 汇总结果表

- [firmware_ablation_summary.csv](D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260805/firmware_ablation_summary.csv)
- [firmware_ablation_runs.csv](D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260805/firmware_ablation_runs.csv)
- [closed_loop_proof.csv](D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260805/closed_loop_proof.csv)
- [summary.md](D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260805/summary.md)

### 代表性单次 run

- [firmware2-wireless-relevant-20260806a-final-enriched.json](D:/Code/SkillClaw/SkillClaw/runtime/imports/remote_vm/firmware2-wireless-relevant-20260806a/firmware2-wireless-relevant-20260806a-final-enriched.json)
- [firmware2-login-seed-20260806a-final-enriched.json](D:/Code/SkillClaw/SkillClaw/runtime/imports/remote_vm/firmware2-login-seed-20260806a/firmware2-login-seed-20260806a-final-enriched.json)

### 对应 skill 文件

- [seed skill](D:/Code/SkillClaw/SkillClaw/skillspace/ablation_profiles/cgi_cmdi_seed_dispatch/embedded-cgi-command-injection-triage/SKILL.md)
- [relevant skill](D:/Code/SkillClaw/SkillClaw/skillspace/ablation_profiles/cgi_cmdi_relevant/embedded-cgi-command-injection-triage/SKILL.md)
