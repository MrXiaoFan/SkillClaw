# Local Changes From SkillClaw

This package is based on SkillClaw with local engineering and research changes
for remote Claude Code usage, server-side skill injection, vulnerability
localization experiments, and dynamic-validation prototyping.

## 1. Remote Claude Code And Server-Side Skill Visibility

The original SkillClaw workflow mainly stores, shares, and injects skills inside
the proxy process. Remote Claude Code clients that only use a SkillClaw API key
cannot automatically see these skills as Claude Code local skills.

Local changes added:

- Server-side skill catalog endpoints:
  - `GET /v1/skills`
  - `GET /v1/skills/{skill_name}`
- Authentication through the same SkillClaw API key used by the proxy.
- Skill catalog output designed for remote agents to distinguish SkillClaw
  server-side skills from Claude Code local skills.
- Prompt wording that tells remote Claude Code not to search local project
  paths for SkillClaw skills.

Main files:

- `skillclaw/api_server.py`
- `skillclaw/skill_manager.py`

## 2. Inline Skill Injection

Original catalog-style injection can tell the LLM that a skill exists, but a
remote machine may not have the corresponding `SKILL.md` path. Inline injection
solves this by selecting relevant server-side skills and inserting their full
content directly into the system prompt.

Local changes added:

- `skills.injection_mode: inline`
- Server-side inline selection and prompt construction.
- Full `<available_server_skills>` catalog plus `<loaded_skills>` content.
- Metadata recording for injected skills:
  - selected skill names
  - injection mode
  - top-k
  - prompt hash
  - available skill count

Main files:

- `skillclaw/config.py`
- `skillclaw/config_store.py`
- `skillclaw/api_server.py`
- `skillclaw/skill_manager.py`

## 3. Skill Path And Persistence Fixes

Local deployment exposed Windows/Linux path and restart persistence issues.

Local changes include:

- Avoid overwriting conversation and PRM record files on restart.
- Fix public skill path formatting when a Windows server serves Linux remote
  clients.
- Add or expose configuration fields for sharing, skill reload, dashboard, and
  evolve-server integration.

Main files:

- `skillclaw/api_server.py`
- `skillclaw/skill_manager.py`
- `skillclaw/config.py`
- `skillclaw/config_store.py`

## 4. Inline Retrieval Bias Fix

Remote experiment prompts often include framework wording such as
`SkillClaw server-side skills`, `Claude Code`, `JSON`, and `Do not WebSearch`.
The previous lightweight keyword retrieval treated these as task terms, causing
SkillClaw self-inspection skills to outrank vulnerability-analysis skills.

Local changes added:

- Query stopwords for framework/plumbing terms.
- Vulnerability-task markers such as `cve`, `cwe`, `overflow`, `oob`,
  `parser`, `firmware`, `binary`, `elf`, and `source`.
- SkillClaw-meta-task markers such as `skill count`, `skill catalog`,
  `/v1/skills`, and `proxy api`.
- Rule: for vulnerability tasks, do not let `skillclaw-*` self-inspection
  skills consume inline top-k slots unless the task is actually about SkillClaw
  itself.
- Rule: for source-level parser boundary tasks, prefer
  `source-parser-state-machine-oob` and exclude IDA/idalib skills unless the
  user explicitly asks for IDA, Hex-Rays, headless, or decompiler analysis.
- Rule: for vulnerability tasks, ignore incidental SSH/remote-execution words
  unless the request has explicit SSH password/login/reconnaissance intent.

Observed effect:

- Before fix, the tcpdump case selected:
  - `ida-headless-cwe120-sink-analysis`
  - `elf-cwe120-firmware-triage`
  - `skillclaw-proxy-introspection`
- After fix, the first turn selected:
  - `source-parser-state-machine-oob`
  - `elf-cwe120-firmware-triage`
  - `vuln-hunting`

Main file:

- `skillclaw/skill_manager.py`

## 5. Session-Stable Inline Skill Injection

After inline retrieval was improved, multi-turn experiments still exposed
another issue: the first turn could select a relevant vulnerability skill, while
later tool-result turns re-selected unrelated skills because the latest context
contained words such as `ssh`, `SkillClaw`, or `server-side skills`.

Local changes added:

