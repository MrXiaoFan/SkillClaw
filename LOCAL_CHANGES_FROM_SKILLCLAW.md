# Local Changes From SkillClaw

这份说明只回答四个问题：

1. 相比原生 SkillClaw，我们额外开发了什么
2. 这些扩展现在放在哪里
3. 当前主流程是什么
4. 当前能力边界在哪里

## 1. 额外开发了什么

原生 SkillClaw 主要提供两层能力：

- `skillclaw/`
  - 本地代理
  - 技能注入
  - 会话采集
- `evolve_server/`
  - 技能演化
  - 反馈消费
  - 技能发布

在此基础上，本仓库新增了一套面向漏洞分析实验的扩展层，分成三块。

### 1.1 基准案例层

目录：`benchmarks/`

作用：

- 定义可重复执行的漏洞分析案例
- 保存案例级确认适配器
- 保存面向漏洞分析任务的本地技能包

### 1.2 执行与验证层

目录：`evaluation/`

作用：

- 运行单案例或批量案例
- 对模型输出评分
- 执行静态或动态确认
- 合并成统一 `final.json`
- 产出技能反馈与技能门控输入

### 1.3 结果与说明层

目录：

- `reports/`
- `docs/`
- `runtime/`
- `scripts/`

作用：

- 统一保存当前结果、证据和归档
- 保存工程说明、计划、周报、运维记录
- 收纳本地运行期输出
- 保留安装、运维、演示辅助脚本

## 2. 这些扩展现在放在哪里

当前正式结构只认下面几块：

- `benchmarks/`
- `evaluation/`
- `reports/`
- `docs/`
- `runtime/`
- `scripts/`

已经退出正式结构的旧命名包括：

- `experiment_cases/`
- `experiment_scripts/`
- `experiment_validation/`
- `experiment_records/`

这些旧目录名现在只应出现在：

- 迁移说明
- 历史归档
- 已冻结的运行证据

不应再作为活跃工程结构继续扩展。

## 3. 当前主流程是什么

当前主链路是：

`benchmark case -> runs -> validation -> postprocess -> reporting -> evolve`

对应入口：

- 案例定义：`benchmarks/cases/*.json`
- 执行入口：`evaluation/runs/`
- 验证入口：`evaluation/validation/`
- 结果整形：`evaluation/postprocess/`
- 汇总与反馈：`evaluation/reporting/`
- 技能演化消费：`evolve_server/`

最小闭环可以理解为：

1. 从 `benchmarks/cases/` 读取案例
2. 运行模型分析，得到原始输出
3. 对输出做评分与确认
4. 合并成 `final.json`
5. 生成技能反馈 bundle 和技能门控报告
6. 由 `evolve_server` 消费这些反馈

## 4. 当前能力边界

当前已经具备：

- 案例级漏洞分析评测
- 静态 / 动态确认
- 统一 `final.json`
- 技能反馈 bundle
- 技能门控报告
- `evolve_server` 读取 validator 支持的反馈输入

但它还不是：

`对未知漏洞自动生成 PoC 并自动完成技能演化的通用系统`

更准确的定位是：

`挂接在 SkillClaw 之上的、面向漏洞分析实验的 confirmation-aware 执行与反馈框架`

当前仍然存在的边界：

- 新案例接入仍需要案例级适配器
- “skill 被选中”不等于“skill 真正起作用”，还缺更强的归因层
- 对未知新目标的泛化能力，还需要更多真实案例验证

