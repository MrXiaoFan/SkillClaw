# AGENT HANDOFF

Last updated: 2026-08-04

这是一份给后续 Agent 的单文件接班说明。目标是：即使聊天历史丢失、上下文被压缩、机器重启，只要先读完本文件，就能继续推进当前工程和实验。

---

## 1. 当前项目一句话定位

本项目是在原生 SkillClaw 之上扩展的一套**面向漏洞分析任务的 skill 演化实验框架**。  
它的核心不是单纯“让模型答对某个 CVE”，而是：

1. 让 SkillClaw 在真实漏洞分析任务中选择并注入 skill；
2. 让任务结果进入**确认链路**（confirmation）；
3. 把确认后的结果整理成可被 `evolve_server` 消费的反馈；
4. 形成 skill 迭代/发布前的**回放门禁**（replay gate）闭环。

---

## 2. 学术目标与工程目标

### 2.1 学术目标

当前论文/研究主线是：

- 面向漏洞分析场景，构建一个**skill 驱动的 Agent 框架**；
- 不只看最终答案是否正确，还要把任务执行、确认结果、技能反馈接到同一条链路里；
- 研究“任务执行结果如何回流为 skill 演化信号”。

当前不要过度宣称的点：

- 还**不能严格证明**“被选中的 skill 一定真正发挥了作用”；
- 对**未知新漏洞/新固件**的泛化能力仍需更多外部案例验证；
- 目前 confirmation 仍然部分依赖 case 级适配信息，尚未达到完全通用。

### 2.2 工程目标

当前工程目标是：

1. 跑通本地 SkillClaw + Evolve Server + Dashboard；
2. 跑通远端 VM 上的 blind case；
3. 让远端结果回传本地，进入 postprocess / reporting / evolve；
4. 持续整理命名、模块边界、目录结构，减少“experiment_*”式散乱痕迹；
5. 最终支持后续接入更多外部漏洞数据集和固件环境。

---

## 3. 原生 SkillClaw vs 扩展层

### 3.1 原生 SkillClaw 主要负责

- LLM 代理与转发
- skills 注入
- 会话采集
- sharing / evolve 基础链路
- dashboard 基础能力

主要目录：

- `skillclaw/`
- `evolve_server/`

### 3.2 扩展层主要负责

- benchmark case 定义
- blind prompt 生成
- confirmation 执行
- 结果整理与评分
- skill 反馈 bundle 生成
- 远端 VM 执行与导入
- 面向论文的结果汇总与证据沉淀

主要目录：

- `benchmarks/`
- `evaluation/`
- `reports/`
- `docs/`
- `runtime/`

---

## 4. 术语约定（当前正在收口）

这是后续开发时必须保持的口径：

### 4.1 confirmation

表示**案例结果确认链路**，也就是：

- 模型输出拿到后，
- 用 case 中的确认规则、工件检查、执行检查等，
- 判断这次 run 是否达到“通过/部分通过/失败”。

旧名字很多地方叫 `validation`，当前正在逐步收口到 `confirmation`。  
**原则：语义上以后都优先说 confirmation。**

### 4.2 replay gate

表示**进入 evolve 之前的门禁/回放验证层**。

它的作用不是确认漏洞真值，而是决定：

- 某个技能候选是否达到发布/演化门槛；
- 某条反馈是否进入共享技能池；
- 候选技能是否应该被 reject / review / publish。

旧名字很多地方叫 `validation worker/store/jobs`，当前正在逐步收口到 `replay_gate_*`。  
**原则：语义上以后都优先说 replay gate。**

---

## 5. 仓库当前结构（只列最关键的）

### 5.1 核心目录

- `skillclaw/`
  - SkillClaw 主服务
  - 当前已新增：
    - `replay_gate_store.py`
    - `replay_gate_worker.py`
    - `skill_markdown.py`

- `evolve_server/`
  - 演化服务
  - 当前已接入 replay gate / feedback bundle 消费

- `benchmarks/cases/`
  - 当前 benchmark case 定义：
    - `giflib-5.1.2-cve-2016-3977.json`
    - `libxml2-2.9.4-cve-2017-8872.json`
    - `tcpdump-4.9.1-cve-2017-13031.json`
    - `tcpdump-4.9.1-cve-2018-14469.json`
    - `exiv2-0.26-cve-2017-17725.json`
    - `libarchive-3.8.0-cve-2025-60753.json`

