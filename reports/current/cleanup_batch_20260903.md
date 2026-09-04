# Batch Cleanup Candidates · 2026-09-03

This is a batch deletion list. The files below are not current code, current paper sources, or
primary experiment records.

## Confirmed deletion candidates

### Duplicate paper build outputs

- `paper/skill_evolution_blind_vulnerability_analysis_arxiv.pdf`
- `paper/skillclaw_confirmation_feedback_elsarticle.pdf`

Both are byte-for-byte identical to the PDFs under `paper/package_20260824/manuscript/`.

### Unreferenced early experiment process logs

- `runtime/ablation/results/f1202_experiment.log`
- `runtime/ablation/results/f9k1122_extra_run.log`
- `runtime/ablation/results/f9k1122_run.log`

These are one-off process logs. Primary result CSVs and raw imported runs remain available.

### Unreferenced old service logs

- `runtime/api_server.log`
- `runtime/api_server_err.log`

These are old local service startup logs with no current-document references. The separately
referenced `runtime/validation_260816.log` and `runtime/logs/remote_vm_commands.log` are kept.

## Keep

- `runtime/ablation/results/ablation_results.csv` — unique 159-run historical aggregate; not
  replaceable by the 153-run clean experiment.
- All `ablation_results_*` primary result files and their referenced logs/state files.
- `runtime/imports/`, `runtime/records/`, `runtime/results/`, and `runtime/evolve/`.

## Historical handoff deletion — content condensed on 2026-09-03

The non-redundant historical detail from these files was condensed into the timestamped section
`历史交接补充（2026-09-03 记录）` in the root `AGENT_HANDOFF.md`. The three source handoffs are now
ready for deletion; they contain no remaining unique engineering or experiment evidence needed by
the current plan.

- `docs/handoff/archive/20260809/AGENT_HANDOFF.md`
- `docs/handoff/archive/20260809/AGENT_HANDOFF_GPT_TO_GLM_20260809.md`
- `docs/handoff/archive/20260809/AGENT_HANDOFF_GPT_TO_GLM_20260809_02.md`

## Additional exact duplicates — package handoff copies

The following six files are byte-for-byte identical to the active copies under `docs/handoff/`.
Keep the `docs/handoff/` versions as the engineering source of truth; the package retains
`handoff/AGENT_HANDOFF_current.md` as its compact entry point. These six package copies can be
deleted without losing unique content:

- `paper/package_20260824/support/handoff/20260811/01_research_and_development_state.md`
- `paper/package_20260824/support/handoff/20260811/02_paper_frame_and_manuscript_state.md`
- `paper/package_20260824/support/handoff/20260811/03_engineering_status_tests_and_next_plan.md`
- `paper/package_20260824/support/handoff/20260812/01_runtime_handoff_and_service_bootstrap.md`
- `paper/package_20260824/support/handoff/20260815/01_gate_fix_and_paper_draft_handoff.md`
- `paper/package_20260824/support/handoff/20260820/01_necessity_plan_done_and_next.md`

## Additional exact duplicates — package plan copies

The following files are byte-for-byte identical to the active files under `docs/plans/` and can
be deleted with the package handoff copies:

- `paper/package_20260824/support/plans/README.md`
- `paper/package_20260824/support/plans/benchmark_candidate_backlog.md`
- `paper/package_20260824/support/plans/research_roadmap_20260820.md`
- `paper/package_20260824/support/plans/work_plan_20260820.md`

## Package report duplicates

The 51 files whose relative paths under `paper/package_20260824/support/reports/` matched files
under `reports/current/` and whose SHA-256 hashes were identical have been deleted. Delete only those exact matches;
retain the three differing files:

- `experiment_archive_all_20260820.md`
- `briefing_20260816/glm_handoff_20260816.md`
- `briefing_20260816/session_archive_20260816.md`

The current report tree remains the sole active report source after this cleanup.

Status: completed. The 51 exact duplicate report files were deleted. The three differing files
listed above remain in the package support tree.
