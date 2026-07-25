# Extension Architecture Summary

这是一份面向汇报和快速对齐的简版说明，只回答三个问题：

1. 我们在原生 SkillClaw 之外新增了什么
2. 当前正式结构是什么
3. 一次完整闭环现在怎么走

---

## 1. 扩展层到底补了什么

原生 SkillClaw 负责：

- 代理请求
- 技能注入
- 会话采集
- 技能演化

扩展层负责：

- 定义漏洞分析基准案例
- 运行案例
- 做静态或动态确认
- 生成统一结果记录
- 把结果整理成可被 `evolve_server` 消费的反馈

一句话定位：

**我们把 SkillClaw 从“会注入技能、会演化技能”，扩展成“能围绕漏洞分析任务做执行、确认、反馈闭环”的系统。**

---

## 2. 当前正式结构

```text
原生层
├─ skillclaw/         代理、技能注入、会话管理
└─ evolve_server/     技能反馈消费与演化

扩展层
├─ benchmarks/        基准案例、确认适配器、技能包
├─ evaluation/        执行、验证、后处理、汇总
├─ reports/           当前结果、证据、归档、论文取数
├─ docs/              结构说明、计划、周报、运维笔记
├─ runtime/           本地运行期输出
└─ scripts/           安装、运维、演示辅助
```

---

## 3. 当前主闭环

```text
benchmark case
  -> run_single_case
  -> score_case_output
  -> run_case_validation
  -> finalize_record
  -> build_feedback_bundle
  -> evolve_server
```

对应含义：

1. `benchmarks/cases/*.json`
   - 定义要测什么
2. `evaluation/runs/`
   - 真实运行模型分析
3. `evaluation/validation/`
   - 判断结果是否正确、是否形成确认
4. `evaluation/postprocess/`
   - 整理成统一 `final.json`
5. `evaluation/reporting/feedback/`
   - 生成技能反馈 bundle
6. `evolve_server/`
   - 消费反馈，进入技能演化链路

---

## 4. 当前状态

已经完成：

- 基准案例结构化
- 执行 / 验证 / 汇总主链路成形
- `validator -> feedback bundle -> evolve_server` 已接通
- 工程结构已从 `experiment_*` 散乱脚本，收敛成正式模块

还没完全解决：

- 新案例接入仍依赖案例级确认适配器
- “skill 被选中”不等于“skill 真起作用”，还缺归因层
- 对未知新目标的泛化能力还需要更多外部案例验证

---

## 5. 现在最稳妥的说法

这套扩展工程更适合描述为：

**一个挂接在 SkillClaw 之上的、面向漏洞分析实验的 confirmation-aware 执行与反馈框架。**
