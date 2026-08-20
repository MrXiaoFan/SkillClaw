# Agent Handoff

当前最新的阶段性交接材料在：

1. [reports/current/briefing_20260816/glm_handoff_20260816.md](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260816/glm_handoff_20260816.md)
2. [reports/current/briefing_20260816/session_archive_20260816.md](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260816/session_archive_20260816.md)
3. [reports/current/briefing_20260816/engineering_status_20260816.md](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260816/engineering_status_20260816.md)
4. [reports/current/briefing_20260816/weekly_report_20260816.md](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260816/weekly_report_20260816.md)
5. [reports/current/briefing_20260816/startup_checklist_20260816.md](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260816/startup_checklist_20260816.md)

上一阶段交接（08-15）归档在：

- [reports/current/briefing_20260815/glm_handoff_20260815.md](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260815/glm_handoff_20260815.md)
- [reports/current/briefing_20260815/session_archive_20260815.md](/D:/Code/SkillClaw/SkillClaw/reports/current/briefing_20260815/session_archive_20260815.md)

本次阶段（08-16）的核心状态：

- 接续 08-15 崩溃会话，重放出 18 条用户指示并完成状态对比、论文 v2 更新（6 处 + 3 处 LaTeX 修复）；
- 首次在 F453 上完整闭合 run → feedback → evolve → candidate → gate(real_rerun) → publish 全链路，零人工 skill 编辑（tenda v2 / cisco v2 / peplink v3 自动发布）；
- F453 命中 formWriteFacMac 从 0/5 提升到 2/15，但 skill 必要性仍未证明；
- 周报与工程状态已于本轮复核并重写为可汇报版本，桌面 docx 与 `briefing_20260816/` 中的 markdown 已同步；
- 后续优先：重写周报 → 修 gate 设计缺陷（34 pending）→ 用 tenda v2 验证 skill 必要性 → 启用 catalog 模式。


---

## 2026-08-20 更新：方案 A 全量重跑完成（新模型 deepseek-v4-flash + 净化技能）

净化提交 8186f34 已合入（盲测提示词抹掉答案线索、修复 OOM、inline skills 不注入 catalog、新增 14 案例 + elf weak skill）。

方案 A 已完成：14 cases × 3 conditions × 2 rounds = **84 runs**，结果输出在
`runtime/ablation/results/ablation_results_rerun_model.csv`（与旧作弊数据 `ablation_results.csv` 用 `--output-tag` 隔离）。

结果对比（同一批 14 案例）：
- **old（作弊 baseline）** oracle-skill YES = 39/40（97.5%）
- **new（净化 + deepseek-v4-flash）**：
  - no-skill:   YES 1/28 (3.6%)  DECOY 9  NO 18
  - weak-skill: YES 4/28 (14.3%) DECOY 12 NO 12
  - oracle-skill: YES 10/28 (35.7%) DECOY 1 NO 17

结论：净化后 oracle 命中率从 ~97% 掉到 ~36%，说明旧 39/40 主要是技能注入泄答案的作弊效果，不再是 clean 命中。清洁重跑下仍有 no-skill(1) 与 weak-skill(4) 的偶然 YES，oracle 未能在所有案例上压倒性领先，skill 必要性尚需进一步论证/调优。

next steps（未做）：可选按案例逐一核 oracle 未命中的 9 个案例（f1202-*、f453-qossetting、f9k1122-crossband/setpassword/setsystemsettings/wlansetup、i12），检查是 clean 模型能力不足还是 oracle skill 本身不够强；可考虑提高 skill 质量后再跑一轮。

---

## 2026-08-20 补充：9 个 oracle 未命中案例排查 + oracle skill 作弊检查

### 作弊检查结论（oracle skill 本身是干净的，没有作弊）
- 对全部 18 个 oracle skill 扫描：**没有任何一个嵌入目标函数名、诱饵函数名、设备/厂商、CVE 号或参数名**。唯一出现 "CVE" 的地方是描述里那句 "does NOT embed ... CVE"（用于声明不泄答案），是自说明，不是线索。
- oracle skill 只是"方法论"级别的非答案指引，符合 design intent。
- **但发现 oracle skill 存在"同质化"问题**：18 个里实际只有 12 份不同 content，其中
  - oracle-case-08/09/10/11/12 五份**逐字相同**（formSetCrossBand/formSetPassword/formSetSystemSettings/formWISP5G/formWlanSetup 共用同一份 webs overflow 方法论）
  - oracle-case-01/03/07 三份相同（三处 cmd-inject）
  - case-04/05/06/13/14/15/16/17 八份 description 相同、content 各异
