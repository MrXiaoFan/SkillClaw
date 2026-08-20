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

### 2026-08-20 结果：族内区分型 oracle 验证完成（15 runs），oracle 命中率大幅回升
- output-tag=f9k_distinguish_oracle 已完成 5 case x oracle-skill x 3 rounds。
- 逐 case（对比旧 generic-oracle 的 YES 率 -> 新 distinguishing 的 YES 率）：
  * f9k1122-overflow(WISP5G)         2/2 -> 3/3  (both HIT)
  * crossband                       0/2 -> 3/3  (全修好，预测 formCrossBandSwitch)
  * wlansetup                       0/2 -> 3/3  (全修好，预测 formWlanSetup)
  * setpassword                     0/2 -> 0/3  (仍 MISS；formSelfHealing/formWISP5G，兼有 ground-truth 异常)
  * setsystemsettings               0/2 -> 1/3  (r1 HIT formSetSystemSettings，r2/r3 又飘 formWISP5G)
- 汇总：old oracle 2/10 (20%) -> new distinguishing 10/15 (66.7%)，约 3 倍。
- 关键结论：族内区分型 skill 用的是二进制字符串表"邻接符号指纹"（不写目标函数名），
  能把 crossband/wlansetup 这类原本全被带偏到 formWISP5G 的案例稳定掰回正确 handler。
- 剩余 2 个顽固案例 setpassword/setsystemsettings 恰是"同 flash-持久化串区、互为前后邻"的近亲对，
  技能难以把二者分开；且 setpassword case 的 ground_truth.functions=['formSetSystemSettings'] 与
  文件名/run_ablation target=formSetPassword 不一致（待核对，可能这个 case 本身定义就有问题）。
- 下一步建议：
  1. 核对 setpassword 的 ground_truth 异常（是否应改为 formSetPassword 或就是重复的 setsystemsettings）。
  2. 对 setpassword/setsystemsettings 两个近亲，可在技能里加更强判据（如各自前后第二个/第三个邻接符号、
     或各自特有的 flash error 子串位置），再补一轮，验证能否把 1/3 提到 3/3。
  3. 若要把"族内区分"推广到全 14 case，需要给每个家族的每份 oracle 生成邻接指纹（已有 f9k_neighborhood 素材）。

### 补充：setpassword case 的 ground_truth 异常已定位
- f9k1122-webs-overflow-formSetPassword.json 与 formSetSystemSettings.json 两份 case 文件
  的 task_profile.notes / ground_truth.functions / required_evidence / blind_workspace.agent_root
  完全相同（都指向 formSetSystemSettings + reboots图同 root）。所以 "setpassword" 这份 case
  实际上是 formSetSystemSettings 的重复定义（dataset 侧混入了同一 vul5 样本）。
- 因此 run_ablation 里 f9k1122-setpassword-overflow 的 target=formSetPassword 与
  case文件 ground_truth=formSetSystemSettings 不一致，导致它评分一直很怪（预测 formWISP5G 被判 NO，
  预测 formSetSystemSettings 判 YES 但文件名是 setpassword）。
- 结论：setpassword case 需在 dataset/benchmark 层面订正（要么给真 formSetPassword 的 ground_truth，
  要么划为重复 case 排除）；不是 oracle skill 的问题。

### 2026-08-20 补强：setpassword 异常已 100% 确认 = dataset 重复 case（非 skill 问题）
- 逐字段比对 f9k1122-webs-overflow-formSetPassword.json 与 formSetSystemSettings.json：
  仅 case_id 与 notes 两个字段不同，其余（target.source_root、blind_workspace、ground_truth、
  required_evidence、validators、confirmation、prompt、oracle_only_paths）逐字节相同。
- 源侧对照 Z 盘原始样本：vul4（真 formSetPassword，poc 打 /goform/formSetPassword，
  webs MD5=205E6972...）与 vul5（formSetSystemSettings，poc 打 /goform/formSetSystemSettings，
  webs MD5=205E6972...）两样本的 webs 二进制 MD5 相等（同一固件），formsDefine.c 也相同，
  仅 vul_function 源码与 description/poc 不同。
- 但 benchmark 里的 setpassword case 把 source_root/blind_workspace/GT/validator 全指向 vul5
  （formSetSystemSettings），notes 文本却声称来自 vul4。结论：这份 case 是从 setsystemsettings case
  直接复制、只改了 case_id 和 notes，从未真正从 vul4 的 formSetPassword 样本重新派生。
- 因此 setpassword 在 ablation 里测的是「vul5 二进制上的 formSetPassword」一个不存在的目标。
  0/3 是数据缺陷造成的，不是 skill 盲区——真正要区分的是同一个 webs 二进制里的相邻两个 handler。
- 近亲对无法靠二进制邻接指纹分开的根因：二者是同一份 webs 固件里的相邻符号，字符串表里
  formSetSystemSettings(445) 紧邻 formSetPassword(446)，且邻接串完全相同（同 flash 持久区），
  没有任何二进制级 token 能区分二者；真正能区分的是 poc 打哪个 /goform/* 端点（但那是 oracle-only，不给模型）。
=> 判定：setpassword case 应在 dataset/benchmark 层面作废或订正（要么改用 vul4 真样本重派生，
   要么标为重复 case 从 14 案例集排除）。tuning oracle skill 无法修复它。

### 2026-08-20 记录归档：F9K 族内区分验证已整理为阶段性工作记录
- 结果原始数据在 runtime/ablation/results/（.gitignore 忽略）：
  ablation_results_f9k_distinguish_oracle.csv、f9k_distinguish_run.log。
- 已在 reports/current/briefing_20260816/（纳入 git）生成归档：
  - f9k_distinguishing_validation_20260820.md（阶段性工作记录）
  - f9k_distinguishing_run_table_20260820.csv（15 行规范化结果表）
- commit: baa7ef3

### 2026-08-20 归档：方案 A 清洁重跑（84 runs 三条件对照）结果整理
- 用户本轮要的是 84 runs 的 no/weak/oracle 对照组（即提到的 97.5%->35.7% 实验），不是族内区分验证。
- 原始数据：runtime/ablation/results/ablation_results_rerun_model.csv（84 行，.gitignore 忽略）。
- 已归档到 reports/current/briefing_20260816/（纳入 git，commit 2ce59e5）：
  - planA_clean_rerun_validation_20260820.md（阶段性工作记录）
  - planA_clean_rerun_table_20260820.csv（84 行规范化结果表）
- 结果速览：no-skill 1/28 (3.6%)、weak-skill 4/28 (14.3%)、oracle-skill 10/28 (35.7%)。

### 08-20 补充:方案 A 清洁重跑中文记录

- 已将 「方案 A 三条件清洁对比(84 runs)」 整理为中文详细实验记录: reports/current/briefing_20260816/planA_clean_rerun_validation_20260820.md (含目的/设计/统计/逐 case/逐 run 84 行表/结论/setpassword 缺陷说明)。
- 规范化结果表: reports/current/briefing_20260816/planA_clean_rerun_table_20260820.csv。
- commit: 2ce59e5 (staged) + 6fb062c (扩充) + e8c8529 (中文重写定稿)。
- 核心结论: 旧作弊 baseline oracle 97.5% -> 清洁重跑 35.7% (约 -62pp); no-skill 3.6% / weak 14.3% / oracle 35.7%。

