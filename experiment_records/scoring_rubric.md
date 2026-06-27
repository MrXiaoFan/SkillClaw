# SkillClaw 漏洞定位实验评分规则

本规则用于小规模 case-level 对照实验，目标是判断 SkillClaw skill 是否真实改善漏洞定位，而不是评价回答文风。

## 总分

默认满分 10 分。每个 case 可以在 `experiment_cases/*.json` 中覆盖权重。

| 项目 | 默认分值 | 说明 |
| --- | ---: | --- |
| CVE 命中 | 2 | 输出正确 CVE 或等价 advisory。若 case 未指定 CVE，则该项可记为不适用。 |
| 文件命中 | 2 | 命中 ground truth 文件，例如 `HTMLparser.c`。 |
| 函数命中 | 3 | 命中 ground truth 函数，例如 `htmlParseTryOrFinish`。 |
| 根因解释 | 2 | 能说明边界条件、数据流、状态机或危险访问为什么成立。 |
| 验证证据 | 1 | 提供 PoC、ASan、crash stack、patch diff、source guard 或 checker 等可核验证据。 |

## 评分原则

1. 优先看漏洞定位质量，不因回答很长而加分。
2. 输出多个候选时，如果 top-1 不正确但 top-3 包含正确点，可以给部分分。
3. 错误 CVE 编号需要扣分，即使命中文件和函数。
4. 只列危险函数或 PLT 导入，不算根因解释。
5. 如果 SkillClaw 选错 skill 导致分析路径明显偏移，应记录为 `skill_mismatch`。
6. 如果模型误调用 Claude Code 本地 `Skill(...)` 并报 unknown skill，但随后正确使用 server-side injected skill，可记录为执行器噪声，不直接扣定位分。

## 建议记录字段

每次实验至少记录：

```json
{
  "case_id": "libxml2-2.9.4-cve-2017-8872",
  "mode": "skillclaw-inline",
  "model": "deepseek-v4-pro",
  "session_id": "",
  "selected_skills": [],
  "skill_prompt_hash": "",
  "predicted_cves": [],
  "predicted_files": [],
  "predicted_functions": [],
  "score": 0,
  "matched": {},
  "validation_status": "",
  "failure_reason": ""
}
```
