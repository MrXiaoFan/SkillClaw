# Differences From The Public SkillClaw Repository

This repository is not a clean mirror of the public SkillClaw codebase. It is a
research and engineering extension branch built on top of SkillClaw for remote
Claude Code usage, server-side skill injection, and vulnerability-localization
experiments.

Use this file as the first checklist when reviewing, uploading, or continuing
development.

## 1. Core Proxy And Skill Injection Changes

Compared with the public SkillClaw repository, this branch changes the proxy
behavior in `skillclaw/`.

Main changed files:

- `skillclaw/api_server.py`
- `skillclaw/skill_manager.py`
- `skillclaw/config.py`
- `skillclaw/config_store.py`
- `skillclaw/skill_hub.py`

Major changes:

- Adds server-side skill visibility endpoints such as `/v1/skills` and
  `/v1/skills/{name}`.
- Adds inline skill injection so remote Claude Code clients can receive
  server-side `SKILL.md` content through the proxy, even when the remote VM does
  not have the skill files locally.
- Adds session-stable inline skill pinning. The first task-oriented inline skill
  set selected for a session is reused on later turns, reducing multi-turn skill
  drift.
- Adds injection metadata for auditing, including selected skills, prompt hash,
  injection mode, stable action, and skill count.
- Improves retrieval routing to avoid selecting `skillclaw-*` framework skills
  for vulnerability-analysis tasks.
- Fixes Windows-to-Linux skill path handling and local record persistence issues
  found during deployment.

## 2. Experiment And Validation Additions

The public SkillClaw repository does not contain the local experiment framework
added here.

Added directories:

- `experiment_cases/`
- `experiment_scripts/`
- `experiment_validation/`
- `experiment_records/`

Purpose:

- Compare `Claude Code + SkillClaw key` against `Claude Code + direct DeepSeek`
  on the same remote VM, target software, prompt, and budget.
- Score vulnerability-localization answers against case ground truth: CVE, file,
  function, evidence, and root cause.
- Track which SkillClaw skills were injected during a run.
- Prototype dynamic-validation modes such as content matching, source matching,
  command checks, bundle scripts, and sanitizer/crash-oriented commands.

Important scripts:

- `experiment_scripts/print_case_prompt.py`
- `experiment_scripts/score_agent_output.py`
- `experiment_scripts/build_result_record.py`
- `experiment_scripts/summarize_results.py`
- `experiment_scripts/run_eval_case.py`
- `experiment_scripts/send_remote_tmux.ps1`

## 3. Test Additions

Added focused regression tests:

- `tests/test_experiment_scripts.py`
- `tests/test_inline_skill_session_cache.py`

These tests cover prompt generation, scoring behavior, guarded prompt modes,
inline skill retrieval, and session-stable skill pin/reuse behavior.

## 4. Research Records Added

This branch intentionally tracks selected experiment records because they are
part of the research evidence.

Important current records include:

- `experiment_records/experiment_matrix_20260625.md`
- `experiment_records/experiment_matrix_20260625.csv`
- `experiment_records/tcpdump_guarded_clean_comparison_20260625.md`
- `experiment_records/libxml2_guarded_clean_comparison_20260625.md`
- `experiment_records/experiment_report_20260615_20260621.md`
- `experiment_records/scoring_rubric.md`

The current evidence is mixed:

- On `tcpdump-4.9.1`, SkillClaw completed a useful answer under a low-budget
  condition where direct DeepSeek exhausted the budget.
- On `libxml2-2.9.4`, direct DeepSeek high-budget reached `10/10`, while
  SkillClaw high-budget reached `8/10` because it localized the bug but missed
  exact CVE calibration.

This means the branch should not claim that SkillClaw is universally better.
The more accurate research direction is to study when skill injection improves
localization efficiency and when it biases the model toward plausible but wrong
vulnerability identities.

## 5. Files That Must Not Be Uploaded As Source History

Do not commit local runtime/private artifacts:

- `.venv/`
- `.local-share/`
- `logs/`
- `records/conversations.jsonl`
- `records/prm_scores.jsonl`
- `experiment_records/recent_conversations_tail_*.jsonl`
- generated `.zip` archives
- dashboard databases
- local API-key backups

The `.gitignore` in this branch is adjusted to keep reproducible experiment
records while excluding large archives and private runtime logs.

## 6. Codeup Dev Branch Warning

At the time this note was written, the remote Codeup `dev` branch contained
unresolved merge-conflict markers in many core files, including
`skillclaw/api_server.py`, `skillclaw/skill_manager.py`, `skillclaw/skill_hub.py`,
`evolve_server/__main__.py`, and `pyproject.toml`.

Before using or publishing `dev`, replace it with a clean branch or explicitly
resolve those conflicts. The local branch used for upload should compile and
pass:

```bash
python -m pytest tests/test_experiment_scripts.py tests/test_inline_skill_session_cache.py
```
