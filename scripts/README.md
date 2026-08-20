# Scripts

`scripts/` 只保留仓库级辅助脚本，不承载主流程实现。

主流程代码请直接看：

- `skillclaw/`
- `evolve_server/`
- `evaluation/`

## 目录

- `install/`
  - 安装和初始化脚本
- `ops/`
  - 日常运维辅助脚本
- `demos/`
  - 演示或最小示例

## 当前文件

- `install/install_skillclaw.sh`
  - 本地客户端安装脚本
- `install/install_skillclaw_server.sh`
  - 服务端依赖安装脚本
- `ops/proxy_session_admin.py`
  - 查看和清理当前 SkillClaw 代理会话
- `ops/start_skillclaw.ps1`
  - 启动本地 SkillClaw 服务端
- `ops/start_evolve.ps1`
  - 启动本地 Evolve Server，直接复用 `C:\Users\Fan\.skillclaw\config.yaml` 中的 LLM 配置
- `ops/start_dashboard.ps1`
  - 启动本地 Dashboard
- `ops/safe-runner.cmd` **（CC Switch 防断层 CMD 工具，所有命令行走这里）**
  - 用途：以短行调用本仓库 scripts 下的 .py/.ps1，规避 CC Switch 对长/内联 PowerShell JSON 的 EOF·吞 $ 导致会话中断（`Invalid function_call arguments for 'exec_command': EOF while parsing a string at line 1 column 866`）。
  - 用法：`cmd /c scripts\ops\safe-runner.cmd <脚本> <参数...>`；多步操作先写成 .py/.ps1 再调用。
  - 脚本头部已内嵌完整提醒；每次 exec_command 前自查：命令行是否 >200 字符 / 含内联 $？是 → 改走 safe-runner。
- `ops/check_stack.ps1`
  - 检查 `30000 / 8787 / 3788` 三个服务状态
- `demos/demo_nacos_skill_lifecycle.py`
  - 演示 Nacos 技能生命周期

## 约束

如果某个脚本已经变成主流程必需逻辑，它就不应继续留在 `scripts/`，而应并入
`evaluation/`、`skillclaw/` 或 `evolve_server/`。
