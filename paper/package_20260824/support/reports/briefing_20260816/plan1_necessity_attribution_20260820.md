# 阶段性工作记录：方案 1.3 逐 case 归因（oracle 未命中 NO 案例分析）— 2026-08-20

> 归属：research_roadmap / work_plan **1.3「逐 case 归因」**。
> 研究问题：在冻结 153-run（plan11_frozen）中 oracle-skill 未命中（NO）的案例，究竟该归因于
> 「**模型能力不足**」还是「**oracle 区分度不够**」？——这决定了后续 1.2 族内区分推广该往哪使劲。

## 1. 数据来源
- 冻结 153-run：`runtime/ablation/results/ablation_results_plan11_frozen.csv`（17 case × 3 cond × 3 rounds，全 completed）。
- oracle-skill 共 51 行：YES 21、DECOY 2、**NO 28**。
- 近亲（不可区分）对（setsystemsettings + wlansetup，0.2 口径）单列；主分母 n=45 中 oracle NO=22。

## 2. 归因框架
把 oracle-NO 划分成五类（evidence-grounded，非猜测）：

| 类 | 含义 | 判据 |
| --- | --- | --- |
| **A · oracle 区分度不够（可修复，已验证）** | generic oracle 只给方法论，不给族内区分判据 → 模型漂到族内"最显眼"handler；**且已被族内区分型 skill 实际救回** | F9K distinguishing 已把该 case 3/3 掰回 |
| **B · oracle 区分度不够（高密度簇，指纹亦不足）** | FH451 簇重叠度过高，邻接/参数 token 无法唯一区分；族内区分型 skill 也无法稳定救回 | FH451 distinguishing 结果不佳 |
| **C · 数据集缺陷** | target 名在二进制中不存在（fromSetCfm 实为 formSetCfm），目标名永远无法命中 | 二进制字符串表核实 + 0 命中 |
| **D · oracle 区分度不够（可能性高，未用区分型验证）** | 同固件内漂到其它 handler，模式与 A 一致，但该家族尚未用区分型 skill 验证 | 漂移模式 + 无验证 |
| **E · 模型能力 / 注意力（oracle 也拖不住）** | oracle 在场仍被抓走，含被诱饵 DECOY 带走 | oracle 下仍 DECOY/漂移 |

## 3. 归因汇总表
详细逐 case 见搭配 CSV：`plan1_necessity_attribution_20260820.csv`。

| 类 | case(s) | oracle-YES/合计 | oracle-NO rounds | 证据要点 | 处置建议 |
| --- | --- | ---: | ---: | --- | --- |
| A | f9k1122-crossband / -wlansetup / -setsystemsettings | 0/9 | 9 | generic 全漂 formWISP5G；**crossband/wlansetup 被区分型 3/3 救回**，setsystemsettings 1/3 | 用区分型 skill（近亲对按 0.2 单列） |
| B | fh451-WrlclientSet / -formWrlExtraSet / -fromAdvSetWan | 2/9 | 6 | FH451 簇重叠高；区分型 1-2/3 不稳定（WrlclientSet 仅 1/3） | 非纯字符串邻接特征（调用图/dispatch），或接受残余误差 |
| C | fh451-fromSetCfm | 0/3 | 3 | 二进制仅 formSetCfm（0x30eb），fromSetCfm 零出现 | 数据层订正命名；非 skill 可修 |
| D | f1202-credential / f453-qossetting | 0/6 | 6 | 同固件漂到 formDefinePwd/getwebuserpwd/formWrlsafeset/formBulletinBoard 等 | 可加区分型 skill 尝试（未验证） |
| E | f453-cmdinject / f453-routestatic / i12-pathtraversal | 2/9 | 4 | f453-cmdinject oracle 下仍 2 次 DECOY 命中诱饵 formexeCommand（NO=0，DECOY=2，另列）；f453-routestatic/i12 各 2 次 NO（漂 formWrlAdvset/formWrlsafeset、request_authenticate_gatekeeper 等） | 模型能力/注意力为主，oracle 收益有限 |

- 合计：A+B+C+D+E 覆盖 28 个 oracle-NO round（9+6+3+6+4=28）✓ 与 CSV 一致。

## 4. 量化小结（oracle-NO 归因占比，按 round）
| 归因方向 | rounds | 占比 | 说明 |
| --- | ---: | ---: | --- |
| oracle 区分度不够（A，已验证可修） | 9 | 32.1% | 已证实是 skill 盲区而非模型盲区 → 用区分型有效 |
| oracle 区分度不够（B+D，簇/同固件） | 12 | 42.9% | 区分型可部分/尝试覆盖（FH451 高密度簇不如 F9K） |
| 数据集缺陷（C） | 3 | 10.7% | 数据层修复，非建模问题 |
| 模型能力/注意力（E） | 4 | 14.3% | oracle 也拖不住的硬样本 |

## 5. 结论（对 1.2 推广的启示）
1. **oracle-NO 中"区分度不够"（A+B+D=21/28=75%）占主导**，多数是"同一固件内选错 handler"，
   印证 plan1_necessity_frozen §3.5 的推断：generic oracle 缺少族内区分判据。
2. 但 **1.2 的 FH451 推广结果是负的**（distinguishing 4/15 < generic 6/15），说明"区分度不够"并不等于
   "邻接指纹一定救得回"——**可修性随家族字符串表分离度而异**（A 类 F9K 分离度高可修；B 类 FH451 高密度簇不可修）。
3. **C 类（fromSetCfm）是数据集缺陷**，必须数据层订正，任何 skill 都无法修复。
4. **E 类（14.3%）是模型能力硬样本**，oracle 收益有限，是"严格必要性未证"的主要残余来源。

## 6. 可信度
- **中-高**：基于 153-run 全 completed 数据 + 二进制字符串表核实 + 与 distinguishing 实验交叉验证；
  但 B/D 类的"可修性"判断对未做区分型验证的家族（D 类 f1202/f453)是推断性，待验证。

## 7. 产物
- 规范表：`reports/current/briefing_20260816/plan1_necessity_attribution_20260820.csv`
- 本文档：`reports/current/briefing_20260816/plan1_necessity_attribution_20260820.md`
- 原始数据：`runtime/ablation/results/ablation_results_plan11_frozen.csv`（.gitignore）

