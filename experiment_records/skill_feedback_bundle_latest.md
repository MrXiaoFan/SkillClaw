# Skill Feedback Bundles

This file summarizes evolver-ready, dimension-level feedback for selected skills.

| skill | gate | runs | relevant | mismatched | infra | mean_score | localization | cve_hit | cve_miss | validator_passed | artifact_generated | artifact_exec | directives | templates |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| vuln-hunting | demote | 3 | 0 | 3 | 0 | 1.0 | 3 | 3 | 0 | 3 | 2 | 2 | reduce over-selection by adding narrower trigger conditions; tighten retrieval or rename the skill so it is not selected for this task family |  |
| ida-headless-cwe120-sink-analysis | demote | 2 | 0 | 2 | 0 | 1.0 | 2 | 2 | 0 | 2 | 2 | 2 | reduce over-selection by adding narrower trigger conditions; tighten retrieval or rename the skill so it is not selected for this task family |  |
| idalib-headless-batch-diagnosis | demote | 2 | 0 | 2 | 0 | 1.0 | 2 | 2 | 0 | 2 | 2 | 2 | reduce over-selection by adding narrower trigger conditions; tighten retrieval or rename the skill so it is not selected for this task family |  |
| verify-rootfs-full-enumeration | demote | 2 | 0 | 2 | 0 | 1.0 | 2 | 2 | 0 | 2 | 2 | 2 | reduce over-selection by adding narrower trigger conditions; tighten retrieval or rename the skill so it is not selected for this task family |  |
| elf-cwe120-firmware-triage | insufficient_evidence | 1 | 0 | 1 | 0 | 1.0 | 1 | 1 | 0 | 1 | 0 | 0 | collect more benchmark runs before changing publication status; reduce over-selection by adding narrower trigger conditions |  |
| source-parser-state-machine-oob | promote | 5 | 3 | 2 | 0 | 1.0 | 5 | 5 | 0 | 5 | 4 | 4 | candidate for broader benchmark evaluation or default retrieval boost if no later evidence gap is found; reduce over-selection by adding narrower trigger conditions |  |
