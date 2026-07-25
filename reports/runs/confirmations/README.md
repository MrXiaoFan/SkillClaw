# Confirmation Run Records

`reports/runs/confirmations/` 只保留当前仍作为主结果引用的确认型运行目录。

## 每个子目录建议保留的文件

核心文件：

- `manifest.json`
- `run_index.json`
- `final.json` 或 `final-enriched.json`

按需保留：

- `validation.json`
- `agent.json`
- `compare.json`
- `compare.md`
- `baseline-final.json`
- `injection-history.jsonl`

如果某个目录里同时出现两份含义重复的对比结果，只保留信息更完整的那一份。

## 不应长期停留在这里的内容

下面这些不应继续堆在当前区：

- 早期试跑
- 被更新结果替换掉的旧版本
- 一次性 probe
- 临时草稿
- 重复 compare 产物

这些统一移动到：

- `../../archive/legacy_runs/`

## 关于路径

部分 `manifest.json`、`run_index.json`、`final*.json` 内部仍可能保留历史执行路径，
例如 `/home/li/skillclaw-eval/...`。

这属于运行证据的一部分，不代表当前仓库结构仍依赖旧目录。

## 审计命令

```powershell
.\.venv\Scripts\python.exe -m evaluation.utils.audit_run_layout
```

