# Experiment Records Index

This directory keeps only the current experiment artifacts that are useful for
reproduction or reporting. SkillClaw runtime session records and generated
skills are intentionally not stored here.

## Kept Files

- `experiment_report_20260615_20260621.md`: consolidated report for completed
  SkillClaw vs direct-LLM experiments.
- `dev_notes_20260627.md`: short engineering log for the latest preflight
  runner work, Codeup dev synchronization, and current test-suite status.
- `libxml2_deepseek_vs_skillclaw_20260623.md`: focused comparison of
  SkillClaw inline skill injection and direct DeepSeek on the libxml2 2.9.4
  case.
- `tcpdump_skillclaw_unified_20260623.md`: first tcpdump run through the
  unified runner, including the observation that the answer scored well while
  injected skills were not task-specific.
- `tcpdump_deepseek_vs_skillclaw_20260623.md`: focused comparison of SkillClaw
  and direct DeepSeek on the tcpdump 4.9.1 case.
- `tcpdump_skillclaw_rerun_20260624.md`: rerun after inline retrieval fix,
  showing improved first-turn retrieval and later injection drift.
- `experiment_matrix_20260623.md` and `experiment_matrix_20260623.csv`:
  compact matrix of all current final records, including score, ground-truth
  hits, validation status, selected skills, and feedback action.
- `experiment_matrix_20260624.md` and `experiment_matrix_20260624.csv`:
  updated matrix with injection-history columns.
- `experiment_matrix_20260625.md` and `experiment_matrix_20260625.csv`:
  guarded clean comparison matrix covering tcpdump and libxml2 budgeted runs.
- `tcpdump_guarded_clean_comparison_20260625.md`: tcpdump comparison showing
  SkillClaw completed under the low-budget condition while direct DeepSeek
  required a higher budget to reach the same localization score.
- `libxml2_guarded_clean_comparison_20260625.md`: libxml2 comparison showing a
  counterexample where direct DeepSeek high-budget reached exact CVE
  calibration while SkillClaw localized the bug but predicted neighboring CVEs.
- `libxml2-*-20260623.*`: raw/final/score/validation artifacts for the libxml2
  comparison.
- `tcpdump-*-20260623.*`: raw/final/score/validation artifacts for the tcpdump
  SkillClaw run.
- `scoring_rubric.md`: readable scoring rules for case-level vulnerability
  localization experiments.
- `skillclaw-experiment-framework-*.zip`: latest portable package containing
  experiment cases, scripts, validators, tests, and the consolidated report.

## Main Runner

- `experiment_scripts/run_eval_case.py` is the current unified entry point for
  a single case. It can either call Claude Code or reuse an existing agent
  output, then writes prompt/raw/stderr/meta/score/validation/final artifacts.
  Use `--preflight` before remote VM runs to verify the target tree, provider,
  and SkillClaw endpoint before spending a long Claude Code session.

## Removed As Redundant

The earlier tcpdump/libxml2 standalone records, old validation selftest JSONL,
old patch exports, and old git bundle exports were removed because their useful
content has been merged into the consolidated report or superseded by the
current source tree and latest portable package.