- 这说明 oracle skill 只区分"漏洞大类/设备家族"，同家族内是同一份通用指引，**并未针对单一目标函数做定向提示**——所以它本来就是"不泄答案"的，但也因此对区分同家族多个目标帮助有限。

### 9 个未命中案例根因分层
关键发现：**未命中几乎全部不是"oracle skill 不够强"，而是模型在多个相似 handler 中选错了（跑到了 family 内另一个嫌疑 handler）**。
- f9k1122 家族：setpassword/wlansetup/setsystemsettings/crossband 全部预测到 **formWISP5G**（同家族里"最显眼"的 handler），而非各自真实目标（formSetPassword/formWlanSetup/formSetSystemSettings/formCrossBandSwitch）。模型把共用方法论套到了最出名的 handler 上。HIT 的 formWISP5G 案例（oracle-case-11）与此一致——case-09/11 是同一条 skill。
- f1202-cmdinject：预测到 formexeCommand（诱饵，被判 NO 而非 DECOY，因为 target=formWriteFacMac），未到 formWriteFacMac。
- f1202-credential-overflow：r1 到 fromSysToolChangePwd/decodePwd（方法论的"credential-decode helper"方向对，但 handler 错了）；r2 到 formWrlsafeset。
- f453-qossetting-overflow：两轮都到 formWrlsafeset / AdvSet（同家族显眼 handler），未到 fromqossetting。
- i12-pathtraversal：r1 httpd_auth_gatekeeper、r2 httpd_decode_url/websGetRequestPath——方向对（都是 gatekeeper/url 处理），但没收敛到 R7WebsSecurityHandler。

### skill_relevance 佐证
- HIT 案例（formWISP5G）：relevance = "has_task_relevant_skill / matched oracle"。
- 多数 MISS 案例：relevance = **"no_task_relevant_skill" + matched_terms 为空**（即使 skill 被 injection 选中），说明在模型看来这份通用方法论没有直接命中它的检索词，削弱了指引效力。

### 结论
1. **oracle skill 无作弊**，净化彻底有效，可放心用作"clean oracle"上界。
2. oracle 命中率低（36%）的主因不是泄答案问题，而是：**(a) oracle skill 同家族同质化、不指向具体目标；(b) 新模型在多个相似 handler 间被"显眼 handler"带偏**。
3. 这反而说明：要给 oracle 注入"定向能力"，必须在方法论里加入**区分同家族 handler 的可操作判据（数据流/字符串特征/参数名提示）**，而不是笼统的"别选最显眼的"。

next steps（建议）：
- 选项1：重写 oracle skill 为"同家族区分型"，加入每个目标 handler 独有的证据特征（不泄露函数名，但给出可验证的字符串/数据流判据），再跑一轮验证 oracle 命中率能否显著回升。
- 选项2：若目标是论证"通用方法论即可"则维持现状，但需说明 oracle 上界本身在 clean 下就只有 ~36%。

---
## 2026-08-20 晚：崩溃根因（CC Switch exec_command JSON 截断）+ 27 案例分类 + 同家族 oracle 方案


## 2026-08-20 深夜：27 案例分类确认 + 方案 A 14 case 矩阵 + 同家族 oracle 设计草案

### 崩溃根因复述（CC Switch 代理 JSON 截断）
- root cause 与之前一致：deepseek-v4-flash 经 CC Switch(C402-DSv4Flash-Codex)生成 tool 参数时，
  exec_command 的 cmd 字符串 JSON 被截断（quote 未闭合，EOF at column ~866）。
- 对策（本轮已经贯彻，后续也必须遵守）：
  1. 不在 exec_command 里传超长单行命令；PowerShell 用 ; 分隔，不用 &&。
  2. 需要多行的 Python/PowerShell 先写到临时 .py 文件再执行，或 python -c 短代码。
  3. 单条 cmd 尽量短，长逻辑拆多个 exec_command。
  4. 避免一次塞大段 heredoc。

### 27 案例全量分类（benchmarks/cases/*.json = 27 个，实测计数）
- HTTP/固件可触达 handler 类 21 个：
  Tenda(F1202/F453/F456/FH451) 13 + Belkin F9K1122 webs 5 + i12 2 + firmware2 lighttpd CGI 2
- 用户态库/解析器类 6 个（非 handler，source-parser 推理）：
  exiv2, giflib, libarchive, libxml2, tcpdump x2

