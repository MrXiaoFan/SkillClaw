# 全部实验档案（Experiment Archive）— 旧 + 新，带完整背景/问题/设计

> 生成日期：2026-08-20｜数据来源：`runtime/ablation/results/*.csv`、`runtime/imports/remote_vm/*/final-enriched.json`、`reports/current/briefing_*`、`docs/handoff/*`
> 用途：长期追踪、重新评估、论文写作参考。逐项数据以原始文件为准；本文档是人工整理的分析档案。

---

## 〇、总体方法学、可信度体系与阅读指引

### 〇.1 工程目标（技术闭环）
在原生 SkillClaw（skill 注入 + 自然语言 agent）之上，扩展并打通一条**端到端可运行的漏洞分析流水线**：
`case 定义 → 远程盲测(blind) → 结构化打分 → 外部确认 → 反馈(confirmation) → self-evolve 生成候选 skill → 门控(gate)/校验 → 发布(e.g. v8) → 再盲测`。
工程上要求**逐层可观测**（每一层都有产物 JSON/CSV/handoff），从而支持对任一 run 的归因与复现。

### 〇.2 学术目标（闭环主张）
学术上要论证的是一个**三要素闭环**的主张，而非孤立的“命中率更高”：
1. **技能自进化迭代**（skill 能从闭环反馈中迭代、门控、发布，且迭代确实是因果地提升后续盲测表现）；
2. **漏洞分析**（注入的技能内容确实影响对真实二进制/固件样例的分析质量）；
3. **漏洞验证/确认**（分析结果经外部 oracle 或验证器确认，而不仅是模型自答）。
一句话：**“针对一类漏洞的持续学习，能否被编码成可复用 skill，并经过迭代和验证后稳定提升后续盲测表现。”**

### 〇.3 诚实前提（贯穿全档案）
- **口径一致才可比**：盲测是否“清洁”决定了结论效度。受污染的 oracle 命中率（97.5%）不能与 clean 条件（35.7%）并列归因于 skill。
- **区分“链路能跑通”与“因 skill 而变好”**：closed-loop 证明的是链路存在，不是必要性/收益。
- **区分“命中”与“命中断言级别”**：命中 CVE/file/function 与命中 root_cause 是不同的证据强度。
- **数据层 bug 先于 skill 效应排除**：如 setpassword/setsystemsettings 复制件污染。
- **feedback attribution 是 observational，不是 causal**。

### 〇.4 可信度分级（全文统一使用）
| 级别 | 含义 | 典型场景 |
| --- | --- | --- |
| **高** | 实验条件清洁、样本足够、数据可复现、结论稳健 | 方案 A（84 runs）、F9K 族内区分（15 runs） |
| **中** | 链路真实、机制成立，但样本少/口径不完全一致/不能替代严谨对照 | 六核心、Firmware 消融、F453 对照 |
| **低/作废** | 实验受污染或数据无效，结论不成立或需重做 | 旧消融 159 runs（oracle 97.5% 受污染）、FH451 60 runs |
| **无统计意义** | 仅作流程验证，不做结论 | sanity 2 runs |

### 〇.5 实验演进主线（脉络）
1. 起步期：证明**端到端闭环能跑通**（六核心盲测 + closed-loop proof）。
2. 消融期：证明**注入的 skill 内容确实改变盲测结果**（Firmware CGI 消融、F453 对照）。
3. 反思期：发现旧消融（159 runs）基线被污染（oracle 97.5%），认识到**“不清洁”本身是方法论缺陷**。
4. 重跑期：方案 A 采取统一 case 口径做 **no / weak / oracle 三条件清洁对比**，得到可信主基线（97.5%→35.7%）。
5. 上升期：针对“怎么写 skill 才既有效又不泄露答案”的问题，设计**族内区分型 oracle skill**（邻接指纹，不写函数名），F9K1122 族内命中 20%→66.7%。
6. 清理/加固期：全量盘点 per-run JSON（456 runsets / 3138 json），标记数据缺陷（setpassword 复制件），为论文写作与复审做准备。

### 〇.6 为什么会话中反复强调“避免 exec_command 长内联 JSON”
本工程的复现脚本多次触发 CC Switch 对长/内联 `exec_command` 参数的截断（“EOF while parsing a string” / 吞掉 `$` 变量），导致会话中断。因此后续一律：**优先新建 .py/.ps1 脚本文件再执行，不用极长内联单行命令**。本文档内所有复现脚本标记都以独立脚本文件为准。

