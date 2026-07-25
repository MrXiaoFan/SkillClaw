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
- `demos/demo_nacos_skill_lifecycle.py`
  - 演示 Nacos 技能生命周期

## 约束

如果某个脚本已经变成主流程必需逻辑，它就不应继续留在 `scripts/`，而应并入
`evaluation/`、`skillclaw/` 或 `evolve_server/`。
