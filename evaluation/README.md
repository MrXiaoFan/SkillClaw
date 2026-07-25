# Evaluation

`evaluation/` 是扩展层的执行与验证主目录，专门承载“跑案例、判结果、出反馈”的可复用流程。

## 目录分工

- `runs/`
  - 案例执行入口
  - 负责单案例运行、批量运行、保存模型原始输出
- `validation/`
  - 通用验证层
  - 负责静态检查、动态确认、确认链路判定
- `postprocess/`
  - 结果整形层
  - 负责把评分、验证、注入、确认结果合并成统一 `final.json`
- `reporting/`
  - 汇总与反馈层
  - 负责当前报告、技能反馈、技能门控、研究取数
- `utils/`
  - 辅助工具层
  - 负责环境检查、盲测准备、工作区整理等辅助动作

## 主链路

`benchmark case -> runs -> validation -> postprocess -> reporting -> evolve`

## 主要入口

- `runs/run_single_case.py`
- `runs/run_case_validation.py`
- `runs/score_case_output.py`
- `validation/core.py`
- `validation/checks.py`
- `postprocess/finalize_record.py`
- `postprocess/compare_records.py`
- `reporting/current/refresh_reports.py`
- `reporting/feedback/build_feedback_bundle.py`
- `reporting/feedback/build_gate_report.py`

## reporting 子结构

- `reporting/current/`
  - 当前 runset、结果矩阵、状态汇总
- `reporting/feedback/`
  - 技能反馈 bundle、技能门控、技能反馈汇总
- `reporting/research/`
  - 面向研究结论的保守汇总
- `reporting/publication/`
  - 面向论文附表、对比清单、发布取数的导出模块

## 设计原则

- 执行、验证、汇总分层
- 案例细节尽量收敛到 `benchmarks/`
- `evaluation/` 只承载可复用流程，不承载历史实验草稿