### 〇.7 阅读指引
- 前八节各带统一的 [背景 / 研究问题 / 实验设计·变量 / 结果(表) / 讨论 / 可信度·论文引用 / 产物文件] 结构，可直接用于重新评估与论文引用。
- 第九节“遗留数据缺陷与风险”是**常驻**清单，任何新实验动工前应先对照排除污染源。
- 数字速查见《八、可信度汇总矩阵与论文写作映射》；逐 run 明细以原始 CSV/JSON 为准。

---

## 一、早期六核心 source/binary case 远程盲测（闭环起步期）

> 时间：约 2026-07.29–08.02（“paper” runs）。可信度：**中**（机制/闭环证明，不主张命中率）。

### 1.1 背景
工程在原生 SkillClaw 之上扩展出 benchmark / 执行 / 评分 / 确认 / 反馈 / 演化 / 门控各层后，
需要先证明整条链路“真的能端到端跑通”——从定义 case、跑 blind、打分、外部确认，
到产出反馈并让 evolve 生成 candidate。选择 6 个公认的 C 语言/开源漏洞样本作为首批可复现案例。

### 1.2 研究问题
Q1. 全链路（blind → score → confirm → feedback → evolve candidate）能否在真实样本上无断点地跑通？
Q2. 在这些样本上，模型+现有 skill 的盲测命中/评分处于什么水平，作为后续改进的起点。

### 1.3 实验设计与变量
- case 集：giflib-5.1.2/CVE-2016-3977、libxml2-2.9.4/CVE-2017-8872、tcpdump-4.9.1/CVE-2018-14469、
  libarchive-3.8.0/CVE-2025-60753、tcpdump-4.9.1/CVE-2017-13031、exiv2-0.26/CVE-2017-17725，共 6。
- runner：`evaluation/runs/run_remote_case.py`，远端 VM blind 工作区。
- 打分：默认 10 分制（CVE2 + file2 + function3 + evidence1 + root_cause2）。
- 每个 case 常规 1 轮（部分如 tcpdump13031 有多次/多日 run）。

### 1.4 结果（代表性分数，满分 10）
| case | score | 备注 |
| --- | ---: | --- |
| giflib 2016-3977 | 8.0 | file/function/evidence/root_cause 全命中 |
| libxml2 2017-8872 | 8.0 | 同上 |
| tcpdump 2018-14469 | 2.0 | 未命中 |
| libarchive 2025-60753 | 10.0 | CVE/file/function/evidence/root_cause 全命中 |
| tcpdump 2017-13031 | 10.0 | 全命中 |
| exiv2 2017-17725 | 6.0 | 部分命中 |

（数字来源：`reports/current/result_matrix.md` 与 `briefing_20260805/core_benchmarks.csv`）

### 1.5 讨论
- 全链路闭环证明成立：6 案上均产出 final-enriched.json 并进入反馈/演化流程（见 closed_loop_proof）。
- 但这只证明“链路在跑”，不证明“skill 自进化带来收益”。6 case 中 3 个未满分/未命中，说明 baseline 能力有限。

### 1.6 可信度与论文参考
- 可信度：中（作为系统打通证据引用；不作命中率主张）。
- 论文引用点：方法学“端到端生命周期可行”的奠基证据。

### 1.7 产物文件
- 原始：`runtime/imports/remote_vm/giflib-*`、`libxml2-*`、`tcpdump-*`、`libarchive-*`、`exiv2-*` 等 runset（final-enriched.json）；
- 汇总：`reports/current/result_matrix.md`、`briefing_20260805/core_benchmarks.csv`、`briefing_20260805/closed_loop_proof.csv`；
- 交接：`docs/handoff/20260811/01_research_and_development_state.md`（§6.1）。

---

## 二、Firmware CGI 技能消融（登录 / 无线命令注入）

> 时间：约 2026-08-05/06。可信度：**中**（证明 skill 内容影响 blind 结果；不主张必要性）。

### 2.1 背景
在证明端到端闭环可跑后，需要回答更细的问题：服务端注入的 skill **内容**是否会真正改变盲测分析质量？
选取两个固件 CGI 命令注入案例（login / wireless），在严格对照下只改变“当前对 LLM 可见的 skill 版本”。

