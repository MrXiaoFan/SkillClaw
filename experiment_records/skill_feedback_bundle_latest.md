# Skill Feedback Bundles

This file summarizes evolver-ready, dimension-level feedback for selected skills.

| skill | gate | runs | mean_score | localization | cve_hit | cve_miss | validator_passed | directives |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| skillclaw-skill-discovery | demote | 3 | 0.7 | 3 | 0 | 0 | 3 | Narrow retrieval so this infrastructure skill is selected only for SkillClaw-internal or catalog tasks.; tighten retrieval so this skill is not selected unless the user asks about SkillClaw internals |
| skillclaw-proxy-introspection | demote | 2 | 0.8 | 2 | 0 | 0 | 2 | Narrow retrieval so this infrastructure skill is selected only for SkillClaw-internal or catalog tasks.; tighten retrieval so this skill is not selected unless the user asks about SkillClaw internals |
| elf-cwe120-plt-analysis | insufficient_evidence | 1 | 0.8 | 1 | 0 | 1 | 1 | Keep useful localization guidance, but add an explicit CVE-calibration section and uncertainty fallback.; Separate source localization from exact CVE identity; require advisory, patch, or version-range evidence before naming a CVE.; collect more benchmark runs before changing publication status |
| skillclaw-claude-env | insufficient_evidence | 1 | 0.8 | 1 | 0 | 0 | 1 | tighten retrieval so this skill is not selected unless the user asks about SkillClaw internals |
| ssh-password-recon-workflow | insufficient_evidence | 1 | 0.5 | 1 | 0 | 0 | 1 | collect more benchmark runs before changing publication status |
| elf-cwe120-firmware-triage | revise | 4 | 0.725 | 4 | 0 | 1 | 2 | Keep useful localization guidance, but add an explicit CVE-calibration section and uncertainty fallback.; Separate source localization from exact CVE identity; require advisory, patch, or version-range evidence before naming a CVE.; add guidance to verify exact CVE identity against advisories or patch metadata; keep as localization guidance, but revise before promotion |
| source-parser-state-machine-oob | revise | 4 | 0.8 | 4 | 0 | 1 | 2 | Keep useful localization guidance, but add an explicit CVE-calibration section and uncertainty fallback.; Separate source localization from exact CVE identity; require advisory, patch, or version-range evidence before naming a CVE.; add guidance to verify exact CVE identity against advisories or patch metadata; keep as localization guidance, but revise before promotion |
| vuln-hunting | revise | 2 | 0.8 | 2 | 0 | 0 | 0 | add guidance to verify exact CVE identity against advisories or patch metadata; keep as localization guidance, but revise before promotion |
