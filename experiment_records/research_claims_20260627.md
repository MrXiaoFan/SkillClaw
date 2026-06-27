# Research Claim Summary

## Scope

- Cases: 3
- Runs: 15
- SkillClaw runs: 8
- Direct LLM runs: 7

## Case-Level Summary

| case_id | SkillClaw best | Direct best | SkillClaw low budget | Direct low budget | SkillClaw high budget | Direct high budget | selected skills |
| --- | --- | --- | --- | --- | --- | --- | --- |
| giflib-5.1.2-cve-2016-3977 | skillclaw-inline-guarded=10/10 | direct-deepseek-guarded=8/10 | n/a | n/a | n/a | n/a |  |
| libxml2-2.9.4-cve-2017-8872 | skillclaw-inline=8/10 | direct-deepseek-guarded-clean-budget080=10/10 | skillclaw-inline-guarded-clean-budget035=0/10 | direct-deepseek-guarded-clean-budget035=0/10 | skillclaw-inline-guarded-clean-budget080=8/10 | direct-deepseek-guarded-clean-budget080=10/10 | source-parser-state-machine-oob, skillclaw-proxy-introspection, skillclaw-skill-discovery |
| tcpdump-4.9.1-cve-2017-13031 | skillclaw-inline=8/10 | direct-deepseek=8/10 | skillclaw-inline-guarded-clean-budget035=8/10 | direct-deepseek-guarded-clean-budget035=0/10 | n/a | direct-deepseek-guarded-clean-budget080=8/10 | skillclaw-proxy-introspection, skillclaw-claude-env, skillclaw-skill-discovery |

## Conservative Observations

- giflib-5.1.2-cve-2016-3977: direct LLM also localized the vulnerability but missed exact CVE identity, so CVE calibration should be scored separately from location evidence.
- libxml2-2.9.4-cve-2017-8872: direct LLM outperformed SkillClaw under the high-budget setting (direct-deepseek-guarded-clean-budget080=10/10 vs skillclaw-inline-guarded-clean-budget080=8/10), which is a counterexample to any unconditional SkillClaw-improves claim.
- libxml2-2.9.4-cve-2017-8872: SkillClaw localized file/function/root-cause evidence but missed exact CVE identity; this suggests a CVE-calibration failure rather than a localization failure.
- tcpdump-4.9.1-cve-2017-13031: SkillClaw produced a stronger low-budget result (skillclaw-inline-guarded-clean-budget035=8/10 vs direct-deepseek-guarded-clean-budget035=0/10).
- tcpdump-4.9.1-cve-2017-13031: SkillClaw localized file/function/root-cause evidence but missed exact CVE identity; this suggests a CVE-calibration failure rather than a localization failure.
- tcpdump-4.9.1-cve-2017-13031: direct LLM also localized the vulnerability but missed exact CVE identity, so CVE calibration should be scored separately from location evidence.

## Paper-Framing Implication

The current evidence should not be framed as a universal win for SkillClaw. A safer framing is that task-specific, session-stable skill injection can improve agent steering under constrained budgets, while exact vulnerability identity and skill-induced bias require separate validation.