### 2.2 研究问题
- Q1. 注入不同写法的 skill（none / wrong / relevant / seed），blind 分析结果是否可解释地变化？
- Q2. “有该 skill 才能找到漏洞”这一必要性主张，目前能否成立？

### 2.3 实验设计与变量
- case：firmware2-login-cgi-cve-2026-2527（login.cgi page=login → /sbin/applogin.sh → system()）；
  firmware2-wireless-cgi-cve-2026-2529（wireless.cgi page=DeleteMac → system()）。
- 变量（仅改可见 skill profile，其余固定：同 case / 同 VM / 同通道 / 同 blind prompt / 同评分）：
  - `none`：不注入该类 skill；
  - `wrong`：注入不适配的 `firmware-embedded-lua-shell-extraction`（偏 Lua/脚本，非本 CGI ELF）；
  - `relevant`：“先枚举 /cgi-bin/ 面、再找 sink”；
  - `seed`：“先找 page/action/mode/cmd 分发点、再沿单条分支追到 system()”。
- 规模：wireless none3/relevant2/wrong1/seed2；login none3/relevant2/wrong2/seed1，共 16 次。
- 评分：默认 10 分制 + 隐藏答案 oracle 校验。

### 2.4 结果（平均分，满分 10）
| case | none | relevant | wrong | seed |
| --- | ---: | ---: | ---: | ---: |
| wireless | 2.67 | 3.0 | 3.0 | **4.0**（最高5.0） |
| login | 4.33 | **5.0** | 4.5 | **5.0** |

（来源：`firmware_ablation_summary.csv` / `firmware_ablation_runs.csv` / `firmware_skill_ablation_summary.md`）

### 2.5 讨论
- skill 内容差异确实改变 blind 结果——有证据；“注不注入都一样”不成立；
- 但存在平局（login 上 seed 与 relevant 打平），不能下“必要性”结论；
- 观察：seed（先分支、后 sink）写法比 relevant（先枚举面）在本任务更有潜力；
- 结论边界：证明“skill 影响结果”+“反馈闭环存在”，未证明“必要性阈值”。

### 2.6 产物文件
- `briefing_20260805/summary.md`、`firmware_skill_ablation_summary.md`、`firmware_ablation_{summary,runs}.csv`；
- skill 定义：`skillspace/ablation_profiles/cgi_cmdi_seed_dispatch/...`、`cgi_cmdi_relevant/...`；
- 原始 run：`runtime/imports/remote_vm/firmware2-*`、`firmware_ablation_20260805/`。

---

## 三、F453 skill 对照 + 闭环正例验证（force / disable / natural）

> 时间：约 2026-08-15。可信度：**中**（证明注入“真生效”+ 一条真实发布正例；不主张必要性）。

### 3.1 背景
此前的 firmware 消融证明 skill 内容影响结果；本组聚焦 F453 单一 blind case
（`f453-httpd-cmdinject-formWriteFacMac`），在 fixed 数据集/VM/模型/链路下只改变服务端 skill 条件，
进一步验证“注入是否真的改分析路径”，并测试能否触发 candidate→gate→published 真实正例。

### 3.2 研究问题
- Q1. server-side skill 注入是否真正改变（而非仅记录于）模型分析路径？
- Q2. 后端闭环 `run→feedback→candidate→gate→published` 能否在真实 run 上发生？
- Q3. 强制注入更泛化/更窄的 skill 是帮助还是伤害该 case？

### 3.3 实验设计与变量（条件）
| 条件 | 服务端 skill 设置 | 选中 skill | score | 结果 |
| --- | --- | --- | ---: | --- |
| A | disable | 无 | 8.0 | 跑偏 formexeCommand/CVE-2018-5767 |
| B | force tenda-httpd-goform-execommand-triage | 同上 | 8.0 | 仍跑偏 formexeCommand |
| C | force embedded-cgi-command-injection-triage | 同上 | 6.0 | 更早跑偏 /goform/ate TendaAte |
| D | force embedded-... + evolve-after-run | 同上 | 0.0 | 触发 candidate→gate→published 真实正例 |
| E | 自然检索 + evolve-after-run | 无 | 8.0 | live skill 未被自然选中，又跑偏 |

（来源：`briefing_20260815/f453_skill_ablation_20260815.md` + `f453_run_table_20260815.csv`）

