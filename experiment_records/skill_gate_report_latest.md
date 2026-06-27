# Skill Gate Report

This report converts validator-backed skill feedback into conservative gate decisions.
It does not automatically publish, rewrite, or delete any skill.

| skill | gate_decision | selected_count | positive | neutral | negative | mean_score | cve_hits | file_hits | function_hits | reasons | suggestions |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| elf-cwe120-firmware-triage | revise | 4 | 2 | 2 | 0 | 0.725 | 0 | 4 | 3 | 2 positive run(s), mean_score=0.725; localization evidence exists but exact CVE calibration is absent; 2 validator-passed run(s) | keep as localization guidance, but revise before promotion; add guidance to verify exact CVE identity against advisories or patch metadata |
| source-parser-state-machine-oob | revise | 4 | 3 | 1 | 0 | 0.8 | 0 | 4 | 4 | 3 positive run(s), mean_score=0.8, file/function evidence hit; localization evidence exists but exact CVE calibration is absent; 2 validator-passed run(s) | keep as localization guidance, but revise before promotion; add guidance to verify exact CVE identity against advisories or patch metadata |
| vuln-hunting | revise | 2 | 2 | 0 | 0 | 0.8 | 0 | 2 | 2 | 2 positive run(s), mean_score=0.8; localization evidence exists but exact CVE calibration is absent | keep as localization guidance, but revise before promotion; add guidance to verify exact CVE identity against advisories or patch metadata |
| skillclaw-skill-discovery | demote | 3 | 1 | 2 | 0 | 0.7 | 0 | 3 | 2 | infrastructure/self-inspection skill selected during vulnerability-localization runs; localization evidence exists but exact CVE calibration is absent; 3 validator-passed run(s) | tighten retrieval so this skill is not selected unless the user asks about SkillClaw internals; add guidance to verify exact CVE identity against advisories or patch metadata |
| skillclaw-proxy-introspection | demote | 2 | 1 | 1 | 0 | 0.8 | 0 | 2 | 2 | infrastructure/self-inspection skill selected during vulnerability-localization runs; localization evidence exists but exact CVE calibration is absent; 2 validator-passed run(s) | tighten retrieval so this skill is not selected unless the user asks about SkillClaw internals; add guidance to verify exact CVE identity against advisories or patch metadata |
| elf-cwe120-plt-analysis | insufficient_evidence | 1 | 0 | 1 | 0 | 0.8 | 0 | 1 | 1 | only 1 selected run(s); require at least 2; 1 validator-passed run(s) | collect more benchmark runs before changing publication status |
| skillclaw-claude-env | insufficient_evidence | 1 | 0 | 1 | 0 | 0.8 | 0 | 1 | 1 | infrastructure/self-inspection skill selected during vulnerability-localization runs; 1 validator-passed run(s) | tighten retrieval so this skill is not selected unless the user asks about SkillClaw internals |
| ssh-password-recon-workflow | insufficient_evidence | 1 | 0 | 1 | 0 | 0.5 | 0 | 1 | 0 | only 1 selected run(s); require at least 2; 1 validator-passed run(s) | collect more benchmark runs before changing publication status |

## Gate Semantics

- `promote`: strong current evidence; candidate for retrieval boost or broader benchmark evaluation.
- `keep`: useful evidence exists, but more cases are needed before promotion.
- `revise`: localization may help, but evidence gaps, CVE calibration errors, or failures require edits.
- `demote`: selected skill is likely unrelated or harmful for the current task family.
- `insufficient_evidence`: too few selected runs to judge.
