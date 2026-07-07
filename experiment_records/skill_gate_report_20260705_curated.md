# Skill Gate Report

This report converts validator-backed skill feedback into conservative gate decisions.
It does not automatically publish, rewrite, or delete any skill.

| skill | gate_decision | selected_count | positive | neutral | negative | mean_score | cve_hits | file_hits | function_hits | reasons | suggestions |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| source-parser-state-machine-oob | promote | 3 | 3 | 0 | 0 | 1.0 | 3 | 3 | 3 | 3 positive run(s), mean_score=1, file/function evidence hit; 3 validator-passed run(s) | candidate for broader benchmark evaluation or default retrieval boost if no later evidence gap is found |
| vuln-hunting | keep | 2 | 2 | 0 | 0 | 1.0 | 2 | 2 | 2 | 2 positive run(s), mean_score=1; 2 validator-passed run(s) | keep enabled, but require more cases before promotion |
| elf-cwe120-firmware-triage | insufficient_evidence | 1 | 1 | 0 | 0 | 1.0 | 1 | 1 | 1 | only 1 selected run(s); require at least 2; 1 validator-passed run(s) | collect more benchmark runs before changing publication status |
| ida-headless-cwe120-sink-analysis | insufficient_evidence | 1 | 1 | 0 | 0 | 1.0 | 1 | 1 | 1 | only 1 selected run(s); require at least 2; 1 validator-passed run(s) | collect more benchmark runs before changing publication status |
| idalib-headless-batch-diagnosis | insufficient_evidence | 1 | 1 | 0 | 0 | 1.0 | 1 | 1 | 1 | only 1 selected run(s); require at least 2; 1 validator-passed run(s) | collect more benchmark runs before changing publication status |
| verify-rootfs-full-enumeration | insufficient_evidence | 1 | 1 | 0 | 0 | 1.0 | 1 | 1 | 1 | only 1 selected run(s); require at least 2; 1 validator-passed run(s) | collect more benchmark runs before changing publication status |

## Gate Semantics

- `promote`: strong current evidence; candidate for retrieval boost or broader benchmark evaluation.
- `keep`: useful evidence exists, but more cases are needed before promotion.
- `revise`: localization may help, but evidence gaps, CVE calibration errors, or failures require edits.
- `demote`: selected skill is likely unrelated or harmful for the current task family.
- `insufficient_evidence`: too few selected runs to judge.