### 3.4 讨论
- 条件 C 从 formexeCommand 进一步偏到 TendaAte：**注入确实改变分析路径**（非仅记录）；
- 条件 D：后端闭环真实正例成立（一次 publish 发生）；但条件 E：当前 live skill 未被自然检索选中，
  说明“发布发生”≠“自然检索会命中”——这呼应全局诚实前提；
- 强注入不合适 skill（C）分数下降：不合适的 skill 会主动带偏方向、甚至负效果；
- 该 case 上 Tenda 历史先验（formexeCommand/CVE-2018-5767）很强，模型易被显著字符串牵引。

### 3.5 产物文件
- `briefing_20260815/f453_run_table_20260815.{md,csv}`、`f453_skill_ablation_20260815.md`、`weekly_report_20260815.md`；
- 原始：`runtime/imports/remote_vm/f453-*`。

---

## 四、旧消融主数据（受污染基线，159 runs）【已作废/负面积累】

> 时间：约 2026-08 中旬（方案 A 之前）。可信度：**低/作废**——含技能泄答案作弊，仅作负面积累与复现对照。

### 4.1 背景
在净化改造之前，工程以同口径跑了 14 案例×多条件的消融，得到 oracle-skill 命中率 **97.5%** 的“亮眼”结果。
复审发现高命中主要来自**未净化的技能**——技能内容把目标函数名/诱饵/设备型号等答案线索拼进上游 prompt，
模型并非真实漏洞分析命中，而是“读答案”，属作弊。

### 4.2 研究问题
- Q1.（事后）旧数据在高命中率下，到底有多少是“真实命中”vs“技能泄答案”？
- Q2. 旧 oracle/weak/medium 各条件的可参考价值如何，能否直接进论文？

### 4.3 实验设计与数据（`ablation_results.csv`，159 行）
- 条件：no-skill / weak-skill / oracle-skill / weak-skill-2 / medium-skill（混合跑，非完整对称 3 条件）。
- 规模按条件：
  - no-skill: 42 runs（14 case），YES=1 (2.4%)，DECOY=18，NO=23
  - weak-skill: 40 runs（14 case），YES=3 (7.5%)，DECOY=19，NO=18
  - **oracle-skill: 40 runs（13 case），YES=39 (97.5%)**，DECOY=0，NO=0（作弊来源）
  - weak-skill-2: 22 runs（7 case），YES=4 (18.2%)，NO=17
  - medium-skill: 15 runs（5 case），YES=2 (13.3%)，9 行 correct 为空

### 4.4 关键判定
- oracle 40 条里 39 条 YES、仅 1 条空 → 旧 97.5% 的来源，现确认为技能泄答案；
- 该份 CSV **未删除**，原始行级数据完好，可随时复现“作弊口径”，用于说明方法学前后的重要性。

### 4.5 讨论与可信度
- 不可作为论文正向证据；仅可作“若不净化会怎样”的对照/警示，或作为复现旧结论的存档；
- 与方案 A（clean 35.7%）合起来正是论文方法学“净化防作弊”的必要性论据。

---

## 五、方案 A：三条件清洁对比实验（可信主结果，84 runs）

> 时间：2026-08-20。模型：deepseek-v4-flash（C402-DSv4Flash-Codex）。可信度：**高**（净化+新模型+防作弊）。

### 5.1 背景与动机（为什么重跑）
上一版 159-run（oracle 97.5%）含技能泄答案作弊。commit `8186f34` 完成净化改造后，
决定用新模型全量重跑同口径实验，以获得可信清洁基线，回答“旧高命中到底是真实还是作弊”。

### 5.2 研究问题
- Q1. 旧 oracle 97.5% 在净化后剩多少？即旧 39/40 有多少是技能泄答案所得？
- Q2. 清洁下 oracle-skill 是否仍优于 weak/no？即技能是否带来“必要性”收益？

### 5.3 净化改造内容（commit 8186f34）
1. 盲测 prompt 抹掉答案线索（目标/诱饵/设备型号等）；
2. 修复运行期 OOM；
3. inline skills 不再注入 catalog（避免库见底副作用）；
4. 新增 14 案例 + elf weak skill（统一 weak 基线）。

### 5.4 实验设计与数据
- 案例：14 个 HTTP handler/cgi 入口 case；条件：no-skill / weak-skill / oracle-skill；每 case×条件 2 轮；
- 规模：14×3×2 = **84 runs**；执行：远端 VM blind（`evaluation.runs.run_remote_case`）；
- 结果文件：`runtime/ablation/results/ablation_results_rerun_model.csv`；运行：84/84 completed，约 68 分钟。

