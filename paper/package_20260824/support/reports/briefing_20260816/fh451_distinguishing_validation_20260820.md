# 阶段性工作记录：FH451 族内区分型 oracle skill 验证（2026-08-20）

> 结论先行：**F9K1122 上验证成功的"族内区分型 skill（二进制邻接符号指纹）"并未泛化到 FH451**。
> FH451 5 案例上，新 distinguishing oracle 命中 4/15（26.7%），反而低于同批 generic-oracle 基线的 6/15（40.0%）。
> 根因：FH451 的 webs 字符串表中脆弱 handler 及其近邻都聚集在重叠度极高的无线/WAN 集群里，
> 邻接符号指纹 + 参数 token 无法把目标与"语义同名"的邻近 handler 唯一区分，模型往往把指纹匹配到
> 邻近的同族符号（fromWanPortParam / formWrlLoginfo / formWrlwpsset / formSetCfm / formSafeWebtypeFilter），
> 而非目标。

## 背景与动机
- 方案 1.1 三条件必要性实验（153 runs，frozen case set，commit 60b7d2a）逐案例排查显示，oracle-skill
  命中率 46.7%，但仍有若干 case 在 oracle 下判 NO（oracle 全不中/部分命中），预测 drift 到同家族其他 handler。
- 方案 1.2 目标：把 1.1 里 oracle 全不中/部分命中的 case 从 family-NO 掰回真实目标，复用已在 F9K1122 上
  验证有效的"邻接符号指纹"族内区分 skill（见 f9k_distinguishing_validation_20260820.md：F9K 20%->66.7%）。
- 选择 FH451 作为首个推广对象：FH451 全部 5 个 vul 样本共享同一份 httpd 二进制（MD5 e211979e），
  是标准的族内区分场景；且 FH451 是 1.1 里 oracle 命中率偏低的家族（formWrlExtraSet 2/3、WrlclientSet 0/3、
  fromSetCfm 0/3、fromAdvSetWan 1/3、formQuickIndex 3/3，合计 6/15）。

## 实验设计
- 新技能：runtime/ablation/oracle_skills_json/oracle-fh451-distinguishing-*.json（5 份，对应 5 个目标 case）
  - 指纹类型：同 F9K——只依据二进制字符串表**可观察**特征（handler 符号邻接 PREV/NEXT 序列、参数名 token、
    格式串），不写目标函数名/设备型号/CVE。
  - 说明：5 个目标里 fromSetCfm 的二进制符号实为 formSetCfm（见下"数据集缺陷"），skill 按 formSetCfm 描述。
- 跑步器：runtime/ablation/run_fh451_distinguish.py（独立 output-tag `fh451_distinguish_oracle`，不碰 frozen CSV）
- 规模：5 case x oracle-skill x 3 rounds = 15 runs，deepseek-v4-flash，净化盲测
- 对照 baseline：同批 5 个 FH451 case 的 generic-oracle 结果（ablation_results_plan11_frozen.csv，oracle-skill，
  5 case x 3 rounds = 15 runs）

## 结果对比（per-case oracle 命中 YES 率：旧 generic → 新 distinguishing）
| case_key | 旧 generic-oracle | 新 distinguishing | 预测（新） |
| --- | --- | --- | --- |
| fh451-formWrlExtraSet-overflow | 2/3 | 1/3 | formWrlsafeset / formSafeWebtypeFilter / formWrlExtraSet |
| fh451-WrlclientSet-overflow | 0/3 | 1/3 | formWrlclientSet / formWrlLoginfo / formWrlwpsset |
| fh451-fromSetCfm-overflow | 0/3 | 0/3 | fromListDataSave / formSetCfm / formSetCfm |
| fh451-fromAdvSetWan-overflow | 1/3 | 0/3 | fromWanPortParam / formWrlAdvset / fromWanPortParam |
| fh451-formQuickIndex-overflow | 3/3 | 2/3 | formQuickIndex / fromWanSetWan / formQuickIndex |
| **汇总** | **6/15 (40.0%)** | **4/15 (26.7%)** | — |

关键结论（与 F9K 相反）：邻接符号指纹在 FH451 上**没有**把 family-NO 掰回目标，反而轻微回退。这与 F9K 的
66.7% 正向结果形成对比，说明"族内区分型 skill 可泛化到其它家族"这一假说**不成立**——至少对 FH451 这种
handler 高密集群不成立。

## 失败模式归因（为什么会比 generic 更差或持平）
逐 run 读 agent 最终输出后，失败主要分三类：

