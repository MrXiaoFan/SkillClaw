# Extension Architecture

这份文档描述的是原生 SkillClaw 之外，本仓库新增的扩展工程结构。

目标不是追溯所有历史草稿，而是说明三件事：

1. 当前正式结构是什么
2. 每一层分别负责什么
3. 一次完整闭环怎样走完

---

## 1. 总体分层

当前仓库可以分成两大部分：

### A. 原生 SkillClaw 层

- `skillclaw/`
  - 代理入口
  - 技能注入
  - 会话管理
- `evolve_server/`
  - 技能反馈消费
  - 技能演化与发布

### B. 扩展评测层

- `benchmarks/`
  - 测什么
- `evaluation/`
  - 怎么跑、怎么验
- `reports/`
  - 留下什么结果
- `docs/`
  - 怎么让人看懂
- `runtime/`
  - 本地运行时输出
- `scripts/`
  - 安装、运维、演示辅助

---

## 2. 推荐目录树

```text
SkillClaw/
├─ skillclaw/                         [原生]
│  ├─ api_server.py                   代理入口、技能注入、会话回流
│  ├─ skill_manager.py                技能检索、inline 注入、技能元数据
│  └─ ...
├─ evolve_server/                     [原生 + 扩展接线]
│  ├─ core/config.py                  演化服务配置
│  ├─ engines/workflow.py             周期消费会话与反馈
│  ├─ pipeline/execution.py           演化执行
│  ├─ pipeline/summarizer.py          演化摘要与反馈整理
│  └─ ...
├─ benchmarks/                        [定制扩展]
│  ├─ cases/                          标准案例定义
│  ├─ confirmations/                  案例级确认适配器
│  └─ skill_bundles/                  本地漏洞分析技能包
├─ evaluation/                        [定制扩展]
│  ├─ runs/                           执行入口
│  ├─ validation/                     通用验证层
│  ├─ postprocess/                    结果整形层
│  ├─ reporting/
│  │  ├─ current/                     当前报告
│  │  ├─ feedback/                    技能反馈与 gate
│  │  ├─ research/                    研究结论汇总
│  │  └─ publication/                 论文取数与导出
│  └─ utils/                          辅助工具
├─ reports/                           [定制扩展]
│  ├─ current/                        当前主结果
│  ├─ runs/confirmations/             当前有效确认运行
│  ├─ evidence/cases/                 关键证据
│  ├─ publication/                    论文材料
│  └─ archive/legacy_runs/            历史归档
├─ docs/                              [定制扩展]
│  ├─ reference/
│  ├─ plans/
│  ├─ weekly/
│  └─ ops/
├─ runtime/                           [定制扩展]
│  ├─ evolve/
│  ├─ logs/
│  ├─ records/
│  ├─ results/
│  └─ tmp/
└─ scripts/                           [定制扩展]
   ├─ install/
   ├─ ops/
   └─ demos/
```

---

## 3. 各层职责

### 3.1 `benchmarks/`

这一层回答：`要测什么`

负责：

- 定义案例
- 描述目标软件、漏洞、期望输出
- 提供案例级确认适配器

不负责：

- 运行 agent
- 统一评分
- 统一汇总

### 3.2 `evaluation/`

这一层回答：`怎么跑、怎么判`

负责：

- 调起 agent
- 保存原始输出
- 评分
- 调 validator 做静态 / 动态确认
- 合并成统一 final record
- 生成反馈输入

### 3.3 `reports/`

这一层回答：`最后保留什么结果`

负责：

- 保存当前主结果
- 保存关键运行目录
- 保存关键证据
- 保存论文取数材料
- 归档历史运行

### 3.4 `docs/`

这一层回答：`怎么让人理解这个工程`

负责：

- 结构说明
- 计划
- 周报
- 运维记录

### 3.5 `runtime/`

这一层回答：`本地临时输出放哪里`

负责：

- 本地日志
- 临时结果
- 运行期缓存

原则上不作为正式研究材料区。

---

## 4. 主工作流

### 4.1 当前正式闭环

```text
benchmarks/cases/*.json
        ->
evaluation/runs/run_single_case.py
        ->
agent 原始输出
        ->
evaluation/validation/*
        ->
evaluation/postprocess/finalize_record.py
        ->
reports/runs/confirmations/*/final.json
        ->
evaluation/reporting/feedback/build_feedback_bundle.py
        ->
reports/current/skill_feedback_bundle.json
        ->
evolve_server 消费反馈
```

### 4.2 每一步的意义

1. `case`
   - 定义这次要测什么
2. `run`
   - 真实执行 agent 分析
3. `validation`
   - 判断分析是否正确、是否确认成功
4. `final record`
   - 把散乱结果整理成统一结构
5. `feedback bundle`
   - 从案例结果提取技能反馈
6. `evolve`
   - 让技能系统消费这些反馈

---

## 5. 当前边界

### 已经具备

- 基准案例驱动的漏洞分析评测
- 静态 / 动态确认
- 统一 final record
- 技能反馈 bundle
- evolve server 消费 validator 支持的反馈

### 还没有完全解决

- 新案例接入仍需案例级确认适配器
- “skill 被选中”不等于“skill 真起作用”，缺归因层
- 对未知新目标的泛化能力还未被充分验证
- 盲测链路与确认链路仍需更严格隔离

---

## 6. 一句话定位

当前这套扩展工程更准确的定位是：

**挂接在 SkillClaw 之上的、面向漏洞分析实验的 confirmation-aware 执行与反馈框架。**
