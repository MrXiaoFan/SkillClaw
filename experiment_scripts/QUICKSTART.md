# 最小入口清单

如果你现在只想抓住这套工程的主干，只看下面这些就够了。

## 1. 最关键的 6 个文件

### 1) `experiment_scripts/execution/run_eval_case.py`

单个实验 case 的主入口。

它负责：

- 读取 case JSON；
- 生成 prompt；
- 可选执行 preflight；
- 调 agent；
- 调 score；
- 调 validator；
- 生成 final record。

这是整条实验链路的中心文件。

### 2) `experiment_validation/runner.py`

validator 总入口。

它负责把 case 里配置的验证项真正执行起来，例如：

- `content_match`
- `source_contains`
- `command`
- `bundle_script`
- `asan_command`

如果你想看“动态验证到底怎么跑”，这里是核心入口。

### 3) `experiment_scripts/postprocess/build_result_record.py`

标准实验记录拼装器。

它负责把：

- score
- validation
- skill injection

合成统一格式的 record。

### 4) `experiment_scripts/feedback/summarize_skill_feedback.py`

把多个 final record 聚合成 skill 级反馈统计。

它是从“case 结果”走向“skill 结果”的第一步。

### 5) `experiment_scripts/feedback/build_skill_gate_report.py`

根据 skill 聚合结果给出 gate 决策，例如：

- `promote`
- `keep`
- `revise`
- `demote`
- `insufficient_evidence`

### 6) `experiment_cases/*.json`

每个 case 的真实配置入口。

这里定义：

- 目标源码路径
- prompt 所需 ground truth
- validation 配置
- artifact / command / script

如果不看 case JSON，就看不到某个漏洞案例究竟怎么接入到框架里。

## 2. 最关键的 3 条命令

### 1) 跑单个 case

```powershell
.\.venv\Scripts\python.exe experiment_scripts\run_eval_case.py <case.json> --mode skillclaw-inline --preflight
```

用途：

- 跑一个 case；
- 输出 prompt/raw/score/validation/final。

### 2) 跑一批 case

```powershell
.\.venv\Scripts\python.exe experiment_scripts\run_case_batch.py --manifest <manifest.json>
```

用途：

- 按 manifest 一次跑多个 case；
- 不再需要手写 shell 循环。

### 3) 刷新整套汇总结果

```powershell
.\.venv\Scripts\python.exe experiment_scripts\refresh_curated_reports.py --manifest experiment_records\curated_skillclaw_runset.json
```

用途：

- 刷新实验矩阵；
- 刷新 skill feedback；
- 刷新 gate report；
- 刷新 feedback bundle；
- 刷新 curated runset 汇总。

## 3. 一次运行后最值得看的输出

### 单次 case 运行

通常看这几个：

- `*-score.json`
- `*-validation.json`
- `*-final.json`

其中：

- `score.json` 看定位评分；
- `validation.json` 看验证有没有通过；
- `final.json` 看最终统一记录。

### 多 case 汇总

通常看这几个：

- `experiment_records/experiment_matrix_latest.md`
- `experiment_records/skill_feedback_latest.md`
- `experiment_records/skill_gate_report_latest.md`
- `experiment_records/skill_feedback_bundle_latest.md`

## 4. 你现在可以怎么理解整套工程

最短表达是：

`case JSON -> run_eval_case -> validator runner -> final record -> skill feedback -> gate report`

也就是说，这套工程当前已经不是“几个零散脚本”，而是一条从 case 执行到 skill 反馈的实验闭环。

## 5. 如果只给别人讲 30 秒

可以直接说：

1. `run_eval_case.py` 是单 case 统一入口；
2. `experiment_validation/runner.py` 负责执行动态/静态验证；
3. `build_result_record.py` 统一落盘；
4. `summarize_skill_feedback.py + build_skill_gate_report.py` 把 case 结果上升到 skill 级反馈。

这就是当前工程最小骨架。