- `evaluation/`
  - 当前是扩展层主入口
  - 关键子目录：
    - `confirmation/`：新的 confirmation 主实现
    - `validation/`：兼容层 wrapper，逐步退场
    - `runs/`：本地/远端 case 执行
    - `postprocess/`：结果整理
    - `reporting/`：当前报告、反馈、publication 汇总
    - `remote/`：远端 VM 连接模块

- `reports/`
  - 面向人读的结果与论文整理材料

- `runtime/`
  - 运行期产物，只放运行数据，不放源码

- `skillspace/`
  - 当前技能物理空间
  - 关键路径：
    - `skillspace/live/`：当前直接被 SkillClaw 使用的 live skills
    - `skillspace/share/`：本地共享/演化产物空间

---

## 6. 当前配置与服务启动方式

当前本机仓库根目录：

- `D:\Code\SkillClaw\SkillClaw`

当前本机分支：

- `dev`

当前 remotes：

- `origin` -> 原始 SkillClaw 仓库
- `fan` -> GitHub 镜像
- `codeup` -> 阿里 Codeup 仓库

### 6.1 本机 SkillClaw 当前配置（已知）

从 `skillclaw.cli config show` 看到的关键值：

- `skills.dir = D:\Code\SkillClaw\SkillClaw\skillspace\live`
- `sharing.local_root = D:\Code\SkillClaw\SkillClaw\skillspace\share`
- `proxy.port = 30000`
- `dashboard.port = 3788`
- `dashboard.evolve_server_url = http://127.0.0.1:8787`
- `validation.mode = replay`

### 6.2 本机三个终端的标准恢复指令

如果新终端没有自动进入 `.venv`，先执行：

```powershell
(Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned) ; (& D:\Code\SkillClaw\SkillClaw\.venv\Scripts\Activate.ps1)
```

#### 终端 1：SkillClaw

```powershell
cd D:\Code\SkillClaw\SkillClaw
.\.venv\Scripts\python.exe -m skillclaw.cli start --port 30000
```

#### 终端 2：Evolve Server

不要把真实 key 写进仓库。运行前在当前终端设置环境变量。

```powershell
cd D:\Code\SkillClaw\SkillClaw

$env:EVOLVE_ENGINE="workflow"
$env:EVOLVE_STORAGE_BACKEND="local"
$env:EVOLVE_STORAGE_LOCAL_ROOT="D:\Code\SkillClaw\SkillClaw\skillspace\share"
$env:EVOLVE_GROUP_ID="default"

$env:OPENAI_API_KEY="<DEEPSEEK_API_KEY>"
$env:OPENAI_BASE_URL="https://api.deepseek.com"
$env:EVOLVE_MODEL="deepseek-v4-pro"
$env:EVOLVE_LLM_API_TYPE="openai-completions"

.\.venv\Scripts\python.exe -m evolve_server `
  --engine workflow `
  --local-root .\skillspace\share `
  --group-id default `
  --port 8787 `
  --publish-mode validated `
  --feedback-bundle runtime\evolve\skill_feedback_bundle.json
```

#### 终端 3：Dashboard

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

### 6.3 本机快速健康检查

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:30000/healthz
```

服务端 skills 列表：

```powershell
$headers = @{ Authorization = "Bearer sk-skillclaw-lab" }
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:30000/v1/skills -Headers $headers
```

Dashboard：

- `http://127.0.0.1:3788`

---

## 7. 远端 VM 能力（当前已确认可用）

### 7.1 远端 VM 基本信息

- 用户：`li`
- 主机：`192.168.1.4`
- 远端仓库根：`/home/li/skillclaw-eval/SkillClaw`
- 远端分支：最近确认是 `dev`

### 7.2 当前这台本机确实具备远程操作 VM 的能力

已确认：

- 本机存在私钥：
  - `C:\Users\Fan\.ssh\skillclaw_vm`
- 直接 SSH 成功：

```powershell
ssh -i C:\Users\Fan\.ssh\skillclaw_vm -o IdentitiesOnly=yes -o BatchMode=yes li@192.168.1.4 "hostname && whoami && pwd"
```

