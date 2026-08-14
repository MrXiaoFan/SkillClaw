# 01 Runtime Handoff and Service Bootstrap

更新时间：2026-08-12

## 1. 这份文件的用途

这份文件给后续模型直接接手用，目标是解决三个问题：

1. 本地三个服务怎么拉起；
2. 现在工程到底通到了哪一步；
3. 后续继续做真实远端实验时，先看什么、先验什么。

配套必读材料：

1. `docs/handoff/20260811/01_research_and_development_state.md`
2. `docs/handoff/20260811/03_engineering_status_tests_and_next_plan.md`
3. `reports/current/briefing_20260811/firmware_wireless_real_runs_20260811.json`
4. `reports/current/briefing_20260811/firmware_wireless_real_runs_20260811.md`

---

## 2. 本地三个终端的启动命令

以下命令都在 Windows PowerShell 下执行，工作目录统一是：

`D:\Code\SkillClaw\SkillClaw`

### 终端 1：SkillClaw 代理

```powershell
cd D:\Code\SkillClaw\SkillClaw
(Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned) ; (& .\.venv\Scripts\Activate.ps1)
.\.venv\Scripts\python.exe -m skillclaw.cli start --port 30000
```

### 终端 2：Evolve Server

说明：

- 当前正确模式是 `validated`
- 当前共享根目录是 `skillspace\share`
- 当前反馈 bundle 路径是 `runtime\evolve\skill_feedback_bundle.json`
- 如果重启后 `/status` 里看不到 `deepseek-v4-pro` 和 `https://api.deepseek.com`，说明这一个终端缺少上游环境变量，需要由人工补上环境变量后再启动

```powershell
cd D:\Code\SkillClaw\SkillClaw
(Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned) ; (& .\.venv\Scripts\Activate.ps1)
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
(Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned) ; (& .\.venv\Scripts\Activate.ps1)
.\.venv\Scripts\python.exe -m skillclaw.cli dashboard serve `
  --host 127.0.0.1 `
  --port 3788 `
  --sharing-local-root D:\Code\SkillClaw\SkillClaw\skillspace\share `
  --sharing-group-id default `
  --sharing-user-alias Fan `
  --evolve-server-url http://127.0.0.1:8787
```

---

## 3. 拉起后的核验命令

### 3.1 本地核验

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:30000/healthz
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8787/status
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:3788/
```

正确现象：

- `30000/healthz` 返回 `{"ok":true}`
- `8787/status` 返回 JSON，不是 404
- `3788/` 返回 200 和 dashboard HTML

注意：

- `Evolve Server` 没有 `/healthz`
- 不要再用 `http://127.0.0.1:8787/healthz` 判断它是否存活

### 3.2 端口冲突排查

如果某个服务起不来，先查监听进程：

```powershell
Get-NetTCPConnection -LocalPort 30000,8787,3788 -State Listen | Select-Object LocalPort,OwningProcess
```

如果确认是旧进程占端口，再手动停：

```powershell
Stop-Process -Id <PID>
```

---

## 4. 当前本地配置要点

当前配置文件：

- `C:\Users\Fan\.skillclaw\config.yaml`

本次 handoff 已核对到的关键配置：

- `skills.dir = D:\Code\SkillClaw\SkillClaw\skillspace\live`
- `sharing.local_root = D:\Code\SkillClaw\SkillClaw\skillspace\share`
- `sharing.group_id = default`
- `skills.injection_mode = inline`
- `skills.retrieval_mode = template`
- `skills.top_k = 3`
- `sharing.skill_reload_mode = off`
- `validation.mode = replay`
- `dashboard.evolve_server_url = http://127.0.0.1:8787`

解释：

1. 真正参与下一轮注入的是 `skillspace/live/`
2. 候选 skill、gate 结果、运行收据主要进 `skillspace/share/default/`
3. `skill_reload_mode = off`，所以不要假设 live skill 改完会自动热加载

---

## 5. 远端 VM 真实实验前的前置检查

### 5.1 当前已知 VM 信息

- VM 用户：`li`
- VM 地址：`192.168.1.4`
- VM 上 Claude 通过 `~/.claude/settings.json` 指向宿主机 SkillClaw 代理

### 5.2 当前已知宿主机地址

本次会话中，宿主机地址是：

- `10.12.189.47`

但这个地址可能在重启或换网后变化，所以每次真实远端实验前，都要重新在宿主机执行：

```powershell
ipconfig
```

然后核对 VM 里的 `~/.claude/settings.json` 是否仍然指向正确宿主机地址。

### 5.3 VM 侧核验命令

在 VM 上执行：

```bash
hostname
whoami
ip a
cat ~/.claude/settings.json
curl http://192.168.1.1:30000/healthz
curl http://10.12.189.47:30000/healthz
```

正确现象：

- VM 能访问宿主机 SkillClaw 代理
- 至少有一个地址返回 `{"ok":true}`

如果宿主机地址变了，就要更新 VM 的 `~/.claude/settings.json`。

---

## 6. 当前最重要的实验事实

当前最可信的一组 firmware 真实远端证据，是这四个 run：

1. `runtime/imports/remote_vm/firmware2-wireless-none-20260812c/`
2. `runtime/imports/remote_vm/firmware2-wireless-seed-20260812a/`
3. `runtime/imports/remote_vm/firmware2-wireless-wrong-20260812h/`
4. `runtime/imports/remote_vm/firmware2-wireless-live-20260812i/`

