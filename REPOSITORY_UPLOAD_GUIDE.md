# Repository Upload Guide For This SkillClaw Fork

This checkout is based on SkillClaw, with local changes for remote Claude Code
usage, server-side skill injection, vulnerability-localization experiments, and
dynamic-validation prototyping.

## What Differs From The Original SkillClaw Repository

### Core SkillClaw Source Changes

- `skillclaw/api_server.py`
  - Adds session-stable inline skill injection cache.
  - Pins the first task-oriented inline skill set for a session and reuses it
    across later turns.
  - Clears pinned inline skills when a session closes.
  - Records injection metadata such as `stable_session`, `stable_action`, and
    `stable_generation`.
  - Emits logs such as `stable=pin` and `stable=reuse` for experiment auditing.

- `skillclaw/skill_manager.py`
  - Improves inline skill retrieval for remote Claude Code prompts.
  - Adds stopwords for framework/plumbing terms such as SkillClaw, server-side,
    Claude Code, JSON, and WebSearch.
  - Distinguishes vulnerability-analysis tasks from SkillClaw meta-management
    tasks.
  - Prevents `skillclaw-*` self-inspection skills from consuming inline slots
    during real vulnerability-analysis tasks.
  - Prefers `source-parser-state-machine-oob` for source-level parser/OOB tasks.
  - Avoids incidental SSH/remote-transport words selecting
    `ssh-password-recon-workflow`.

Historical local changes that may already be present in this checkout are
summarized in `LOCAL_CHANGES_FROM_SKILLCLAW.md`, including `/v1/skills`,
inline skill injection, Windows/Linux path handling, and record persistence
fixes.

### New Research And Experiment Directories

- `experiment_cases/`
  - Benchmark case definitions with target metadata, ground truth, scoring
    rules, validators, and recommended prompts.
  - Current cases:
    - `tcpdump-4.9.1-cve-2017-13031.json`
    - `libxml2-2.9.4-cve-2017-8872.json`
  - `skill_bundles/source-parser-state-machine-oob/` contains a prototype
    text-plus-script skill bundle.

- `experiment_scripts/`
  - Experiment runner and utility scripts:
    - `print_case_prompt.py`
    - `score_agent_output.py`
    - `run_eval_case.py`
    - `run_dynamic_case.py`
    - `build_result_record.py`
    - `extract_skill_injection.py`
    - `summarize_results.py`
    - `skill_bundle_runner.py`
    - `send_remote_tmux.ps1`
  - These scripts support SkillClaw-vs-direct baselines, scoring, remote VM
    operation, and result record generation.

- `experiment_validation/`
  - Validator framework for turning text-only skill evaluation into a more
    evidence-based workflow.
  - Current modes:
    - `content_match`
    - `source_contains`
    - `command`
    - `bundle_script`
    - `asan_command`

- `experiment_records/`
  - Experiment reports, matrices, raw/final model outputs, score files,
    validation files, and copied remote-run artifacts.
  - Important current records:
    - `tcpdump_guarded_clean_comparison_20260625.md`
    - `tcpdump_skillclaw_guarded_clean_20260625.md`
    - `tcpdump_skillclaw_postfix_budget_failure_20260625.md`
    - `inline_skill_retrieval_routing_fix_20260625.md`
    - `inline_skill_session_stability_fix_20260625.md`
    - `experiment_report_20260615_20260621.md`

- `tests/test_experiment_scripts.py`
  - Regression tests for scoring, prompt generation, guarded modes, and inline
    retrieval behavior.

- `tests/test_inline_skill_session_cache.py`
  - Regression tests for session-stable inline skill pin/reuse behavior and
    meta-task non-pinning.

## Generated Skills Snapshot

The collaborative `dev` branch keeps the current generated skills snapshot
inside this checkout:

```text
D:\Code\SkillClaw\SkillClaw\Skills
```

The historical sibling path `D:\Code\SkillClaw\Skills` may still exist on the
original machine, but it should no longer be the primary working path. New
SkillClaw runs and future skill updates should use the repository-local
`Skills/` directory so that skill changes are visible in `git status` and can
be reviewed before pushing. In the current workspace it contains 35 `SKILL.md`
files, including `source-parser-state-machine-oob`.

## Data Included In The Upload Package

The upload package includes:

- Source tree files required to run SkillClaw.
- Experiment framework code.
- Experiment case definitions.
- Experiment records and result files.
- Current generated skills snapshot from repository-local `Skills/`.
- `evolve_history.jsonl` as optional research/runtime history data.

The upload package excludes:

- `.git/`
- `.venv/`
- `.pytest_cache/`
- `__pycache__/`
- `logs/`
- `.local-share/`
- `records/conversations.jsonl`
- `records/prm_scores.jsonl`
- generated `.zip` archives inside `experiment_records/`

`records/conversations.jsonl` is intentionally excluded because it is very
large and may contain full interaction history.

## Verification Before Upload

The current focused regression suite passes:

```text
python -m pytest tests/test_experiment_scripts.py tests/test_inline_skill_session_cache.py
27 passed
```

## Suggested GitHub Upload Workflow

After extracting the package into a clean repository:

```bash
git init
git add .
git commit -m "Add SkillClaw remote skill injection and validation experiments"
git remote add origin <your-fork-url>
git push -u origin main
```

If using an existing fork, inspect `.gitignore` first. This fork intentionally
keeps `experiment_records/` trackable, while still ignoring generated archives
and caches.