### 7.3 工程化远端模块

文件：

- `evaluation/remote/experiment_vm.py`

能力：

- 远端 SSH 执行命令
- 上传文件
- 下载文件
- 自动记录远端操作日志

默认日志文件：

- `runtime/logs/remote_vm_commands.log`

### 7.4 远端模块的直接用法

#### 连通性检查

```powershell
.\.venv\Scripts\python.exe -m evaluation.remote.experiment_vm `
  --host 192.168.1.4 `
  --user li `
  check
```

#### 执行一条远端命令

```powershell
.\.venv\Scripts\python.exe -m evaluation.remote.experiment_vm `
  --host 192.168.1.4 `
  --user li `
  run "cd ~/skillclaw-eval/SkillClaw && git branch --show-current && pwd"
```

#### 上传文件

```powershell
.\.venv\Scripts\python.exe -m evaluation.remote.experiment_vm `
  --host 192.168.1.4 `
  --user li `
  upload .\local.txt ~/skillclaw-eval/local.txt
```

#### 下载文件

```powershell
.\.venv\Scripts\python.exe -m evaluation.remote.experiment_vm `
  --host 192.168.1.4 `
  --user li `
  download ~/skillclaw-eval/remote.txt .\runtime\imports\remote_vm\remote.txt
```

### 7.5 VM 上 Claude 与 SkillClaw 代理的关系

当前 VM 多数情况下跑在 VMware NAT 网段：

- VM: `192.168.1.4`
- Windows 宿主机 NAT 地址：`192.168.1.1`

因此 VM 上 Claude 应优先连：

- `http://192.168.1.1:30000`

不要默认写死校园网地址 `10.12.189.47`，除非 VM 改为桥接并确认能直达。

---

## 8. 当前主执行链路

### 8.1 本地服务链路

```text
Claude/客户端
  -> SkillClaw proxy
  -> 会话采集 + skill 注入
  -> runtime/records/conversations.jsonl
  -> confirmation / scoring / postprocess
  -> reports / feedback bundle
  -> evolve_server
```

### 8.2 benchmark case 链路

关键入口：

- `evaluation/runs/run_single_case.py`
- `evaluation/runs/run_remote_case.py`
- `evaluation/postprocess/finalize_record.py`

逻辑大致是：

1. 读取 case JSON
2. 渲染 blind prompt 或执行 orchestration
3. 获取 agent 原始输出
4. 跑 confirmation
5. 生成 final / final-enriched 记录
6. 汇入 feedback bundle / publication reports

### 8.3 远端 blind case 链路

相关脚本/路径：

- prompt 渲染：
  - `evaluation/utils/render_case_prompt.py`
- blind workspace：
  - `evaluation/utils/prepare_blind_workspace.py`
- remote orchestration：
  - `evaluation/runs/run_remote_case.py`

远端手工运行常见路径：

- 远端源码根：
  - `~/skillclaw-eval/<target>`
- blind workspace：
  - `~/skillclaw-eval/blind_workspaces/<case-id>`
- 手工运行输出：
  - `~/skillclaw-eval/manual_runs/<run-name>/`

---

## 9. 当前重要数据路径

### 9.1 skill 相关

- live skills：
  - `skillspace/live/`
- shared / evolve space：
  - `skillspace/share/`

### 9.2 运行记录

- 会话记录：
  - `runtime/records/conversations.jsonl`
- PRM 分数：
  - `runtime/records/prm_scores.jsonl`
- 远端导入结果：
  - `runtime/imports/remote_vm/`
- 远端命令日志：
  - `runtime/logs/remote_vm_commands.log`
- evolve 历史：
  - `runtime/evolve/evolve_history.jsonl`

### 9.3 面向论文/汇报的结果

- 当前结果矩阵：
  - `reports/current/result_matrix.md`
- 当前 runset：
  - `reports/current/runset.md`
- 当前 skill 反馈：
  - `reports/current/skill_feedback.md`
- publication 版本：
  - `reports/publication/`

### 9.4 说明文档

- 本文件：
  - `AGENT_HANDOFF.md`
- 远端执行说明：
  - `docs/ops/remote_execution_notes.md`
- 远端操作日志：
  - `docs/ops/remote_vm_live_log.md`