这四组目前共同支持的结论是：

1. 远端 `Claude -> SkillClaw -> Evolve -> replay gate` 链路已经真实闭环；
2. `selected_skill_names`、`skill_relevance`、`feedback`、`evolution_handoff` 已经能稳定落到最终记录里；
3. `wrong skill` 和 `seed skill` 都可能进入 candidate 阶段；
4. 但目前还没有任何一次 candidate 被证明优于 baseline 并发布到 live skill。

换句话说：

- 工程闭环是真的；
- skill 增益还没有被证明；
- skill 必要性也还没有被证明。

---

## 7. 当前服务实际状态

本次 handoff 写入前，已现场核验：

### SkillClaw

- `http://127.0.0.1:30000/healthz`
- 返回：`{"ok":true}`

### Evolve

- `http://127.0.0.1:8787/status`
- 返回关键字段：
  - `engine = workflow`
  - `running = true`
  - `publish_mode = validated`
  - `llm_model = deepseek-v4-pro`
  - `llm_base_url = https://api.deepseek.com`
  - `feedback_bundle_path = runtime\\evolve\\skill_feedback_bundle.json`
  - `closed_sessions_waiting_feedback = 0`
  - `stale_closed_sessions_without_feedback = 26`

### Dashboard

- `http://127.0.0.1:3788/`
- 返回：`200 OK`

解释：

- 三个服务在写这份 handoff 时是活着的
- 但 Evolve 里仍然有 `26` 个历史 stale session
- 这不是当前四组核心 run 失败的证据，而是历史积累状态

---

## 8. 当前工程状态的简短判断

### 已经成立的

1. SkillClaw 本地代理可用
2. Evolve validated 模式可用
3. Dashboard 可用
4. 远端 VM 真实 blind run 可跑
5. 结果能 finalize、handoff、consume、gate

### 还没成立的

1. 还没有“被接受并发布进 live skill”的正例证据
2. 还没有“下一轮真的因为 skill 进化而变好”的正例证据
3. 还没有“没有这个 skill 就找不到，但有这个 skill 才能找到”的严格必要性证据

---

## 9. 当前目录里哪些是主证据，哪些是历史噪音

### 应保留并优先阅读

- `docs/handoff/20260811/`
- `docs/handoff/20260812/`
- `reports/current/briefing_20260811/`
- `runtime/imports/remote_vm/firmware2-wireless-none-20260812c/`
- `runtime/imports/remote_vm/firmware2-wireless-seed-20260812a/`
- `runtime/imports/remote_vm/firmware2-wireless-wrong-20260812h/`
- `runtime/imports/remote_vm/firmware2-wireless-live-20260812i/`

### 已经做过减法

已删除：

- `runtime/tmp/cgi_cmdi_seed_dispatch.inline.json`
- `runtime/tmp/skill_payloads/`

已归档：

- `runtime/archive/remote_vm/wireless_legacy_unreferenced_20260812/`

其中放的是一批当前没有汇总材料引用的旧 wireless run。

---

## 10. 当前 git 状态的意义

当前工作区不是干净树。

特征：

- `evaluation/`
- `evolve_server/`
- `skillclaw/`
- `reports/current/`
- `tests/`

都有大量已修改文件；

另外这些目录大多还是未跟踪状态：

- `docs/handoff/`
- `paper/`
- `evaluation/confirmation/`
- `reports/current/briefing_20260805/`
- `reports/current/briefing_20260811/`
- `skillspace/ablation_profiles/`

这意味着：

1. 后续模型不要假设当前内容已经全部提交到 git；
2. 后续模型应以“本地工作区真实状态”为准，不要只看远端仓库；
3. 在继续清理前，优先确认哪些文件已经是主证据，哪些只是历史材料。

---

## 11. 后续模型接手后第一步该做什么

推荐顺序：

1. 先核验三个本地服务是否都活着
2. 再核验 VM 是否还能访问宿主机 SkillClaw 代理
3. 读取四组 firmware 核心 run 的 `final-enriched.json`
4. 读取 `reports/current/briefing_20260811/firmware_wireless_real_runs_20260811.json`
5. 明确本轮目标是：
   - 继续做“skill 是否真的有用”的真实实验
   - 而不是再扩张新脚本和新目录

---

## 12. 禁止误判的几条规则

1. 不要把“生成了 candidate”当成成功
2. 不要把“selected_skill_names 有值”当成 skill 一定有效
3. 不要把“wrong skill 也生成了 candidate”误读成链路坏了
4. 不要把“Evolve 有 stale session”误读成当前四组 run 没有 handoff
5. 不要只做本地单元测试就声称“实验已验证”
6. 本项目里说“测试”，默认优先指真实实验测试，尤其是远端 VM blind run

---

## 13. 当前最短接手路径

如果别的模型只想用最短路径接上：

1. 读本文件
2. 启动三个本地服务
3. 核验：
   - `30000/healthz`
   - `8787/status`
   - `3788/`
4. 去看四组核心 run：
   - none
   - seed
   - wrong
   - live
5. 再决定下一轮真实实验是：
   - 先继续压低 skill 干扰
   - 还是直接追一个能通过 gate 的 candidate