- `_handle_openclaw_request()` passes `session_id` into `_inject_skills()`.
- Inline/server-inline mode pins the first task-oriented skill set for the
  session.
- Later main turns reuse the pinned skill bodies if the local skill generation
  has not changed.
- Pure SkillClaw meta tasks, such as querying skill count or catalog, are not
  pinned.
- Session close removes the inline skill cache.
- Injection metadata now records:
  - `stable_session`
  - `stable_action` (`pin`, `reuse`, or `none`)
  - `stable_generation`

Main files:

- `skillclaw/api_server.py`
- `tests/test_inline_skill_session_cache.py`
- `experiment_records/inline_skill_session_stability_fix_20260625.md`

## 6. Experiment And Dynamic Validation Framework

A lightweight experiment framework was added outside the original SkillClaw
core. Its purpose is to evaluate whether evolved or injected skills actually
improve vulnerability localization.

Added directories:

- `experiment_cases/`
- `experiment_scripts/`
- `experiment_validation/`

Core capabilities:

- Case definitions with target, ground truth, scoring, validators, and prompts.
- Direct DeepSeek vs SkillClaw key comparison.
- Unified runner for Claude Code experiments.
- Output scoring against CVE, file, function, evidence, and root cause.
- Validation modes:
  - `content_match`
  - `source_contains`
  - `command`
  - `bundle_script`
  - `asan_command`
- Result record builder and experiment matrix summarizer.
- Injection-history tracking to detect skill drift inside a multi-turn session.

Key scripts:

- `experiment_scripts/run_eval_case.py`
- `experiment_scripts/build_result_record.py`
- `experiment_scripts/score_agent_output.py`
- `experiment_scripts/run_dynamic_case.py`
- `experiment_scripts/extract_skill_injection.py`
- `experiment_scripts/summarize_results.py`
- `experiment_scripts/package_experiment_framework.py`
- `experiment_scripts/send_remote_tmux.ps1`

Remote experiment operation note:

- `send_remote_tmux.ps1` sends command blocks to a watched VM `tmux`
  session through UTF-8 base64 transport. This avoids Windows PowerShell /
  SSH encoding issues where Chinese prompts were converted to `???`.

## 7. Current Research Observations

Current evidence from tcpdump and libxml2 experiments suggests:

- SkillClaw can improve localization when a task-relevant skill is selected.
- SkillClaw is not automatically better than a direct LLM baseline.
- Skill quality and retrieval quality must be evaluated separately.
- Text-only skill evolution is not enough to prove improvement.
- Dynamic validation and injection-history-aware evaluation are needed.
- Multi-turn sessions can suffer from skill injection drift.

This motivates the next engineering direction:

- Session-stable skill injection.
- Stronger final-output schema enforcement.
- More realistic dynamic validators using sanitizer/crash evidence.
- Skill bundle support for scripts and executable checks.

## 8. Upload Package And Repository Layout Notes

The repository upload package should include:

- `skillclaw/` source changes listed above.
- `experiment_cases/` benchmark definitions and skill-bundle examples.
- `experiment_scripts/` experiment, scoring, packaging, and remote-tmux helper scripts.
- `experiment_validation/` validator framework.
- `experiment_records/` experiment reports, raw/final outputs, score JSON/JSONL,
  validation JSON, matrices, and remote run artifacts.
- `tests/test_experiment_scripts.py`.
- `tests/test_inline_skill_session_cache.py`.
- `LOCAL_CHANGES_FROM_SKILLCLAW.md`.
- `REPOSITORY_UPLOAD_GUIDE.md`.

The generated upload archive may also include a `Skills/` snapshot copied from
the sibling directory `../Skills`, because this project keeps generated
SkillClaw skills outside the Python package checkout.

## 9. Files Deliberately Not Included In Source Packages

Source packages should not include runtime/private artifacts such as:

- `.venv/`
- `records/conversations.jsonl` (large full session history; 600MB+ in the current workspace)
- `records/prm_scores.jsonl`
- `.local-share/`
- dashboard SQLite databases
- local API-key backups
- model/cache directories
- `logs/`
- `__pycache__/`
- `.pytest_cache/`
- old generated `.zip` packages under `experiment_records/`

These files are environment-specific and may contain large logs or sensitive
data.
