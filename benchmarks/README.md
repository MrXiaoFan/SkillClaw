# Benchmarks

`benchmarks/` 是扩展层的基准定义区，不是运行结果区。

这里回答三件事：

- 测什么
- 怎么定义
- 每个案例需要哪些确认工件

## 目录

- `cases/`
  - 每个案例一个 JSON
  - 定义目标、任务说明、验证链路、成熟度、运行配置
- `confirmations/`
  - 案例级确认工件
  - 包括输入生成脚本、确认脚本、wrapper、harness
- `skill_bundles/`
  - 面向漏洞分析任务整理的本地技能包
  - 用于指导模型分析，不用于保存运行结果

## 命名原则

- `cases/<target>-<version>-<cve>.json`
  - 统一描述一个标准案例
- `confirmations/<target>-<version>-<cve>/`
  - 存放这个案例自己的确认输入、确认脚本、确认支撑代码
- `skill_bundles/<bundle-name>/`
  - 存放按任务类型整理的分析技能

## 多环境路径

case JSON 允许继续保留原来的单一路径字段，例如：

- `target.source_root`
- `blind_workspace.agent_root`
- `blind_workspace.validator_root`

如果同一条 case 需要同时支持本地、远端 VM、共享挂载等多种环境，也可以补充：

- `<field>_candidates`
- `<field>_by_profile`

其中：

- loader 会优先选择当前机器上真实存在的路径
- 若设置环境变量 `SKILLCLAW_PATH_PROFILE`，则会优先使用 `<field>_by_profile` 中对应的命名路径

## 边界

`confirmations/` 的作用，是把“某一个具体漏洞案例”接到统一验证框架里。

这不代表系统已经具备“对未知漏洞自动生成 PoC”的通用能力。当前更准确的状态是：

- 框架层已经基本统一
- 案例接入层仍然需要按案例准备确认工件

## 与其他目录的关系

- `Skills/`
  - SkillClaw 服务端真实加载的技能目录
- `benchmarks/skill_bundles/`
  - 为基准测试维护的分析技能包

两者相关，但职责不同，不应混看。