### 方案 A 的 14 个 case = 全为 HTTP handler/cgi 入口
- run_ablation.py CASES 实测 13 个 key + fh451 家族 5 个子 case，去重后共 14 个 case
- 这 14 个全部是 formXxx / fromXxx / R7WebsSecurityHandler / Wrlxxx / sub_xxx(lighttpd cgi) 类
  dispatch 入口中的 handler 漏洞。用户问题"答案全都是 handler？"：对这 14 个 ablation case 而言 = 是，
  全部都是 handler；但对全部 27 个 benchmark case 而言 = 否（6 个是用户态解析器函数）。
- 84 runs = 14 case x 3 conditions(no/weak/oracle) x 2 rounds，已在 ablation_results_rerun_model.csv 确认。

### oracle skill 同质化确认（F9K1122 家族）
- oracle-case-08/09/10/11/12 五份 content 逐字相同（webs overflow 通用方法论），哈希也一致。
- oracle-case-01/03/07 三份逐字相同（cmd-inject）。
- F9K1122 家族 4 个非 WISP 目标全被预测成 formWISP5G：同一份通用方法论不区分族内目标，
  模型被"最显眼 handler"带偏。

### F9K1122 族内区分特征（binary-derived，来自 f9k_neighborhood.json / f9k_strings.json）
每个 handler 符号在字符串表中的邻接 token 可作为不泄函数名的判据：
- formWlanSetup: 紧跟 formWlanMP/formWdsEncrypt/formHwSet/formTcpipSetup；内含 admin_mac_addr 参数、
  /var/w1.ip 写文件、submitMAC/Delindex(删除行) 前端逻辑
- formWISP5G: 紧跟 formWlanSetupWPS/formWlanGuestSetup/formCrossBandSwitch，接 formSetWanType 家族
- formCrossBandSwitch: 紧跟 formSetWanType/formSetWanDynamic...formSetWanPPPoE(formSetWan* 家族)
- formSetSystemSettings / formSetPassword: 紧跟 flash 读写错误串(Write flash current-setting header failed!、
  Invalid default setting signature...), formSelfHealing/formSetAPROUTERMODE/formSetFirewall 邻居

### 下一步建议（选项1 落地）
重写 oracle skill 为"族内区分型"，对 F9K1122 家族先做一轮（5 case），验证 oracle 命中率能否回升。
生成素材：runtime/ablation/werk/f9k_neighborhood.json（全量邻接数据）。执行时注意分批写文件，避免长命令。

### 2026-08-20 深夜续：族内区分型 oracle skill 起草 + 验证跑已启动
- 生成 5 份 F9K1122 族内区分型 oracle skill（runtime/ablation/oracle_skills_json/oracle-f9k-distinguishing-*.json）：
  wisp5g / crossband / wlan-setup / set-system-settings / set-password。
- 关键设计：用二进制字符串表"邻接符号指纹"区分族内 handler（如 formWlanSetup 紧邻 formWlanMP/formWdsEncrypt/formHwSet/formTcpipSetup；
  formWISP5G 关联 wispWanId/formiNIC*；formCrossBandSwitch 紧邻 formSetWan* 家族；
  formSetSystemSettings/formSetPassword 在 flash-持久化错误串区域，互为前后邻）。均不写目标函数名本身。
- 抽查确认：5 份内部都不含各自目标符号名（set-password 那份只引用兄弟 formSetSystemSettings 作为定位参照，不含 formSetPassword）。
- 验证跑步器 runtime/ablation/run_f9k_distinguish.py（独立 output-tag f9k_distinguish_oracle，不碰 rerun_model CSV），
  5 case x oracle-skill x 3 rounds = 15 runs，后台已启动，log: runtime/ablation/results/f9k_distinguish_run.log。
- 复核 baseline（rerun_model.csv f9k1122 族）：
  * wisp5g/overflow(case f9k1122-overflow) oracle 2/2 HIT(score8)
  * crossband oracle r1=8(HIT formWISP5G 但实际 gt 要 formCrossBandSwitch，判分是否命中待核) r2=4.5(MISS)
  * setpassword oracle 2/2=8(但预测 formWISP5G；注意该 case 的 ground_truth.functions=['formSetSystemSettings','strcpy']，
    与文件名 setpassword/run_ablation target=formSetPassword 不一致，可能两边都算对或都算错，需专门核对)
  * setsystemsettings oracle r1=8 r2=4.5
  * wlansetup oracle 2/2=4.5(MISS，预测 formWISP5G)
- 待验证结果出来后，判断族内区分 skill 是否把 4 个非 WISP 目标从"全预测 formWISP5G"掰到各自真相。
- 注意 runtime/ 目录在 .gitignore 里，生成的 skill 与 runner 不纳入 git；如需版本化需另行处理。
