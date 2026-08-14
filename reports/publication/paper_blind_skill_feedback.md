# 技能反馈汇总

这份文件把 final record 聚合成技能级反馈证据。
它不是全局质量分，只反映当前基准案例集中的表现。

| skill | selected_count | positive | neutral | negative | mean_score | validation_passed | validation_partial | validation_failed | artifact_generated | artifact_execution_passed | relevant_selected | mismatched_selected | infra_selected | file_hits | function_hits | cve_hits | actions | cases |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| source-parser-state-machine-oob | 3 | 0 | 2 | 1 | 0.6 | 3 | 0 | 0 | 3 | 3 | 2 | 1 | 0 | 2 | 2 | 0 | inspect_retrieval_before_promoting_skill:1, inspect_skill_mismatch_or_deprecate:1, revise_cve_identity_before_promotion:1 | giflib-5.1.2-cve-2016-3977, libxml2-2.9.4-cve-2017-8872, tcpdump-4.9.1-cve-2018-14469 |
| elf-cwe120-plt-analysis | 3 | 0 | 3 | 0 | 0.6 | 3 | 0 | 0 | 3 | 3 | 0 | 3 | 0 | 2 | 2 | 0 | inspect_retrieval_before_promoting_skill:1, inspect_skill_mismatch_or_deprecate:1, revise_cve_identity_before_promotion:1 | giflib-5.1.2-cve-2016-3977, libxml2-2.9.4-cve-2017-8872, tcpdump-4.9.1-cve-2018-14469 |

## 解读

- `positive/neutral/negative` 来自 run 级别的反馈决策。
- `mismatched_selected` 表示该技能虽然被选中，但与任务并不对齐，因此不应获得正向 credit。
- `mean_score` 是该技能被选中时的平均归一化定位分。
- `artifact_generated` / `artifact_execution_passed` 汇总的是 confirmation 导向的工件检查结果。
- 如果某个技能的样本数很少，只能视为轶事性证据，不能直接当稳定排序。
