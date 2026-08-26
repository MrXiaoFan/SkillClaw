# 2026-08-20 · 阶段 0.4 + 阶段 1 完结交接（GPT/Codex → 下一模型）

> 交接日期：2026-08-20 · 分支：`dev`（领先 codeup/dev 41 个提交，未 push）
> 前置阅读：`docs/handoff/20260815/01_gate_fix_and_paper_draft_handoff.md`、
> `docs/plans/work_plan_20260820.md`（操作级）、`docs/plans/research_roadmap_20260820.md`（战略）
> 本轮所有实验记录产物在 `reports/current/briefing_20260816/`

---

## 0. 一句话状态

「skill 必要性」实证链路（0.x 数据可信化 + 1.x 必要性）已阶段性完结并全部提交：
oracle 46.7% vs weak 11.1% vs no 6.7%，诱饵 28→2，且已给出 28 个 oracle-NO 的逐 case 归因；
族内区分验证了「收益 family-dependent」。剩余工作是 2.x 系统完整性 + 3.x 论文对齐。

---

## 1. 本轮完成并已提交的成果

| commit | 内容 |
| --- | --- |
| `b60aae1` | Plan 0.3 冻结 25-case 集 + benchmark protocol（固定 ref 01f5830） |
| `60b7d2a` | Plan 1.1 三条件必要性 153-run（no 6.7 / weak 11.1 / oracle 46.7，DECOY 28→2） |
| `2e28257` | Plan 1.2 FH451 族内区分（负结果 4/15 vs generic 6/15） |
| `18d6f02` | Plan 1.3 逐 case 归因 + Plan 0.4 FH451 旧数据处理 |
| `227324c` | 8.23 周报草稿补 1.3/0.4 两行 |
| `f46a66a` | 根目录 AGENT_HANDOFF.md 追加本次交接小节 |

### 关键结论速览
- **1.1**：冻结口径下 oracle 46.7% ≈ no 的 7 倍、weak 的 4.2 倍；诱饵命中 28→2（控诱饵强）；
  但 oracle 仍 48.9% NO，**严格必要性未证**。
- **1.2（负）**：FH451 高密度簇邻接/参数 token 重叠，邻接指纹无法唯一区分，distinguishing 4/15 < generic 6/15；
  仅对字符串表分离度高的家族（F9K，20%→66.7%）有效 → **family-dependent，非通用**。
- **1.3**：28 个 oracle-NO round 归因 5 类——区分度不够 A+B+D=21/28≈75% 主导、数据集缺陷 C=3、
  模型能力 E=4。产物 `plan1_necessity_attribution_20260820.md/.csv`。
- **0.4**：旧 60-run（error 51/60、correct 空白 51、oracle 15 行全空）**作废（superseded）**，
  已由冻结 153-run（45 completed）+ 族内区分 15-run 取代；archive §7.1 标注已作废。

---

## 2. 交给下一模型的后续（按 work_plan/roadmap 优先级）

1. **2.3** 检索回归（D4：gate 加 description→检索断言）+ catalog 对比（D3 延伸）；
2. **2.2** 发布后效果追踪 + 回退（D5，hold-out 前后对比）；
3. **3.x** 论文对齐（v2 tex 换旧 18 case/213 run 口径，写入净化/作废/族内区分/gate 边界 D3/D5/D6 诚实标注）；
4. **4.1** 8.23 周报定稿（草稿已补 1.3/0.4 行，见 `weekly_report_20260823_draft.md`）。
5. **4.5** `paper/` 生成物（.tex/.aux/.log/.pdf）决定是否入 .gitignore（当前未跟踪）。

---

## 3. 坑与交接提醒

- **archive §7.1 是 UTF-8 BOM + CR/CRLF 混合格式**：改它必须用 Python 明确指定编码和换行，
  禁止 PowerShell `Set-Content`（会把整份 1300 行触发成全量 diff，已踩过并修复）。
- **文件编码纪律**：本仓库多数 .md/.csv 为 UTF-8 BOM（或 CRLF）。追加/改写一律用 Python 显式以
  `utf-8`（必要时 `-X utf8`）处理，核对 BOM/换行，避免 PowerShell 把中文转成乱码（本会话已踩过两次）。
- **桌面文档不能直接当真源**：
  - `C:\Users\Fan\Desktop\20260823weekly.docx` 只覆盖到较早一轮，未纳入 2026-08-20 的 84-run / 153-run / F9K / FH451 主证据；
  - `C:\Users\Fan\Desktop\工程状态（新版）.docx` 当前内容是乱码，不适合继续作为工程状态入口；
  - 桌面周报/工程状态如需继续使用，必须先按 `reports/current/briefing_20260816/` 与 `reports/current/experiment_archive_all_20260820.md` 回填。
- **未跟踪历史文件不要提交**：`paper/*`、`reports/current/_tmp_*`、旧 briefing（engineering_status/glm_handoff/
  session_archive/session_rollout/startup_checklist/weekly_report_20260816）、`scripts/ops/_*.py`。
- 所有数字以原始 CSV 为准；**论文严禁旧 18 case/213 run/53-of-54/严格必要 的强结论**。
- 当前 plan 状态总览：0.1–0.4 ✅、1.1 ✅、1.2 🔶（部分否定）、1.3 ✅、2.1 ✅；2.2/2.3/3.x/B.x 待做。
