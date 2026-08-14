# Current Briefing Package

Updated: `2026-08-06`

## 1. Core blind benchmarks

- Core benchmark runs: `6`
- Firmware ablation runs: `16`
- Closed-loop proof rows: `15`

## 2. Firmware ablation summary

| case_id | profile | runs | mean_score | best_score | file_hit_runs | function_hit_runs | selected_skill_set | feedback_decisions | handoff_runs | consumed_runs |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| firmware2-login-cgi-cve-2026-2527 | none | 3 | 4.333 | 5.0 | 2 | 0 |  | neutral | 0 | 0 |
| firmware2-login-cgi-cve-2026-2527 | relevant | 2 | 5.0 | 5.0 | 2 | 0 | embedded-cgi-command-injection-triage | neutral | 0 | 0 |
| firmware2-login-cgi-cve-2026-2527 | wrong | 2 | 4.5 | 5.0 | 2 | 0 | firmware-embedded-lua-shell-extraction | neutral | 0 | 0 |
| firmware2-login-cgi-cve-2026-2527 | seed | 1 | 5.0 | 5.0 | 1 | 0 | embedded-cgi-command-injection-triage | neutral | 1 | 1 |
| firmware2-wireless-cgi-cve-2026-2529 | none | 3 | 2.667 | 3.0 | 0 | 0 |  | neutral | 1 | 1 |
| firmware2-wireless-cgi-cve-2026-2529 | relevant | 2 | 3.0 | 3.0 | 0 | 0 | embedded-cgi-command-injection-triage | negative | 1 | 1 |
| firmware2-wireless-cgi-cve-2026-2529 | wrong | 1 | 3.0 | 3.0 | 0 | 0 | firmware-embedded-lua-shell-extraction | negative | 1 | 1 |
| firmware2-wireless-cgi-cve-2026-2529 | seed | 2 | 4.0 | 5.0 | 1 | 0 | embedded-cgi-command-injection-triage | negative; neutral | 2 | 2 |

## 3. Closed-loop proof

| case_id | run_id | selected_skills | handoff_status | receipt_status | candidates_queued | published_after_validation | validation_followup_status | validation_job_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| exiv2-0.26-cve-2017-17725 | exiv2-paper-20260802a | source-parser-state-machine-oob, elf-cwe120-plt-analysis | handed_off | consumed | 2 | 0 | completed | 2 |
| firmware2-login-cgi-cve-2026-2527 | firmware2-login-cgi-cve-2026-2527-blind-skillclaw-inline-guarded-20260805-174210 | embedded-cgi-command-injection-triage | handed_off | consumed | 1 | 0 | completed | 1 |
| firmware2-login-cgi-cve-2026-2527 | firmware2-login-seed-20260806a | embedded-cgi-command-injection-triage | handed_off | consumed | 1 | 0 | completed | 1 |
| firmware2-wireless-cgi-cve-2026-2529 | firmware2-wireless-none-20260806a |  | handed_off | consumed | 0 | 0 | not_needed | 0 |
| firmware2-wireless-cgi-cve-2026-2529 | firmware2-wireless-relevant-20260806a | embedded-cgi-command-injection-triage | handed_off | consumed | 1 | 0 | completed | 1 |
| firmware2-wireless-cgi-cve-2026-2529 | firmware2-wireless-seed-20260805a | embedded-cgi-command-injection-triage | handed_off | consumed | 0 | 0 | not_needed | 0 |
| firmware2-wireless-cgi-cve-2026-2529 | firmware2-wireless-seed-20260805b | embedded-cgi-command-injection-triage | handed_off | consumed | 1 | 0 | completed | 1 |
| firmware2-wireless-cgi-cve-2026-2529 | firmware2-wireless-wrong-20260806a | firmware-embedded-lua-shell-extraction | handed_off | consumed | 1 | 0 | completed | 1 |
| giflib-5.1.2-cve-2016-3977 | giflib-blind-e2e-20260801e | source-parser-state-machine-oob, elf-cwe120-plt-analysis | handed_off | consumed | 2 | 0 | completed | 2 |
| giflib-5.1.2-cve-2016-3977 | giflib-e2e-20260804a | source-parser-state-machine-oob, elf-cwe120-plt-analysis | handed_off | pending | 0 | 0 | not_needed | 0 |
| giflib-5.1.2-cve-2016-3977 | giflib-paper-20260801a | source-parser-state-machine-oob, elf-cwe120-plt-analysis | handed_off | consumed | 1 | 0 | completed | 1 |
| libarchive-3.8.0-cve-2025-60753 | libarchive-paper-20260802a | elf-cwe120-plt-analysis | handed_off | consumed | 1 | 0 | completed | 1 |
| libxml2-2.9.4-cve-2017-8872 | libxml2-paper-20260801a | source-parser-state-machine-oob, elf-cwe120-plt-analysis | handed_off | consumed | 2 | 0 | completed | 2 |
| tcpdump-4.9.1-cve-2017-13031 | tcpdump13031-paper-20260802a | source-parser-state-machine-oob, elf-cwe120-plt-analysis | handed_off | consumed | 1 | 0 | completed | 1 |
| tcpdump-4.9.1-cve-2018-14469 | tcpdump-paper-20260801a | source-parser-state-machine-oob, elf-cwe120-plt-analysis | handed_off | consumed | 0 | 0 | not_needed | 0 |

## 4. Notes

- Wireless 20260806a relevant / none / wrong runs are included.
- Login 20260806a seed run is included.
- Current evidence suggests the branch-first seed profile is more stable than the narrowed relevant profile on firmware CGI cases.