### 5.5 主要结果
| 条件 | runs | YES | DECOY | NO | 平均分 |
| --- | ---: | ---: | ---: | ---: | ---: |
| no-skill | 28 | 1 (3.6%) | 9 | 18 | 4.38 |
| weak-skill | 28 | 4 (14.3%) | 12 | 12 | 4.34 |
| oracle-skill | 28 | 10 (35.7%) | 1 | 17 | 6.32 |

**核心对照**：oracle 97.5% → clean 35.7%（-62pp）→ 证旧 39/40 主要来自技能泄答案，非真实命中。

### 5.6 逐案例×条件 YES（关键细节）
| case | target | no | weak | oracle |
| --- | --- | ---: | ---: | ---: |
| f1202-cmdinject | formWriteFacMac | 0/2 | 1/2 | 0/2 |
| f1202-credential-overflow | fromAdvSetWan | 0/2 | 0/2 | 0/2 |
| f453-cmdinject | formWriteFacMac | 0/2 | 0/2 | 2/2 |
| f453-overflow | formWrlsafeset | 0/2 | 1/2 | 2/2 |
| f453-qossetting-overflow | fromqossetting | 0/2 | 0/2 | 0/2 |
| f453-routestatic-overflow | fromRouteStatic | 0/2 | 0/2 | 2/2 |
| f456-cmdinject | formWriteFacMac | 0/2 | 0/2 | 1/2 |
| f9k1122-crossband-overflow | formCrossBandSwitch | 0/2 | 0/2 | 0/2 |
| f9k1122-overflow | formWISP5G | 0/2 | 2/2 | 2/2 |
| f9k1122-setpassword-overflow | formSetPassword | 0/2 | 0/2 | 0/2 |
| f9k1122-setsystemsettings-overflow | formSetSystemSettings | 1/2 | 0/2 | 0/2 |
| f9k1122-wlansetup-overflow | formWlanSetup | 0/2 | 0/2 | 0/2 |
| fh451-formWrlExtraSet-overflow | formWrlExtraSet | 0/2 | 0/2 | 1/2 |
| i12-pathtraversal | R7WebsSecurityHandler | 0/2 | 0/2 | 0/2 |

### 5.7 讨论
1. 净化效应确认：oracle 97.5%→35.7%；
2. oracle 仍高于 no/weak（35.7>14.3>3.6），但未完全碾压——28 个 oracle run 中仍有 17 NO、1 DECOY；
3. F9K1122 家族是主要拖累：4 个非 WISP 目标（crossband/setpassword/setsystemsettings/wlansetup）
   oracle 下几乎全 MISS，反复被预测成同家族“最显眼”的 formWISP5G → 触发后续“族内区分”改良；
4. oracle 控诱饵能力显著增强：DECOY 从 no/weak 的 9~12/28 降到 oracle 1/28；
5. **skill 必要性仍未证明**：clean 下 oracle 仅部分 case 领先，尚不能断言“必须用该 skill 才能找到目标”。

### 5.8 setpassword 数据缺陷说明（重要）
- `f9k1122-webs-overflow-formSetPassword.json` 实为 `formSetSystemSettings.json` 复制件（仅 case_id/notes 不同；
  ground_truth/blind_workspace/validator 全指向后者；源侧 webs 二进制 MD5 相同 205E6972...）。
- 因此 ablation 在“vul5 二进制上找 formSetPassword 这个不存在的目标”，其 0 命中是**数据集重复缺陷**，非 skill 盲区。
- 处理建议：作废或用 vul4 真样本重派生（需修正 run_ablation 的 target 与 case_file 一致性）。\n- **已处理（2026-08-20，path A）：case 已作废**（include_in_current_runs=false, publication_ready=false，promotion_blockers 与 notes 已写入作废说明）。ground_truth/validators/blind_workspace 保留原样以便审计。整改脚本：scripts/ops/fix_setpassword_case.py。

### 5.9 产物文件
- `runtime/ablation/results/ablation_results_rerun_model.csv`（84 行）、`ablation_log_rerun_model.txt`、`ablation_state_rerun_model.json`；
- 规范化表：`briefing_20260816/planA_clean_rerun_table_20260820.csv`；完整记录：`planA_clean_rerun_validation_20260820.md`；
- 原始 run：`runtime/imports/remote_vm/`。

