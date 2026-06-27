# giflib 5.1.2 CVE-2016-3977 对照实验记录

## 实验目标

本次实验用于补充第三个轻量级 Linux C/C++ 漏洞定位 case，目标是检验 SkillClaw inline skill/catalog 环境与 DeepSeek 直连环境在同一远端 VM、同一源码目录、同一任务提示下的漏洞定位差异。目标软件为 giflib 5.1.2，分析对象为 `util/gif2rgb`，ground truth 为 `CVE-2016-3977`。

官方漏洞描述要点是 giflib 的 `gif2rgb` 在处理 GIF 背景色索引时存在越界读取风险。实验 ground truth 将漏洞位置标注为 `util/gif2rgb.c` 的 `DumpScreen2RGB` 相关路径：`GifFile->SBackGroundColor` 被写入 `ScreenBuffer[0][i]`，后续作为 `ColorMap->Colors[GifRow[j]]` 的下标使用，而缺少与 `ColorMap->ColorCount` 的边界校验。

## 环境与输入

远端 VM 工作目录为 `/home/li/skillclaw-eval`。本地实验框架包 `skillclaw-experiment-framework-20260627-210904.zip` 已同步到远端并解压。giflib 源码通过 GitHub mirror 的 `5.1.2` tag 获取，因原始 `Makefile.unx` 在当前环境下无法直接完成子目录构建，最终使用显式 `gcc` 命令编译出 `util/gif2rgb`。preflight 检查确认源码目录、目标二进制、ground truth 文件、Claude Code provider 均符合预期。

两组实验均使用 `experiment_scripts/run_eval_case.py` 运行，case 文件为 `experiment_cases/giflib-5.1.2-cve-2016-3977.json`。SkillClaw 组 provider 为 `skillclaw`，SkillClaw 服务端 `/v1/skills` 返回 35 个 skill；Direct 组 provider 为 `deepseek`，不经过 SkillClaw。

## 评分规则

评分由 `experiment_scripts/score_agent_output.py` 和 case ground truth 自动计算，总分 10 分。评分维度包括是否命中 CVE 编号、目标文件、关键函数、核心证据和根因描述。validator 同时执行 `content_match`、`source_contains` 和 `command` 检查，其中 `content_match` 检查 Agent 最终 JSON 输出是否覆盖 CVE、文件、函数、证据模式；`source_contains` 确认 ground truth 源码位置真实存在；`command` 确认 `util/gif2rgb` 二进制可运行。当前 `asan_command` 仍为占位禁用，尚未进行真实崩溃触发验证。

## 实验结果

SkillClaw 组运行 ID 为 `giflib-skillclaw-guarded-20260627`，模式为 `skillclaw-inline-guarded`，最终得分 `10/10`。模型正确输出 `CVE-2016-3977`，命中 `util/gif2rgb.c`、`DumpScreen2RGB`、`GifFile->SBackGroundColor`、`ScreenBuffer[0][i]` 和 `ColorMap->Colors[GifRow[j]]`，并解释了背景色索引未校验导致 color map 越界读取的根因。后处理从 SkillClaw 服务端 `records/conversations.jsonl` 抽取到本次 session `26601cab-9351-4301-a0bc-24a5a5347524` 的 inline injection 记录，确认注入 skill 为 `vuln-hunting`、`source-parser-state-machine-oob` 和 `elf-cwe120-firmware-triage`，`skill_relevance` 被评估为 `has_task_relevant_skill`。

DeepSeek 直连组运行 ID 为 `giflib-direct-guarded-20260627`，模式为 `direct-deepseek-guarded`，最终得分 `8/10`。模型同样定位到 `util/gif2rgb.c` 和 `DumpScreen2RGB`，并完整覆盖 `GifFile->SBackGroundColor`、`ScreenBuffer[0][i]`、`ColorMap->Colors[GifRow[j]]`、`ColorMap->ColorCount` 等关键证据；但 CVE 编号输出为 `CVE-2016-3177`，未命中正确的 `CVE-2016-3977`，因此扣分。

## 初步结论

本 case 中，SkillClaw 组优于 Direct 组的主要原因不是源码定位能力，而是 CVE identity/calibration 更准确。Direct 组已经具备很强的源码级定位和根因分析能力，但在漏洞编号上出现近似错误。结合注入记录看，本次 SkillClaw 确实选择了与状态机越界和漏洞狩猎相关的 task skill，但仍不能单独证明提升来自某一个 skill；更稳妥的论文表述是：SkillClaw 不应被宣称为普遍提升漏洞定位能力，而更适合作为任务稳定化、检索增强和漏洞身份校准机制来研究；源码定位、CVE 校准、skill 归因和动态触发验证应拆成不同评价维度。

相关原始产物保存在 `experiment_records/remote_runs/giflib-20260627/`。跨实验汇总已更新到 `experiment_records/research_claims_20260627.md` 和 `experiment_records/research_claims_20260627.json`。
