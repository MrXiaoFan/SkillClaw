# Skill Gate Report

This report converts validator-backed skill feedback into conservative gate decisions.
It does not automatically publish, rewrite, or delete any skill.

| skill | gate_decision | selected_count | positive | neutral | negative | mean_score | cve_hits | file_hits | function_hits | reasons | suggestions |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| source-parser-state-machine-oob | promote | 5 | 3 | 2 | 0 | 1.0 | 5 | 5 | 5 | 3 positive run(s), mean_score=1, file/function evidence hit; 2 run(s) selected this skill without task alignment; 5 validator-passed run(s) | candidate for broader benchmark evaluation or default retrieval boost if no later evidence gap is found; reduce over-selection by adding narrower trigger conditions |
| vuln-hunting | demote | 3 | 0 | 3 | 0 | 1.0 | 3 | 3 | 3 | 3 mismatched selection(s) and no task-aligned evidence; 3 run(s) selected this skill without task alignment; 3 validator-passed run(s) | tighten retrieval or rename the skill so it is not selected for this task family; reduce over-selection by adding narrower trigger conditions |
| ida-headless-cwe120-sink-analysis | demote | 2 | 0 | 2 | 0 | 1.0 | 2 | 2 | 2 | 2 mismatched selection(s) and no task-aligned evidence; 2 run(s) selected this skill without task alignment; 2 validator-passed run(s) | tighten retrieval or rename the skill so it is not selected for this task family; reduce over-selection by adding narrower trigger conditions |
| idalib-headless-batch-diagnosis | demote | 2 | 0 | 2 | 0 | 1.0 | 2 | 2 | 2 | 2 mismatched selection(s) and no task-aligned evidence; 2 run(s) selected this skill without task alignment; 2 validator-passed run(s) | tighten retrieval or rename the skill so it is not selected for this task family; reduce over-selection by adding narrower trigger conditions |
| verify-rootfs-full-enumeration | demote | 2 | 0 | 2 | 0 | 1.0 | 2 | 2 | 2 | 2 mismatched selection(s) and no task-aligned evidence; 2 run(s) selected this skill without task alignment; 2 validator-passed run(s) | tighten retrieval or rename the skill so it is not selected for this task family; reduce over-selection by adding narrower trigger conditions |
| elf-cwe120-firmware-triage | insufficient_evidence | 1 | 0 | 1 | 0 | 1.0 | 1 | 1 | 1 | only 1 selected run(s); require at least 2; 1 run(s) selected this skill without task alignment; 1 validator-passed run(s) | collect more benchmark runs before changing publication status; reduce over-selection by adding narrower trigger conditions |

## Gate Semantics

- `promote`: strong current evidence; candidate for retrieval boost or broader benchmark evaluation.
- `keep`: useful evidence exists, but more cases are needed before promotion.
- `revise`: localization may help, but evidence gaps, CVE calibration errors, or failures require edits.
- `demote`: selected skill is likely unrelated or harmful for the current task family.
- `insufficient_evidence`: too few selected runs to judge.