---

## 六、F9K1122 族内区分型 oracle skill 验证（可信，15 runs）

> 时间：2026-08-20。模型：deepseek-v4-flash。可信度：**高**（净化、防作弊、不写函数名的隔离盲测）。

### 6.1 背景与动机
方案 A 中 F9K1122 的非 WISP 目标（crossband/setpassword/setsystemsettings/wlansetup）在 oracle 下几乎全 MISS，
反复被预测成同家族“最显眼”的 formWISP5G。逐条核查 oracle skill 发现 F9K1122 五份 content 逐字相同，
只写“webs overflow 通用方法论”，不区分族内目标 → 模型把通用方法论套到最出名的 handler。

### 6.2 研究问题
- Q1. 若不写死目标函数名，能否用**二进制的邻接符号指纹**把模型从家族内显眼 handler 掰回真实目标？
- Q2. 族内区分型 oracle 相对旧 generic-oracle 的命中率提升幅度？
- Q3. setpassword/setsystemsettings 这组近亲对是 skill 盲区还是数据层不可分？

### 6.3 实验设计与变量
- **核心方法**：把 oracle skill 重写为“族内区分型”——每份 skill 只描述该目标在二进制字符串表中的**邻接符号指纹**
  （引导模型靠符号相邻关系锁定目标），**不写目标函数名、不泄答案**。素材来自 `runtime/ablation/werk/f9k_neighborhood.json` / `f9k_strings.json`。
- 新技能：`oracle-f9k-distinguishing-*.json`（5 份：wisp5g / crossband / wlan-setup / set-system-settings / set-password）。
- runner：`runtime/ablation/run_f9k_distinguish.py`（独立 output-tag `f9k_distinguish_oracle`，不碰 rerun_model CSV）。
- 规模：5 case × oracle × 3 轮 = 15 runs；对照：同批 F9K 旧 generic-oracle（5 case × 2 轮 = 10 runs，取自 plan A）。

### 6.4 结果（per-case YES/总）
| case | 旧 generic-oracle | 新 distinguishing | 新预测 |
| --- | ---: | ---: | --- |
| f9k1122-overflow (formWISP5G) | 2/2 | 3/3 | formWISP5G ✓ |
| f9k1122-crossband-overflow | 0/2 | **3/3** | formCrossBandSwitch ✓（重新掰回） |
| f9k1122-wlansetup-overflow | 0/2 | **3/3** | formWlanSetup ✓（重新掰回） |
| f9k1122-setpassword-overflow | 0/2 | 0/3 | formSelfHealing/formWISP5G ✗ |
| f9k1122-setsystemsettings-overflow | 0/2 | 1/3 | formSetSystemSettings(r1) / formWISP5G(r2,r3) |
| **汇总** | **2/10 (20%)** | **10/15 (66.7%)** | — |

### 6.5 讨论
- 不写函数名、基于邻接符号指纹的 skill 能把 crossband/wlansetup 从全被 formWISP5G 带偏稳定掰回正确 handler，
  命中率约 3 倍回升（20%→66.7%），且不泄答案；
