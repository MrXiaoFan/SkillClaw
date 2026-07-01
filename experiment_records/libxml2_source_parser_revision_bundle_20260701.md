# Skill Feedback Bundles

This file summarizes evolver-ready, dimension-level feedback for selected skills.

| skill | gate | runs | mean_score | localization | cve_hit | cve_miss | validator_passed | artifact_generated | artifact_exec | directives | templates |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| source-parser-state-machine-oob | revise | 2 | 0.8 | 2 | 0 | 1 | 2 | 0 | 0 | Keep useful localization guidance, but add an explicit CVE-calibration section and uncertainty fallback.; Separate source localization from exact CVE identity; require advisory, patch, or version-range evidence before naming a CVE.; add guidance to verify exact CVE identity against advisories or patch metadata; keep as localization guidance, but revise before promotion | cve_calibration_miss |
