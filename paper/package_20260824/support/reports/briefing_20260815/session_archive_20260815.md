# Session Archive (2026-08-15)

## 1. 本次阶段目标

本阶段的目标不是继续大规模改代码，而是完成一个可交接节点：

1. 重新验证当前本地服务和远端 VM 是否正常；
2. 再跑一轮真实远端实验；
3. 把实验、周报、交接和当前状态整理成可直接交给 GLM 继续工作的材料。

## 2. 本阶段实际执行的检查

### 本地服务

- `http://127.0.0.1:30000/healthz` -> `{"ok":true}`
- `http://127.0.0.1:8787/status` -> 正常返回 workflow 状态
- `http://127.0.0.1:3788/` -> 返回 200

### 远端 VM

- 通过本机 SSH key 连接 `li@192.168.1.4`
- 确认远端仓库目录存在：`/home/li/skillclaw-eval/SkillClaw`
- 确认 VM 能访问本机 SkillClaw：`curl http://192.168.1.1:30000/healthz -> {"ok":true}`

## 3. 本阶段执行的真实实验

### 实验命令

在仓库根目录执行：

```powershell
.\.venv\Scripts\python.exe -m evaluation.runs.run_remote_case `
  --host 192.168.1.4 `
  --user li `
  --key-path C:\Users\Fan\.ssh\skillclaw_vm `
  --sync-repo `
  --remote-path-profile vm-li `
  --local-import-root runtime\imports\remote_vm\ablation_20260815 `
  run-auto benchmarks\cases\f453-httpd-cmdinject-formWriteFacMac.json `
  --mode blind-skillclaw-inline-guarded `
  --preflight `
  --expected-provider skillclaw `
  --skillclaw-url http://192.168.1.1:30000 `
  --skillclaw-key <本地代理 key> `
  --evolve-after-run `
  --evolve-url http://127.0.0.1:8787
```

### 新产生的 run

- `run_id`: `f453-httpd-cmdinject-formWriteFacMac-blind-skillclaw-inline-guarded-20260815-193021`

### 实验结果

- `selected_skill_names = []`
- `score = 8.0`
- `predicted_functions = ["formexeCommand"]`
- `predicted_cves = ["CVE-2018-5767"]`
- `confirmation.status = passed`
- `evolution_handoff.status = handed_off`
- `next_stage = no_candidate`

### 结果解释

这说明：

1. 当前收窄后的 live skill 没有被这轮自然检索命中；
2. 模型在没有 skill 干预的情况下，仍然稳定跑偏到 `formexeCommand / CVE-2018-5767`；
3. 当前链路已经能够把“无 skill 控制组”也作为 `__no_skill__` 反馈样本送入 Evolve；
4. 但这轮没有 candidate，因此不会触发新的发布。

关键文件：

- [`...193021-final-enriched.json`](/D:/Code/SkillClaw/SkillClaw/runtime/imports/remote_vm/ablation_20260815/f453-httpd-cmdinject-formWriteFacMac-blind-skillclaw-inline-guarded-20260815-193021/f453-httpd-cmdinject-formWriteFacMac-blind-skillclaw-inline-guarded-20260815-193021-final-enriched.json)

## 4. 本阶段确认的核心结论

### 结论 A：真实闭环已经有正例

`...191115` 这一轮已经证明：

`run -> feedback -> evolve -> candidate -> gate -> published`

不再只是概念流程，而是实际发生过一次。

### 结论 B：F453 上还没有证明 skill 必要性

目前只能证明：

- skill 会改变分析路径；
- 某些 skill 会让结果更差；
- 收窄 skill 后，自然检索可能根本选不中它。

但还不能证明：

- “只有这个 skill 才能找到 `formWriteFacMac`”

### 结论 C：后续实验重点应转向“阈值实验”

更合理的后续方向是：

1. 做一个更弱的 seed skill；
2. 做一个更退化的 target skill；
3. 比较 no-skill / weak-skill / target-skill / wrong-skill；
4. 看从哪一档开始，模型才第一次稳定靠近 `formWriteFacMac`。

## 5. 本阶段做过的清理

- 删除了 `paper/` 下的 LaTeX 构建临时文件：
  - `.aux`
  - `.bbl`
  - `.blg`
  - `.log`
  - `.out`
  - `.pdf`
  - `.spl`

保留了源码和翻译稿，不保留这类纯构建产物。

## 6. 当前仓库状态

### 当前有代码改动的主要文件

- `evaluation/postprocess/finalize_record.py`
- `evolve_server/__main__.py`
- `evolve_server/core/config.py`
- `evolve_server/engines/agent.py`
- `evolve_server/engines/workflow.py`
- `skillclaw/api_server.py`
- `skillclaw/replay_gate_worker.py`
- `paper/references.bib`
- `paper/skillclaw_confirmation_feedback_elsarticle.tex`
- `README.md`

### 本阶段新整理的材料

- `AGENT_HANDOFF.md`
- `reports/current/briefing_20260815/f453_skill_ablation_20260815.md`
- `reports/current/briefing_20260815/f453_run_table_20260815.md`
- `reports/current/briefing_20260815/f453_run_table_20260815.csv`
- `reports/current/briefing_20260815/weekly_report_20260815.md`
- `reports/current/briefing_20260815/session_archive_20260815.md`
- `reports/current/briefing_20260815/glm_handoff_20260815.md`

## 7. 当前不建议立刻做的事

1. 不建议继续堆新的泛化 firmware skill；
2. 不建议同时再扩第二个 firmware case；
3. 不建议为了追求“命中”而硬编码特定 case 规则；
4. 不建议新增更多一次性脚本，优先复用现有 `evaluation/` 入口。
