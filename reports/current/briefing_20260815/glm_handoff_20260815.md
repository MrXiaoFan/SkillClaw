# GLM Handoff (2026-08-15)

## 一、先看什么

GLM 接手后，建议按这个顺序读：

1. [reports/current/briefing_20260815/f453_skill_ablation_20260815.md](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260815/f453_skill_ablation_20260815.md)
2. [reports/current/briefing_20260815/f453_run_table_20260815.md](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260815/f453_run_table_20260815.md)
3. [reports/current/briefing_20260815/session_archive_20260815.md](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260815/session_archive_20260815.md)
4. [runtime/imports/remote_vm/ablation_20260815/f453-httpd-cmdinject-formWriteFacMac-blind-skillclaw-inline-guarded-20260815-191115/f453-httpd-cmdinject-formWriteFacMac-blind-skillclaw-inline-guarded-20260815-191115-final-enriched.json](/D:/Code/SkillClaw/SkillClaw/runtime/imports/remote_vm/ablation_20260815/f453-httpd-cmdinject-formWriteFacMac-blind-skillclaw-inline-guarded-20260815-191115/f453-httpd-cmdinject-formWriteFacMac-blind-skillclaw-inline-guarded-20260815-191115-final-enriched.json)
5. [runtime/imports/remote_vm/ablation_20260815/f453-httpd-cmdinject-formWriteFacMac-blind-skillclaw-inline-guarded-20260815-193021/f453-httpd-cmdinject-formWriteFacMac-blind-skillclaw-inline-guarded-20260815-193021-final-enriched.json](/D:/Code/SkillClaw/SkillClaw/runtime/imports/remote_vm/ablation_20260815/f453-httpd-cmdinject-formWriteFacMac-blind-skillclaw-inline-guarded-20260815-193021/f453-httpd-cmdinject-formWriteFacMac-blind-skillclaw-inline-guarded-20260815-193021-final-enriched.json)

## 二、当前阶段结论

### 1. 已确认的

- SkillClaw 服务端注入 skill 的链路是“真生效”的。
- `run -> feedback -> evolve -> candidate -> gate -> published` 这条闭环至少已有一条真实正例（`...191115`）。
- F453 上，当前模型会稳定被 `formexeCommand / CVE-2018-5767` 吸走。
- 当前 live skill 收窄后，自然检索这轮没有选中任何 skill（`...193021`）。

### 2. 还没有确认的

- 还没有证明“某个 skill 是找到 `formWriteFacMac` 的必要条件”。
- 还没有证明“发布后的 live skill 已经对后续 blind run 带来正向收益”。

## 三、当前应该怎么继续

优先级从高到低：

1. **继续做 F453 必要性实验，不要扩新 case。**
2. **做弱 skill / 退化 skill / 正确 target skill / wrong skill 的四组对照。**
3. **观察哪一档 skill 内容第一次让模型靠近 `formWriteFacMac`。**
4. **只有这条线稳定后，再考虑扩到第二个 firmware case。**

## 四、建议的下一轮实验

### 目标

回答这个问题：

> 当前 F453 case 上，到底需要多强、什么内容的 skill，模型才会第一次不再跑偏到 `formexeCommand`？

### 建议实验组

1. `no-skill`
2. `wrong-skill`
3. `weak-target-skill`
4. `strong-target-skill`

其中 `weak-target-skill` 不要重新发明脚本，直接从 `embedded-cgi-command-injection-triage` 精简出更弱版本即可。

## 五、三个终端手动启动命令

### 终端 1：SkillClaw

```powershell
cd D:\Code\SkillClaw\SkillClaw
.\.venv\Scripts\python.exe -m skillclaw.cli start --port 30000
```

### 终端 2：Evolve Server

```powershell
cd D:\Code\SkillClaw\SkillClaw
.\.venv\Scripts\python.exe -m evolve_server `
  --engine workflow `
  --local-root .\skillspace\share `
  --group-id default `
  --port 8787 `
  --publish-mode validated `
  --feedback-bundle runtime\evolve\skill_feedback_bundle.json
```

### 终端 3：Dashboard

```powershell
cd D:\Code\SkillClaw\SkillClaw
.\.venv\Scripts\python.exe -m skillclaw.cli dashboard serve `
  --host 127.0.0.1 `
  --port 3788 `
  --sharing-local-root D:\Code\SkillClaw\SkillClaw\skillspace\share `
  --sharing-group-id default `
  --sharing-user-alias Fan `
  --evolve-server-url http://127.0.0.1:8787
```

说明：

- 不要把密钥写进 handoff 文件；
- 当前上游模型地址与密钥都在本机 SkillClaw 配置里；
- 若重启终端后配置丢失，先检查 `C:\Users\Fan\.skillclaw\config.yaml`。

## 六、不要做什么

1. 不要继续增加大量一次性脚本；
2. 不要把新的临时实验写成分叉路径很多的工程入口；
3. 不要把 case-specific 规则硬塞进检索代码；
4. 不要覆盖已有 run 结果目录；
5. 不要在 handoff 里写 API key、token、密码。
