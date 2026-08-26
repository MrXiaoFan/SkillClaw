# 六案例闭环实测计划

目标：用同一套远端 blind 协议检查当前工程对 6 个 benchmark case 的真实检测能力，以及它们是否能形成可用的 skill 进化反馈。

统一协议：

- 执行环境：远端 VM
- 运行模式：`blind-skillclaw-inline-guarded`
- 核心链路：`blind prompt -> SkillClaw 注入 -> Claude 分析 -> validator -> finalize_record -> evolve handoff -> gate`
- 统一观察维度：
  - 是否命中 `file / function / root_cause / cve`
  - validator 是否 `passed`
  - `selected_skills` 是否合理
  - 是否产生 evolve candidate
  - candidate 是 `published / rejected / none`

## 当前分组

### A 组：已完成真实 blind 远端运行，可直接作为基线

| case | 当前状态 | 最近 blind 结果 | 下一步 |
| --- | --- | --- | --- |
| `giflib-5.1.2 / CVE-2016-3977` | `current / publication-ready` | `8/10`，`file/function/root_cause` 对，`CVE` 错 | 保留为强基线；后续只做对照实验 |
| `libxml2-2.9.4 / CVE-2017-8872` | `confirmed / current-confirmation` | `8/10`，`file/function/root_cause` 对，`CVE` 错 | 观察 skill 是否能减少 CVE 误判 |
| `tcpdump-4.9.1 / CVE-2018-14469` | `confirmed / current-confirmation` | `2/10`，定位失败 | 作为负例，重点看错配 skill 和 evolve gate |

### B 组：已有 case 与 validator，但还没纳入本轮统一 blind runset

| case | 当前状态 | 目标 |
| --- | --- | --- |
| `tcpdump-4.9.1 / CVE-2017-13031` | `confirmed / current-confirmation` | 补一条真实远端 blind run，看是否比 2018-14469 更容易定位 |
| `libarchive-3.8.0 / CVE-2025-60753` | `confirmed / publication-ready` | 补一条真实远端 blind run，看非崩溃型 case 的检测与 evolve 行为 |
| `exiv2-0.26 / CVE-2017-17725` | `confirmed / candidate` | 先确认当前 blind 协议下是否能稳定跑完，再决定是否进入论文主结果 |

## 执行顺序

1. `libarchive-3.8.0 / CVE-2025-60753`
2. `tcpdump-4.9.1 / CVE-2017-13031`
3. `exiv2-0.26 / CVE-2017-17725`

理由：

- `libarchive` 已经是 `publication-ready`，最适合先补齐论文 runset
- `tcpdump-2017-13031` 与现有 `tcpdump-2018-14469` 可形成同家族对照
- `exiv2` 风险最大，放最后，避免拖慢整轮闭环验证

## 每个 case 的完成判据

一个 case 只有在同时满足以下条件时，才算真正纳入“闭环已实测”：

1. 远端 blind run 完成并生成 `final-enriched.json`
2. validator `status = passed`
3. local final record 中能看到 `selected_skills`
4. evolve side 能看到该 session 被消费
5. candidate 结果明确为三种之一：
   - `published`
   - `rejected`
   - `none`

## 本轮结束后要产出的结果

1. 六案例总表：
   - 哪些 case 能定位漏洞
   - 哪些只能跑通确认链路
   - 哪些完全跑偏
2. skill 总表：
   - 哪些 skill 高频错配
   - 哪些 skill 有局部帮助
   - 哪些 skill 值得修订
3. 论文结论所需最小事实：
   - 当前工程是否真的形成检测-验证-进化闭环
   - 闭环是否已经产生正向 skill 改进，还是仍以“拒绝错误更新”为主