- 顽固近亲对 setpassword/setsystemsettings：同份 webs 里 formSetSystemSettings(445) 与 formSetPassword(446) 是相邻符号，
  邻接 token 完全相同，二进制层面无区分 token；唯一可区分的是 poc 打哪个 /goform/* 端点（oracle-only、不给模型）
  → 属**数据层不可分**，非 skill 盲区（并叠加 5.8 的复制缺陷）。

### 6.6 可信度与论文参考
- 可信度：高。这是“怎么写才有效且不泄答案”的正面证据，直接支撑论文方法学（邻接指纹技能塑造）。

### 6.7 产物文件
- 技能：`runtime/ablation/oracle_skills_json/oracle-f9k-distinguishing-*.json`（5 份）；runner：`run_f9k_distinguish.py`；
- 结果：`runtime/ablation/results/ablation_results_f9k_distinguish_oracle.csv`（15 行）、`f9k_distinguish_run.log`；
- 邻接素材：`runtime/ablation/werk/f9k_neighborhood.json`、`f9k_strings.json`；
- 记录：`briefing_20260816/f9k_distinguishing_validation_20260820.md` + `f9k_distinguishing_run_table_20260820.csv`。

---

## 七、其余辅助/存疑实验（FH451 / sanity / closed-loop）

### 7.1 FH451 五 case 四条件对照（60 runs，数据无效待排查）
- 规模：5 个 FH451 case × 4 条件（no/weak/weak-skill-2/oracle）× 3 轮 = 60 runs；文件 `ablation_results_fh451.csv`。
- 结果：四条件 YES 全 = 0，且 oracle 15 行全空、其余各约 12/15 的 correct 为空 → 基本无可判读输出，**数据无效**。
- 结论：不能作证据；需排查 FH451 case 构造（同名 formWrlExtraSet 冲突）或模型输出解析问题后重做。

### 7.2 sanity 冒烟测试（2 runs，无统计意义）
- 1 case（f453-cmdinject）× no/oracle 各 1 轮，验证实验台能跑通即可；一次 DECOY、一次 NO。文件 `ablation_results_sanity.csv`。
- 作用：流程调通验证，不作结论。

### 7.3 Closed-loop proof（供应链闭环证明）
- 文件：`briefing_20260805/closed_loop_proof.csv`。
- 证明：handoff 发生、evolve 消费 receipt、candidate job 入队、validation follow-up 存在；
- 未证明：发布进 live、可测的发布后收益——与全局诚实前提一致。

### 7.4 最原始 per-run JSON 全量盘点（`runtime/imports/remote_vm`）
- 总 runsets：456；总 final/score JSON：3138。
- 分布：f9k 129/903、f453 103/720、firmware 59/405、i12 41/287、f1202 36/252、giflib 28/174、fh451 15/105、
  tcpdump 10/64、exiv2 6/37、libxml 6/38、libarchive 4/27。
- 意义：每次运行的完整会话记录（final-enriched.json 含预测函数/CVE/打分明细）全部保留，可任意回溯单条 run 做归因/复现。

---

## 八、可信度汇总矩阵与论文写作映射

| 实验 | runs | 可信度 | 论文用途 |
| --- | ---: | --- | --- |
| 六核心 blind | 6 | 中 | 方法学“闭环可跑”奠基 |
| Firmware CGI 消融 | 16 | 中 | skill 内容影响结果 |
| F453 对照+闭环正例 | ~16 | 中 | 注入真生效 + 一条发布正例 |
| 旧消融（作弊） | 159 | 低/作废 | 负面积累 / 净化必要性对照 |
| 方案 A clean | 84 | **高** | 主基线（97.5→35.7） |
| F9K 族内区分 | 15 | **高** | 邻接指纹方法学正面证据 |
| FH451 | 60 | 无效 | 待重做 |
| sanity | 2 | 无意义 | 流程验证 |

### 论文写作可直接引用的核心数字
- 旧 oracle 97.5% → clean 35.7%（-62pp）→ 证“不净化=作弊”的方法学必要性；
- clean 下 oracle(35.7%) > weak(14.3%) > no(3.6%)；oracle DECOY 仅 1/28 vs no/weak 9~12/28；
- 族内区分 oracle：20% → 66.7%（不写函数名、用邻接指纹）→ “怎么写才有效且不泄答案”；
- 诚实边界：skill 必要性（“必须用它才能找到漏洞”）仍未在 clean 数据上证明，论文严禁套旧 54/54 类强结论。

## 九、遗留数据缺陷与风险（常驻）
1. setpassword case 是 setsystemsettings 的复制件（数据集 bug，非 skill 盲区）→ **已于 2026-08-20 作废（path A）**，见 5.8；
2. setpassword/setsystemsettings 二进制不可分（相邻符号 token 相同）→ **已定为「不可区分类别」口径（2026-08-20）**：不计入 per-function 命中分母，单独列类别汇报；setpassword 复制件另作废（见 §5.8）；
3. 评分/确认的语义盲区（规则级匹配、artifact 级确认为主，无行为级模拟器）；
4. gate 的 tool-free replay 与“description→检索”未覆盖，使 gate 通过 ≠ 真实有效；
5. 无发布后效果追踪/回退，唯一发布（v8）反向检索更差；
6. 反馈 attribution 是 observational 非 causal。

---
*本文档为“全部实验档案”，由脚本/手工依据原始 CSV/JSON/handoff 整理生成（2026-08-20）。
*逐行数据以原始文件为准；本文档用于长期追踪、重新评估与论文写作参考。*