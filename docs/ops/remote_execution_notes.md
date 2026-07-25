# Remote Execution Notes

这份文件不再保存逐行原始终端回显，而是保留对当前工程有用的远端执行纪要。

目的只有两个：

1. 记录远端 VM 上真实发生过的关键操作
2. 说明哪些问题来自环境，哪些问题来自当前工程

---

## 2026-07-16：本地三服务恢复

本地恢复并确认了三项服务可正常启动：

- SkillClaw proxy：`http://127.0.0.1:30000`
- Evolve Server：`http://127.0.0.1:8787`
- Dashboard：`http://127.0.0.1:3788`

结论：

- 本地代理、演化服务、面板三者链路可重新拉起
- 本地配置中的技能注入、验证 worker、dashboard 接线是通的

---

## 2026-07-19：远端 VM 上手工盲跑 giflib

远端 VM 环境：

- 主机名：`li-virtual-machine`
- 用户：`li`
- 工作目录：`~/skillclaw-eval/SkillClaw`

在远端手工执行了 Claude CLI，对 giflib 进行盲跑分析。做法是：

1. 进入 `~/skillclaw-eval/giflib-5.1.2`
2. 使用人工准备的 blind prompt
3. 直接运行 `claude -p`
4. 输出写入 `~/skillclaw-eval/manual_runs/giflib_blind/raw.txt`

观察结果：

- Claude 能直接定位到 `util/gif2rgb.c`
- 能指出 `DumpScreen2RGB` / `GIF2RGB`
- 能给出背景色索引越界读这一根因

结论：

- 远端模型本身具备完成该案例静态分析的能力
- 但这一步只是“模型手工分析成功”，还不等于 SkillClaw 闭环已经完整可用

---

## 2026-07-19：SkillClaw 代理侧暴露出的输入问题

在让 Claude 通过 SkillClaw 代理走完整链路时，服务端出现过一次关键错误：

- 上游 DeepSeek 返回 `400 Bad Request`
- 报错核心是 `messages[*]: unknown variant image_url, expected text`

问题含义：

- 当前代理转发给上游 LLM 的消息里，混入了非纯文本内容
- 这不是漏洞案例本身的问题，而是“代理输入整理层”的问题

工程结论：

- 对上游模型的请求需要强制收敛为纯文本上下文
- 否则远端盲跑即使在 Claude CLI 成功，也可能在 SkillClaw 代理层失败

---

## 2026-07-20：闭环接线状态复核

复核本地日志后确认：

- SkillClaw 会话结束时，验证 worker 会生成验证结果
- Evolve Server 启动时会读取 `reports/current/skill_feedback_bundle.json`
- 说明“结果进入反馈 bundle，再被 evolve server 读取”这段接线已经存在

但同时也发现一个重要限制：

- 当前进入 evolve 的 `selected_skill_names` 只是“被选中/被注入”的技能
- 还不能严格证明这些技能“真的在本次会话里起了作用”

这意味着：

- **闭环已通**
- **归因还不够强**

---

## 当前远端侧结论

截至 2026-07-21，远端 VM 相关结论可以压缩成四句：

1. 远端手工盲跑 giflib 是成功的
2. SkillClaw -> 上游 LLM 的纯文本化处理还需要更严格
3. validator -> feedback bundle -> evolve server 这条链已经接上
4. “技能被选中”不等于“技能真的生效”，后续还需要补归因层

---

## 后续使用建议

后续如果还要在远端 VM 做对比实验，建议统一分成两类：

### A. 手工盲跑

用途：

- 观察模型真实分析过程
- 避免 case 自带工件泄露答案

### B. 框架闭环跑

用途：

- 验证 SkillClaw 代理、validator、反馈 bundle、evolve server 是否完整联通
- 检查闭环记录是否合理

不要把这两类结果混在一起解释。