- 架构摘要：
  - `docs/reference/extension_architecture_summary.md`

---

## 10. 当前工程真实状态（非常重要）

### 10.1 当前不是干净工作树

截至 2026-08-04，本地 `git status --short` 仍然显示大量未提交修改与新增文件。  
不要假设当前仓库是“完全稳定、完全整理完毕”的状态。

### 10.2 当前正在进行的主要整理

正在把旧命名逐步收口到：

- `confirmation`
- `replay_gate`

已经改到核心链路和部分 dashboard / reporting，  
但展示层、报表层、旧兼容字段仍有残留。

### 10.3 当前 WIP 的关键新增文件

- `evaluation/confirmation/`
- `skillclaw/replay_gate_store.py`
- `skillclaw/replay_gate_worker.py`
- `skillclaw/skill_markdown.py`

### 10.4 当前仍需注意的遗留问题

1. `validation` / `confirmation` 命名仍有并存残留  
2. `validation worker/store` 与 `replay gate` 的展示层尚未完全收口  
3. dashboard / reporting 中仍有旧词和旧字段  
4. 不能过度宣称“selected skill = 一定真实生效”  
5. 新 case 的确认链路仍常需要 case 级适配信息

---

## 11. 当前已知可用的 benchmark / 结果情况

当前仓库内有 6 个 benchmark case 定义，分别是：

- giflib
- libxml2
- tcpdump-2017-13031
- tcpdump-2018-14469
- exiv2
- libarchive

注意：

- **case 定义存在**，不等于都已经在当前最新代码状态下重新完整复跑；
- `runtime/imports/remote_vm/` 和 `reports/publication/` 中已经沉淀了多轮历史远端结果；
- 这些结果可以作为证据和论文素材，但在最新结构整理完成后，仍应按需要重新验证关键链路。

---

## 12. 当前最推荐的工作方式

### 12.1 如果目标是继续工程整理

优先顺序：

1. 读本文件
2. 看 `git status`
3. 启动三服务
4. 检查 VM 连接
5. 跑一条最小链路
6. 再改代码

### 12.2 如果目标是继续远端 blind case

优先顺序：

1. 启动本机 SkillClaw / Evolve / Dashboard
2. SSH 检查 VM
3. 确认 VM 上 Claude 指向 SkillClaw proxy
4. 渲染 prompt
5. 在 VM 跑 case
6. 把结果导回 `runtime/imports/remote_vm/`
7. 跑 finalize / reporting

### 12.3 如果目标是继续论文工作

优先顺序：

1. 不要先写长篇 tex
2. 先核对工程真实闭环状态
3. 只基于实际跑过的结果写 claims
4. 明确区分：
   - benchmark case 是否存在
   - blind run 是否成功
   - confirmation 是否通过
   - feedback 是否进入 evolve

---

## 13. 对后续 Agent 的直接建议

1. **先把当前树当作 WIP，而不是已完成版本。**
2. **先跑最小验证，再继续改。**
3. **远端 VM 能力已经具备，可以直接使用。**
4. **不要把 key、token 写进仓库。**
5. **对外表述时，谨慎区分 confirmation 和 replay gate。**
6. **不要重新引入大批 `experiment_*` 式命名。**
7. **优先把新增能力收进已有模块，而不是继续堆脚本。**

---

## 14. 建议的下一步（接手即做）

如果你是下一位 Agent，建议直接按这个顺序继续：

1. 读本文件；
2. `git status --short`；
3. 拉起三服务；
4. `python -m evaluation.remote.experiment_vm --host 192.168.1.4 --user li check`；
5. 选一个最小 case（优先 giflib）跑一遍当前链路；
6. 确认：
   - SkillClaw 有无正确注入 skill
   - confirmation 是否落盘
   - feedback bundle 是否更新
   - evolve 是否消费到记录
7. 再决定继续做：
   - 命名整理
   - 远端闭环增强
   - 新固件 case 接入
   - 论文实验整理

---

## 15. 最后一句话

当前项目**不是从零开始**，也**不是完全收尾**。  
它已经具备了：

- 本地三服务恢复能力
- 远端 VM 连接能力
- benchmark / confirmation / feedback / evolve 基础链路

但仍处在“**核心链路已成型，命名与归因仍需继续打磨**”的阶段。