1. **邻接锚点被模型忽略，转而匹配"语义同名"的近邻符号（WAN 集群）**
   - fromAdvSetWan 3/3 全 NO：指纹准确给出 `aspTendaGetDhcpClients, TARGET, formWrlsafeset, formWebTypeGroup,
     aspmGetRouteTable...` 邻接 + `wanmode/WANPORT/reboot/wan%d.isp/delay_restart_multiWAN` token 集群。
     但模型读到 WAN per-port + delay_restart_multiWAN 后，把答案定为 `fromWanPortParam`（0x32a8，语义更贴合
     "port param + wan%d.*"），而 fromWanPortParam 并不在描述的邻接运行里。即：模型按"名字听起来对"而非
     邻接锚点定位。
   - formQuickIndex r2 判成 `fromWanSetWan`：同样是 WAN 集群语义漂移。

2. **无线集群内近邻符号互相冒充（wrl*/form* 同前缀簇）**
   - WrlclientSet：r1 给 `formWrlclientSet`（近似但非目标，碰巧包含子串判 YES）、r2 `formWrlLoginfo`、
     r3 `formWrlwpsset`——都在同一无线 wrl* 簇。formSafeWebtypeFilter（formWrlExtraSet r2）同理。
   - 根因：这些符号同处一个无线 block，PREV/NEXT 邻居重叠度极高，指纹的"邻接运行"几乎相同，
     模型在这些同簇符号间任选其一。

3. **数据集缺陷（fromSetCfm）**
   - fh451-fromSetCfm 的 ground_truth functions 是 `fromSetCfm`，但 FH451 httpd 字符串表里**只有 `formSetCfm`**
     （0x30eb），`fromSetCfm` 字节序列在二进制中零出现（0 命中）。模型给 formSetCfm（r2,r3）或
     fromListDataSave（r1）都判 NO——因为 `fromSetCfm` 子串不匹配 formSetCfm，且目标名不在二进制里。
   - 这是数据集命名不一致（target 用 `fromSetCfm`，二进制用 `formSetCfm`），与 F9K setpassword 的性质类似：
     二进制层面根本无法命中目标名，非 skill 质量所能修复。

## 与 F9K 成功的结构性差异（为何不泛化）
| 维度 | F9K1122（成功） | FH451（失败） |
| --- | --- | --- |
| 目标 handler 在字符串表的分布 | 5 个目标符号彼此**充分分离**，各有唯一、不重叠的邻接运行 | 5 个目标及其近邻聚集在**重叠度极高的无线/WAN 集群** |
| 指纹唯一性 | 邻接运行可作为排他锚点 | 邻接运行几乎相同，token 被多个近邻共享 |
| 语义同名干扰 | 低（簇内概念边界清晰） | 高（fromWanPortParam / formWrl* 等语义相近） |

教训：邻接符号指纹的区分能力**依赖目标在字符串表中的分离度**；对高密度、同前缀、共享参数 token 的
handler 簇，纯二进制邻接/参数指纹不足以保证唯一性，模型会退回到"语义取名"导致按错误符号作答。

## 产物清单
- 技能：runtime/ablation/oracle_skills_json/oracle-fh451-distinguishing-*.json（5 份）
- 跑步器：runtime/ablation/run_fh451_distinguish.py
- 原始结果：runtime/ablation/results/ablation_results_fh451_distinguish_oracle.csv（15 行）
- 邻接/参数素材：runtime/ablation/werk/fh451_neighborhood.txt、fh451_handler_neighbors.txt、fh451_sources.txt、fh451_widen.txt
- 本记录：reports/current/briefing_20260816/fh451_distinguishing_run_table_20260820.csv + 本 md
- 注：runtime/ 在 .gitignore 中未纳入 git；reports/ 下本 md 与 table 供版本化/汇报。

## 下一步（建议）
1. **不再简单复用 F9K 指纹模板**推广到高密度簇家族；先做"字符串表分离度"预判（目标符号 PREV/NEXT 是否
   与近邻唯一可辨），只在可辨家族上应用族内区分型 skill。
2. fromSetCfm / formSetCfm 命名不一致应在数据层订正（统一 target 名与二进制符号名），否则该 case 永远判 NO。
3. 对 FH451 这类近邻完全相同的高密度簇，考虑引入其它可观察特征（函数交叉引用/调用图、可执行区段的
   dispatch 表序）而非纯字符串邻接。
4. 族内区分推广实验的结论应写入 roadmap：区分型 skill 的收益是 family-dependent，非通用增益。
